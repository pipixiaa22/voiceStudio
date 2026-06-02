# server/routes/novels/events.py
from flask import request, jsonify
from server.models import db
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/events', methods=['GET'])
def list_events(project_id):
    NovelProject.query.get_or_404(project_id)
    events = NovelEvent.query.filter_by(
        project_id=project_id
    ).order_by(NovelEvent.timeline_order).all()
    return jsonify([e.to_dict() for e in events])


@novels_bp.route('/api/novels/<int:project_id>/events', methods=['POST'])
def create_event(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400

    event = NovelEvent(
        project_id=project_id,
        chapter_id=data.get('chapter_id'),
        title=data['title'],
        summary=data.get('summary'),
        event_type=data.get('event_type', 'event'),
        timeline_order=data.get('timeline_order', 0),
        location_entity_id=data.get('location_entity_id'),
        node_x=data.get('node_x', 0),
        node_y=data.get('node_y', 0),
    )
    if 'participants' in data:
        event.participants = data['participants']
    if 'effects' in data:
        event.effects = data['effects']

    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/events/<int:event_id>', methods=['GET'])
def get_event(project_id, event_id):
    event = NovelEvent.query.get_or_404(event_id)
    if event.project_id != project_id:
        return jsonify({'error': '事件不属于该项目'}), 400
    return jsonify(event.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/events/<int:event_id>', methods=['PUT'])
def update_event(project_id, event_id):
    event = NovelEvent.query.get_or_404(event_id)
    if event.project_id != project_id:
        return jsonify({'error': '事件不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('title', 'summary', 'event_type', 'timeline_order',
                  'chapter_id', 'location_entity_id', 'node_x', 'node_y'):
        if field in data:
            setattr(event, field, data[field])
    if 'participants' in data:
        event.participants = data['participants']
    if 'effects' in data:
        event.effects = data['effects']

    db.session.commit()
    return jsonify(event.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/events/<int:event_id>', methods=['DELETE'])
def delete_event(project_id, event_id):
    event = NovelEvent.query.get_or_404(event_id)
    if event.project_id != project_id:
        return jsonify({'error': '事件不属于该项目'}), 400

    # Delete related event relations
    NovelEventRelation.query.filter(
        (NovelEventRelation.source_event_id == event_id) |
        (NovelEventRelation.target_event_id == event_id)
    ).delete()

    db.session.delete(event)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/event-relations', methods=['POST'])
def create_event_relation(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('source_event_id') or not data.get('target_event_id'):
        return jsonify({'error': '源事件和目标事件不能为空'}), 400
    if not data.get('relation_type'):
        return jsonify({'error': '关系类型不能为空'}), 400

    relation = NovelEventRelation(
        project_id=project_id,
        source_event_id=data['source_event_id'],
        target_event_id=data['target_event_id'],
        relation_type=data['relation_type'],
        label=data.get('label'),
        description=data.get('description'),
        confidence=data.get('confidence', 1.0),
    )
    db.session.add(relation)
    db.session.commit()
    return jsonify(relation.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/event-relations/<int:relation_id>', methods=['PUT'])
def update_event_relation(project_id, relation_id):
    relation = NovelEventRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('relation_type', 'label', 'description', 'confidence'):
        if field in data:
            setattr(relation, field, data[field])

    db.session.commit()
    return jsonify(relation.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/event-relations/<int:relation_id>', methods=['DELETE'])
def delete_event_relation(project_id, relation_id):
    relation = NovelEventRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400
    db.session.delete(relation)
    db.session.commit()
    return '', 204
