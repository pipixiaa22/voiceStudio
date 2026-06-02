# server/routes/novels/graph.py
import json
from flask import request, jsonify, Response
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.chapter import NovelChapter
from server.models.novel.graph_change import NovelGraphChange, NovelGeneration
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/graph/characters', methods=['GET'])
def get_character_graph(project_id):
    NovelProject.query.get_or_404(project_id)
    entities = NovelEntity.query.filter_by(project_id=project_id).all()
    relations = NovelRelation.query.filter_by(project_id=project_id).all()
    return jsonify({
        'nodes': [{
            'id': e.id,
            'type': e.entity_type,
            'name': e.name,
            'importance': e.importance,
            'x': e.node_x,
            'y': e.node_y,
            'summary': e.summary,
        } for e in entities],
        'edges': [{
            'id': r.id,
            'source': r.source_entity_id,
            'target': r.target_entity_id,
            'type': r.relation_type,
            'label': r.label,
            'strength': r.strength,
            'status': r.status,
        } for r in relations],
    })


@novels_bp.route('/api/novels/<int:project_id>/graph/events', methods=['GET'])
def get_event_graph(project_id):
    NovelProject.query.get_or_404(project_id)
    events = NovelEvent.query.filter_by(project_id=project_id).all()
    relations = NovelEventRelation.query.filter_by(project_id=project_id).all()
    return jsonify({
        'nodes': [{
            'id': e.id,
            'type': e.event_type,
            'title': e.title,
            'summary': e.summary,
            'chapter_id': e.chapter_id,
            'timeline_order': e.timeline_order,
            'x': e.node_x,
            'y': e.node_y,
        } for e in events],
        'edges': [{
            'id': r.id,
            'source': r.source_event_id,
            'target': r.target_event_id,
            'type': r.relation_type,
            'label': r.label,
            'confidence': r.confidence,
        } for r in relations],
    })


