# server/services/novel/auto_continue.py
from server.models import db
from server.models.novel.chapter import NovelChapter
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode


def run_auto_continue(project_id, params):
    """Generate multiple chapters sequentially through the pipeline.

    Args:
        project_id: Project ID.
        params: dict with 'count' (int), 'version_type' (str), 'model_config' (dict).

    Returns:
        dict with 'chapters' (list) and 'completed' (int).
    """
    count = min(params.get('count', 3), 10)
    version_type = params.get('version_type', 'steady')
    model_config = params.get('model_config')

    results = []
    completed = 0

    for i in range(count):
        # 1. Find or create next empty chapter
        chapter = _ensure_next_chapter(project_id)
        if not chapter:
            break

        # 2. Run pipeline
        try:
            from server.services.memory.workflow import run_chapter_workflow
            result = run_chapter_workflow(
                project_id=project_id,
                chapter_id=chapter.id,
                version_type=version_type,
                model_config=model_config,
            )
        except Exception as e:
            results.append({
                'chapter_id': chapter.id,
                'status': 'failed',
                'reason': str(e),
            })
            break

        # 3. Check pause conditions
        if result.get('needs_human_review'):
            results.append({
                'chapter_id': chapter.id,
                'status': 'paused',
                'reason': 'high_severity_review',
                'review_result': result.get('review_result'),
            })
            break

        # 4. Check low-confidence knowledge changes
        structured = result.get('structured_result', {})
        knowledge = structured.get('knowledge_updates') or {}
        low_conf = any(
            (c.get('confidence') or 1.0) < 0.5
            for c in (knowledge.get('graph_changes') or [])
        )
        if low_conf:
            results.append({
                'chapter_id': chapter.id,
                'status': 'paused',
                'reason': 'low_confidence_graph_change',
            })
            break

        # 5. Auto-confirm chapter
        chapter.status = 'confirmed'
        db.session.commit()

        # 6. Generate summary (best effort)
        try:
            from server.services.novel.summarizer import generate_summary
            generate_summary(chapter.id)
        except Exception:
            pass

        completed += 1
        results.append({
            'chapter_id': chapter.id,
            'version_id': result.get('version_id'),
            'status': 'confirmed',
        })

    return {'chapters': results, 'completed': completed}


def _ensure_next_chapter(project_id):
    """Find the next empty chapter, or create one if outline nodes exist."""
    # First, find existing empty chapter
    empty = NovelChapter.query.filter(
        NovelChapter.project_id == project_id,
        (NovelChapter.content_markdown == '') | (NovelChapter.content_markdown.is_(None)),
    ).order_by(NovelChapter.order_index).first()

    if empty:
        return empty

    # No empty chapter — create one from the next outline node
    project = NovelProject.query.get(project_id)
    if not project:
        return None

    # Find the highest existing chapter order
    max_order = db.session.query(db.func.max(NovelChapter.order_index)).filter_by(
        project_id=project_id,
    ).scalar() or 0

    next_order = max_order + 1

    # Find outline node for this order
    outline = NovelOutlineNode.query.filter(
        NovelOutlineNode.project_id == project_id,
        NovelOutlineNode.node_type == 'chapter',
        NovelOutlineNode.order_index == next_order,
    ).first()

    chapter = NovelChapter(
        project_id=project_id,
        outline_node_id=outline.id if outline else None,
        title=outline.title if outline else f'第{next_order}章',
        content_markdown='',
        order_index=next_order,
        target_words=outline.target_words if outline else project.words_per_chapter,
        word_count=0,
        status='draft',
    )
    db.session.add(chapter)
    db.session.commit()

    return chapter
