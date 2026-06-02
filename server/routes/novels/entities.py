# server/routes/novels/entities.py
from flask import request, jsonify
from server.models import db
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/entities', methods=['GET'])
def list_entities(project_id):
    NovelProject.query.get_or_404(project_id)
    entity_type = request.args.get('type')
    query = NovelEntity.query.filter_by(project_id=project_id)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    query = query.order_by(NovelEntity.importance.desc())
    entities = query.all()
    return jsonify([e.to_dict() for e in entities])


@novels_bp.route('/api/novels/<int:project_id>/entities', methods=['POST'])
def create_entity(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': '名称不能为空'}), 400

    entity = NovelEntity(
        project_id=project_id,
        entity_type=data.get('entity_type', 'character'),
        name=data['name'],
        summary=data.get('summary'),
        importance=data.get('importance', 5),
        node_x=data.get('node_x', 0),
        node_y=data.get('node_y', 0),
    )
    if 'aliases' in data:
        entity.aliases = data['aliases']
    if 'attributes' in data:
        entity.attributes = data['attributes']

    db.session.add(entity)
    db.session.commit()
    return jsonify(entity.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/entities/<int:entity_id>', methods=['GET'])
def get_entity(project_id, entity_id):
    entity = NovelEntity.query.get_or_404(entity_id)
    if entity.project_id != project_id:
        return jsonify({'error': '实体不属于该项目'}), 400
    return jsonify(entity.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/entities/<int:entity_id>', methods=['PUT'])
def update_entity(project_id, entity_id):
    entity = NovelEntity.query.get_or_404(entity_id)
    if entity.project_id != project_id:
        return jsonify({'error': '实体不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('entity_type', 'name', 'summary', 'importance', 'node_x', 'node_y'):
        if field in data:
            setattr(entity, field, data[field])
    if 'aliases' in data:
        entity.aliases = data['aliases']
    if 'attributes' in data:
        entity.attributes = data['attributes']

    db.session.commit()
    return jsonify(entity.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/entities/<int:entity_id>', methods=['DELETE'])
def delete_entity(project_id, entity_id):
    entity = NovelEntity.query.get_or_404(entity_id)
    if entity.project_id != project_id:
        return jsonify({'error': '实体不属于该项目'}), 400

    # Delete related relations
    NovelRelation.query.filter(
        (NovelRelation.source_entity_id == entity_id) |
        (NovelRelation.target_entity_id == entity_id)
    ).delete()

    db.session.delete(entity)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/relations', methods=['GET'])
def list_relations(project_id):
    NovelProject.query.get_or_404(project_id)
    relations = NovelRelation.query.filter_by(project_id=project_id).all()
    return jsonify([r.to_dict() for r in relations])


@novels_bp.route('/api/novels/<int:project_id>/relations', methods=['POST'])
def create_relation(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('source_entity_id') or not data.get('target_entity_id'):
        return jsonify({'error': '源实体和目标实体不能为空'}), 400
    if not data.get('relation_type'):
        return jsonify({'error': '关系类型不能为空'}), 400

    relation = NovelRelation(
        project_id=project_id,
        source_entity_id=data['source_entity_id'],
        target_entity_id=data['target_entity_id'],
        relation_type=data['relation_type'],
        label=data.get('label'),
        description=data.get('description'),
        strength=data.get('strength', 0.5),
        status=data.get('status', 'active'),
    )
    if 'evidence' in data:
        relation.evidence = data['evidence']

    db.session.add(relation)
    db.session.commit()
    return jsonify(relation.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/relations/<int:relation_id>', methods=['PUT'])
def update_relation(project_id, relation_id):
    relation = NovelRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('relation_type', 'label', 'description', 'strength', 'status',
                  'source_entity_id', 'target_entity_id'):
        if field in data:
            setattr(relation, field, data[field])
    if 'evidence' in data:
        relation.evidence = data['evidence']

    db.session.commit()
    return jsonify(relation.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/relations/<int:relation_id>', methods=['DELETE'])
def delete_relation(project_id, relation_id):
    relation = NovelRelation.query.get_or_404(relation_id)
    if relation.project_id != project_id:
        return jsonify({'error': '关系不属于该项目'}), 400
    db.session.delete(relation)
    db.session.commit()
    return '', 204