@novels_bp.route('/api/novels/<int:project_id>/graph/layout', methods=['PUT'])
def update_graph_layout(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    entity_positions = data.get('entity_positions', [])
    for pos in entity_positions:
        entity = NovelEntity.query.get(pos.get('id'))
        if entity and entity.project_id == project_id:
            entity.node_x = pos.get('x', entity.node_x)
            entity.node_y = pos.get('y', entity.node_y)

    event_positions = data.get('event_positions', [])
    for pos in event_positions:
        event = NovelEvent.query.get(pos.get('id'))
        if event and event.project_id == project_id:
            event.node_x = pos.get('x', event.node_x)
            event.node_y = pos.get('y', event.node_y)

    db.session.commit()
    return jsonify({'ok': True})


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/extract-graph', methods=['POST'])
def extract_graph(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='extract',
        target_id=chapter_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202


@novels_bp.route('/api/novels/<int:project_id>/graph-changes/<int:change_id>/accept', methods=['POST'])
def accept_graph_change(project_id, change_id):
    change = NovelGraphChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return jsonify({'error': '变更不属于该项目'}), 400

    try:
        _apply_graph_change(change)
        change.accepted = True
    except (ValueError, KeyError, TypeError) as e:
        change.accepted = False
        db.session.commit()
        return jsonify({'error': str(e), 'change': change.to_dict()}), 400

    db.session.commit()
    return jsonify(change.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/graph-changes/<int:change_id>/reject', methods=['POST'])
def reject_graph_change(project_id, change_id):
    change = NovelGraphChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return jsonify({'error': '变更不属于该项目'}), 400

    change.accepted = False
    db.session.commit()
    return jsonify(change.to_dict())


def _validate_entity_in_project(entity_id, project_id, label='实体'):
    if not entity_id:
        raise ValueError(f'{label} ID 不能为空')
    entity = NovelEntity.query.get(entity_id)
    if not entity or entity.project_id != project_id:
        raise ValueError(f'{label} {entity_id} 不属于该项目')


def _validate_event_in_project(event_id, project_id, label='事件'):
    if not event_id:
        raise ValueError(f'{label} ID 不能为空')
    event = NovelEvent.query.get(event_id)
    if not event or event.project_id != project_id:
        raise ValueError(f'{label} {event_id} 不属于该项目')


def _apply_graph_change(change):
    """Apply an accepted graph change to the actual data."""
    after = change.after
    if not after:
        raise ValueError('变更内容不能为空')

    if change.change_type == 'add':
        if change.target_type == 'entity':
            if not after.get('name', '').strip():
                raise ValueError('实体名称不能为空')
            entity = NovelEntity(
                project_id=change.project_id,
                entity_type=after.get('entity_type', 'character'),
                name=after['name'].strip(),
                summary=after.get('summary'),
                importance=after.get('importance', 5),
            )
            if 'aliases' in after:
                entity.aliases = after['aliases']
            if 'attributes' in after:
                entity.attributes = after['attributes']
            db.session.add(entity)
            db.session.flush()
            change.target_id = entity.id

        elif change.target_type == 'relation':
            _validate_entity_in_project(after.get('source_entity_id'), change.project_id, '源实体')
            _validate_entity_in_project(after.get('target_entity_id'), change.project_id, '目标实体')
            if not after.get('relation_type'):
                raise ValueError('关系类型不能为空')
            rel = NovelRelation(
                project_id=change.project_id,
                source_entity_id=after['source_entity_id'],
                target_entity_id=after['target_entity_id'],
                relation_type=after['relation_type'],
                label=after.get('label'),
                description=after.get('description'),
                strength=after.get('strength', 0.5),
            )
            db.session.add(rel)
            db.session.flush()
            change.target_id = rel.id

        elif change.target_type == 'event':
            event = NovelEvent(
                project_id=change.project_id,
                chapter_id=change.chapter_id,
                title=after.get('title', ''),
                summary=after.get('summary'),
                event_type=after.get('event_type', 'event'),
                timeline_order=after.get('timeline_order', 0),
            )
            if 'participants' in after:
                event.participants = after['participants']
            db.session.add(event)
            db.session.flush()
            change.target_id = event.id

        elif change.target_type == 'event_relation':
            _validate_event_in_project(after.get('source_event_id'), change.project_id, '源事件')
            _validate_event_in_project(after.get('target_event_id'), change.project_id, '目标事件')
            if not after.get('relation_type'):
                raise ValueError('事件关系类型不能为空')
            rel = NovelEventRelation(
                project_id=change.project_id,
                source_event_id=after['source_event_id'],
                target_event_id=after['target_event_id'],
                relation_type=after['relation_type'],
                label=after.get('label'),
                description=after.get('description'),
                confidence=after.get('confidence', 0.8),
            )
            db.session.add(rel)
            db.session.flush()
            change.target_id = rel.id

    elif change.change_type == 'modify':
        if change.target_type == 'entity':
            entity = NovelEntity.query.get(change.target_id)
            if not entity or entity.project_id != change.project_id:
                raise ValueError(f'实体 {change.target_id} 不属于该项目')
            for k, v in after.items():
                if k in ('name', 'summary', 'importance', 'entity_type'):
                    setattr(entity, k, v)
                elif k == 'aliases':
                    entity.aliases = v
                elif k == 'attributes':
                    entity.attributes = v

        elif change.target_type == 'relation':
            rel = NovelRelation.query.get(change.target_id)
            if not rel or rel.project_id != change.project_id:
                raise ValueError(f'关系 {change.target_id} 不属于该项目')
            _RELATION_SAFE_FIELDS = {'relation_type', 'label', 'description', 'strength', 'status'}
            for k, v in after.items():
                if k in _RELATION_SAFE_FIELDS:
                    setattr(rel, k, v)
                elif k == 'evidence':
                    rel.evidence = v
                # Ignore unsafe fields (source_entity_id, target_entity_id, project_id, etc.)


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/review', methods=['POST'])
def review_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='review',
        target_id=chapter_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202


@novels_bp.route('/api/novels/generations/<int:gen_id>', methods=['GET'])
def get_generation(gen_id):
    gen = NovelGeneration.query.get_or_404(gen_id)
    return jsonify(gen.to_dict())


@novels_bp.route('/api/novels/generations/<int:gen_id>/stream', methods=['GET'])
def stream_generation(gen_id):
    def generate():
        import time
        gen = NovelGeneration.query.get(gen_id)
        if not gen:
            yield f'event: error\ndata: {json.dumps({"error": "not found"})}\n\n'
            return

        # Check Redis first
        from server.services.redis_client import get_redis, redis_key
        r = get_redis()

        while True:
            db.session.refresh(gen)
            data = gen.to_dict()
            yield f'event: progress\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'

            if gen.status in ('completed', 'failed'):
                yield f'event: done\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
                break

            time.sleep(1)

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
