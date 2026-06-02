from flask import request, jsonify
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.memory import NovelMemory, NovelMemoryChange
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/memories', methods=['GET'])
def list_memories(project_id):
    NovelProject.query.get_or_404(project_id)
    query = NovelMemory.query.filter_by(project_id=project_id)

    memory_type = request.args.get('memory_type')
    if memory_type:
        query = query.filter_by(memory_type=memory_type)

    source_type = request.args.get('source_type')
    if source_type:
        query = query.filter_by(source_type=source_type)

    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            db.or_(
                NovelMemory.title.contains(keyword),
                NovelMemory.content.contains(keyword),
            )
        )

    query = query.order_by(NovelMemory.importance.desc(), NovelMemory.updated_at.desc())
    memories = query.all()
    return jsonify([m.to_dict() for m in memories])


@novels_bp.route('/api/novels/<int:project_id>/memories', methods=['POST'])
def create_memory(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    if not data.get('content'):
        return jsonify({'error': '内容不能为空'}), 400

    memory = NovelMemory(
        project_id=project_id,
        title=data.get('title'),
        content=data['content'],
        memory_type=data.get('memory_type', 'general'),
        source_type=data.get('source_type', 'manual_note'),
        source_id=data.get('source_id'),
        summary=data.get('summary'),
        importance=data.get('importance', 3),
        status=data.get('status', 'active'),
        vector_status='pending',
    )
    if 'metadata' in data:
        memory.metadata_ = data['metadata']

    db.session.add(memory)
    db.session.commit()
    return jsonify(memory.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/memories/<int:memory_id>', methods=['PATCH'])
def update_memory(project_id, memory_id):
    NovelProject.query.get_or_404(project_id)
    memory = NovelMemory.query.get_or_404(memory_id)
    if memory.project_id != project_id:
        return jsonify({'error': '记忆不属于该项目'}), 400

    data = request.get_json() or {}

    for field in ('title', 'content', 'summary', 'memory_type', 'source_type',
                  'importance', 'status'):
        if field in data:
            setattr(memory, field, data[field])

    if 'metadata' in data:
        memory.metadata_ = data['metadata']

    if 'content' in data:
        memory.vector_status = 'pending'

    db.session.commit()
    return jsonify(memory.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/memories/<int:memory_id>', methods=['DELETE'])
def delete_memory(project_id, memory_id):
    NovelProject.query.get_or_404(project_id)
    memory = NovelMemory.query.get_or_404(memory_id)
    if memory.project_id != project_id:
        return jsonify({'error': '记忆不属于该项目'}), 400

    db.session.delete(memory)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/memory-changes', methods=['GET'])
def list_memory_changes(project_id):
    NovelProject.query.get_or_404(project_id)
    changes = NovelMemoryChange.query.filter_by(project_id=project_id) \
        .order_by(NovelMemoryChange.created_at.desc()).all()
    return jsonify([c.to_dict() for c in changes])
