import json
import threading
import queue
import traceback
from datetime import datetime, timezone

from server.models import db
from server.models.novel.graph_change import NovelGeneration
from server.services.redis_client import get_redis, redis_key, acquire_lock, release_lock


_sse_subscribers = {}
_sse_lock = threading.Lock()


def _sse_broadcast(gen_id, event, data):
    from server.services.redis_client import get_redis, redis_key
    r = get_redis()
    payload = f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
    if r is not None:
        try:
            r.publish(redis_key('novel', 'generation', str(gen_id), 'events'), payload)
        except Exception:
            pass
    else:
        with _sse_lock:
            subscribers = list(_sse_subscribers.get(gen_id, []))
        for q in subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                pass


def _update_progress(gen, progress, status=None):
    gen.progress = progress
    if status:
        gen.status = status
    db.session.commit()
    _sse_broadcast(gen.id, 'progress', gen.to_dict())


def start_generation(project_id, generation_type, target_id=None, params=None):
    """Create a generation record and start background thread."""
    gen = NovelGeneration(
        project_id=project_id,
        generation_type=generation_type,
        target_id=target_id,
        status='pending',
        progress=0,
    )
    db.session.add(gen)
    db.session.commit()

    # Check concurrency limits
    active_count = NovelGeneration.query.filter(
        NovelGeneration.project_id == project_id,
        NovelGeneration.status.in_(['pending', 'running']),
    ).count()
    if active_count > 3:
        gen.status = 'failed'
        gen.error = '该项目同时进行的任务过多，请等待完成后再试'
        db.session.commit()
        return gen

    # Check chapter-level lock for chapter_version and extract
    if generation_type in ('chapter_version', 'extract', 'review', 'chapter_workflow') and target_id:
        lock_key = redis_key('novel', 'lock', generation_type, str(target_id))
        r = get_redis()
        if r is not None:
            # Redis available — use distributed lock
            token = acquire_lock(lock_key, ttl=300)
            if token is None:
                gen.status = 'failed'
                gen.error = '该章节正在生成中，请稍后再试'
                db.session.commit()
                return gen
        else:
            # No Redis — check DB for active generations on same target
            lock_key = None
            token = None
            active_same_target = NovelGeneration.query.filter(
                NovelGeneration.target_id == target_id,
                NovelGeneration.generation_type == generation_type,
                NovelGeneration.status.in_(['pending', 'running']),
                NovelGeneration.id != gen.id,
            ).count()
            if active_same_target > 0:
                gen.status = 'failed'
                gen.error = '该章节正在生成中，请稍后再试'
                db.session.commit()
                return gen
    else:
        lock_key = None
        token = None

    thread = threading.Thread(
        target=_run_generation,
        args=(gen.id, params or {}, lock_key, token),
        daemon=True,
    )
    thread.start()

    return gen


def _run_generation(gen_id, params, lock_key, token):
    """Background thread that runs the actual generation."""
    from server.app import create_app
    app = create_app()
    with app.app_context():
        gen = NovelGeneration.query.get(gen_id)
        if not gen:
            return

        try:
            gen.status = 'running'
            db.session.commit()
            _sse_broadcast(gen.id, 'progress', gen.to_dict())

            if gen.generation_type == 'blueprint':
                _run_blueprint(gen, params)
            elif gen.generation_type == 'chapter_version':
                _run_chapter_version(gen, params)
            elif gen.generation_type == 'extract':
                _run_extract(gen, params)
            elif gen.generation_type == 'review':
                _run_review(gen, params)
            elif gen.generation_type == 'chapter_workflow':
                _run_chapter_workflow(gen, params)
            else:
                raise ValueError(f'未知的生成类型: {gen.generation_type}')

            gen.status = 'completed'
            gen.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            _sse_broadcast(gen.id, 'completed', gen.to_dict())

        except Exception as e:
            gen.status = 'failed'
            gen.error = str(e)
            gen.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            _sse_broadcast(gen.id, 'failed', gen.to_dict())

        finally:
            if lock_key and token:
                release_lock(lock_key, token)


def _run_blueprint(gen, params):
    from server.services.novel.blueprint_generator import generate_blueprint
    _update_progress(gen, 10)
    result = generate_blueprint(gen.project_id, params)
    gen.result = result
    _update_progress(gen, 100)


def _run_chapter_version(gen, params):
    from server.services.novel.version_generator import generate_versions
    _update_progress(gen, 10)
    result = generate_versions(gen.project_id, gen.target_id, params)
    gen.result = result
    _update_progress(gen, 100)


def _run_extract(gen, params):
    from server.services.novel.graph_extractor import extract_graph_changes
    _update_progress(gen, 10)
    result = extract_graph_changes(gen.project_id, gen.target_id)
    gen.result = result
    _update_progress(gen, 100)


def _run_review(gen, params):
    from server.services.novel.consistency_reviewer import review_chapter
    _update_progress(gen, 10)
    result = review_chapter(gen.project_id, gen.target_id)
    gen.result = result
    _update_progress(gen, 100)


def _run_chapter_workflow(gen, params):
    """Run the LangGraph chapter workflow."""
    from server.services.memory.workflow import run_chapter_workflow

    result = run_chapter_workflow(
        project_id=gen.project_id,
        chapter_id=gen.target_id,
        user_instruction=params.get('user_instruction', ''),
        version_type=params.get('version_type', 'custom'),
        model_key=params.get('model_key'),
    )

    gen.result = {
        'version_id': result.get('version_id'),
        'memory_changes': result.get('memory_changes', []),
        'conflicts': result.get('conflicts', []),
    }
