import logging
from flask import request, jsonify
from server.models import db
from server.models.novel.project import NovelProject
from server.models.novel.memory import NovelMemory, NovelMemoryChange
from server.routes.novels import novels_bp

logger = logging.getLogger(__name__)


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

    from server.services.memory.document_types import MEMORY_TYPES
    memory_type = data.get('memory_type', 'summary')
    if memory_type not in MEMORY_TYPES:
        return jsonify({'error': f'无效的记忆类型: {memory_type}'}), 400

    importance = data.get('importance', 3)
    if not isinstance(importance, int) or not (1 <= importance <= 5):
        importance = 3

    memory = NovelMemory(
        project_id=project_id,
        title=data.get('title'),
        content=data['content'],
        memory_type=memory_type,
        source_type=data.get('source_type', 'manual_note'),
        source_id=data.get('source_id'),
        summary=data.get('summary'),
        importance=importance,
        status=data.get('status', 'active'),
        vector_status='pending',
    )
    if 'metadata' in data:
        memory.metadata_ = data['metadata']

    db.session.add(memory)
    db.session.commit()

    # Index into vector store (best effort)
    try:
        from server.services.memory.memory_writer import index_memory
        index_memory(memory)
    except Exception:
        logger.exception('Failed to index new memory %s', memory.id)

    return jsonify(memory.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/memories/<int:memory_id>', methods=['PATCH'])
def update_memory(project_id, memory_id):
    NovelProject.query.get_or_404(project_id)
    memory = NovelMemory.query.get_or_404(memory_id)
    if memory.project_id != project_id:
        return jsonify({'error': '记忆不属于该项目'}), 400

    data = request.get_json() or {}

    from server.services.memory.document_types import MEMORY_TYPES

    # Validate memory_type if provided
    if 'memory_type' in data and data['memory_type'] not in MEMORY_TYPES:
        return jsonify({'error': f'无效的记忆类型: {data["memory_type"]}'}), 400

    # Validate and clamp importance if provided
    if 'importance' in data:
        imp = data['importance']
        if not isinstance(imp, int) or not (1 <= imp <= 5):
            return jsonify({'error': '重要性必须是 1-5 的整数'}), 400

    for field in ('title', 'content', 'summary', 'memory_type', 'source_type',
                  'importance', 'status'):
        if field in data:
            setattr(memory, field, data[field])

    if 'metadata' in data:
        memory.metadata_ = data['metadata']

    needs_reindex = any(k in data for k in ('content', 'memory_type', 'importance'))
    if needs_reindex:
        memory.vector_status = 'pending'

    db.session.commit()

    # Re-index if content or metadata-affecting fields changed (best effort)
    if needs_reindex:
        try:
            from server.services.memory.memory_writer import index_memory
            index_memory(memory)
        except Exception:
            logger.exception('Failed to re-index memory %s', memory_id)

    return jsonify(memory.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/memories/<int:memory_id>', methods=['DELETE'])
def delete_memory(project_id, memory_id):
    NovelProject.query.get_or_404(project_id)
    memory = NovelMemory.query.get_or_404(memory_id)
    if memory.project_id != project_id:
        return jsonify({'error': '记忆不属于该项目'}), 400

    # Delete from vector store first (best effort)
    try:
        from server.services.memory.vector_store import delete_by_memory_id
        delete_by_memory_id(project_id, memory_id)
    except Exception:
        logger.exception('Failed to delete vectors for memory %s', memory_id)

    db.session.delete(memory)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/memory-changes', methods=['GET'])
def list_memory_changes(project_id):
    NovelProject.query.get_or_404(project_id)
    changes = NovelMemoryChange.query.filter_by(project_id=project_id, status='pending') \
        .order_by(NovelMemoryChange.created_at.desc()).all()
    return jsonify([c.to_dict() for c in changes])


@novels_bp.route('/api/novels/<int:project_id>/memory-changes/<int:change_id>/confirm', methods=['POST'])
def confirm_memory_change(project_id, change_id):
    NovelProject.query.get_or_404(project_id)
    change = NovelMemoryChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return jsonify({'error': '变更不属于该项目'}), 400

    if change.status != 'pending':
        return jsonify(change.to_dict())

    from datetime import datetime, timezone
    after = change.after
    if not after:
        return jsonify({'error': '变更数据为空'}), 400

    target_memory = None
    if change.change_type == 'add':
        from server.services.memory.document_types import MEMORY_TYPES
        memory_type = after.get('memory_type', 'summary')
        if memory_type not in MEMORY_TYPES:
            memory_type = 'summary'
        importance = after.get('importance', 3)
        if not isinstance(importance, int) or not (1 <= importance <= 5):
            importance = 3

        memory = NovelMemory(
            project_id=project_id,
            source_type=after.get('source_type', 'ai_extract'),
            source_id=after.get('source_id'),
            memory_type=memory_type,
            title=after.get('title'),
            content=after.get('content', ''),
            summary=after.get('summary'),
            importance=importance,
            status='active',
            vector_status='pending',
        )
        db.session.add(memory)
        db.session.flush()
        change.memory_id = memory.id
        target_memory = memory
    elif change.change_type == 'modify':
        if not change.memory_id:
            return jsonify({'error': '无目标记忆'}), 400
        memory = NovelMemory.query.get(change.memory_id)
        if not memory:
            return jsonify({'error': '目标记忆已删除'}), 404
        # Validate fields before applying
        if 'memory_type' in after and after['memory_type'] not in MEMORY_TYPES:
            after['memory_type'] = memory.memory_type  # keep existing
        if 'importance' in after:
            imp = after['importance']
            if not isinstance(imp, int) or not (1 <= imp <= 5):
                after['importance'] = memory.importance  # keep existing
        for field in ('title', 'content', 'summary', 'importance', 'memory_type'):
            if field in after:
                setattr(memory, field, after[field])
        memory.vector_status = 'pending'
        target_memory = memory

    change.status = 'confirmed'
    change.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()

    # Index the memory into vector store (best effort)
    if target_memory:
        try:
            from server.services.memory.memory_writer import index_memory
            index_memory(target_memory)
        except Exception:
            logger.exception('Failed to index confirmed memory %s', target_memory.id)

    return jsonify(change.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/memory-changes/<int:change_id>/reject', methods=['POST'])
def reject_memory_change(project_id, change_id):
    NovelProject.query.get_or_404(project_id)
    change = NovelMemoryChange.query.get_or_404(change_id)
    if change.project_id != project_id:
        return jsonify({'error': '变更不属于该项目'}), 400

    if change.status != 'pending':
        return jsonify(change.to_dict())

    change.status = 'rejected'
    db.session.commit()
    return jsonify(change.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/memories/reindex', methods=['POST'])
def reindex_memories(project_id):
    NovelProject.query.get_or_404(project_id)
    memories = NovelMemory.query.filter_by(project_id=project_id, status='active').all()

    # Mark all as pending BEFORE rebuilding so crash doesn't leave stale 'indexed'
    for mem in memories:
        mem.vector_status = 'pending'
    db.session.flush()

    from server.services.memory.vector_store import rebuild_index
    count = rebuild_index(project_id, memories)

    # Only mark as indexed if chunks were actually indexed
    if count > 0:
        for mem in memories:
            mem.vector_status = 'indexed'

    db.session.commit()

    return jsonify({'indexed_chunks': count, 'memories': len(memories)})


@novels_bp.route('/api/novels/<int:project_id>/memories/search', methods=['POST'])
def search_memories(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    query = data.get('query', '')
    try:
        k = int(data.get('k', 10))
    except (ValueError, TypeError):
        k = 10
    k = max(1, min(k, 50))
    memory_type = data.get('memory_type')

    from server.services.memory.retriever import retrieve_memories, retrieve_by_type

    if memory_type:
        results = retrieve_by_type(project_id, memory_type, query, k=k)
    else:
        results = retrieve_memories(project_id, query, k=k)

    return jsonify({'results': results, 'query': query})
