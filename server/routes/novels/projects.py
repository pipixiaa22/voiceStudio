# server/routes/novels/projects.py
from flask import request, jsonify
from server.models import db
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels', methods=['GET'])
def list_projects():
    status = request.args.get('status')
    query = NovelProject.query
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(NovelProject.updated_at.desc())
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [p.to_dict(include_stats=True) for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
    })


@novels_bp.route('/api/novels', methods=['POST'])
def create_project():
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400

    project = NovelProject(
        title=data['title'],
        genre=data.get('genre', '玄幻'),
        premise=data.get('premise'),
        target_total_words=data.get('target_total_words', 300000),
        target_chapters=data.get('target_chapters', 100),
        words_per_chapter=data.get('words_per_chapter', 3000),
        volume_count=data.get('volume_count', 1),
        knowledge_update_mode=data.get('knowledge_update_mode', 'ai_confirm'),
    )
    if 'style_guide' in data:
        project.style_guide = data['style_guide']
    if 'settings' in data:
        project.settings = data['settings']

    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = NovelProject.query.get_or_404(project_id)
    return jsonify(project.to_dict(include_stats=True))


@novels_bp.route('/api/novels/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    for field in ('title', 'genre', 'premise', 'target_total_words', 'target_chapters',
                  'words_per_chapter', 'volume_count', 'knowledge_update_mode', 'status'):
        if field in data:
            setattr(project, field, data[field])
    if 'style_guide' in data:
        project.style_guide = data['style_guide']
    if 'settings' in data:
        project.settings = data['settings']

    db.session.commit()
    return jsonify(project.to_dict())


@novels_bp.route('/api/novels/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = NovelProject.query.get_or_404(project_id)
    # Cascade delete: remove all related data
    from server.models.novel.chapter import NovelChapter, NovelChapterVersion
    from server.models.novel.outline import NovelOutlineNode
    from server.models.novel.entity import NovelEntity, NovelRelation
    from server.models.novel.event import NovelEvent, NovelEventRelation
    from server.models.novel.graph_change import NovelGraphChange, NovelGeneration
    from server.models.novel.memory import NovelMemory, NovelMemoryChange

    # Delete in dependency order (children first, then parents)
    chapter_ids = [c.id for c in NovelChapter.query.filter_by(project_id=project_id).all()]

    # 1. NovelGraphChange references chapter — delete before chapters
    NovelGraphChange.query.filter_by(project_id=project_id).delete()
    # 2. NovelChapterVersion references chapter — delete before chapters
    if chapter_ids:
        NovelChapterVersion.query.filter(NovelChapterVersion.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
    # 3. NovelEventRelation references event — delete before events
    NovelEventRelation.query.filter_by(project_id=project_id).delete()
    # 4. NovelEvent references entity (location_entity_id) and chapter — delete before entity/chapter
    NovelEvent.query.filter_by(project_id=project_id).delete()
    # 5. Now safe to delete chapters and outline
    NovelChapter.query.filter_by(project_id=project_id).delete()
    NovelOutlineNode.query.filter_by(project_id=project_id).delete()
    # 6. NovelRelation references entity — delete before entity
    NovelRelation.query.filter_by(project_id=project_id).delete()
    # 7. Now safe to delete entities
    NovelEntity.query.filter_by(project_id=project_id).delete()
    # 8. NovelGeneration has no FK deps on other novel tables
    NovelGeneration.query.filter_by(project_id=project_id).delete()
    # 9. NovelMemoryChange references memory — delete before memory
    NovelMemoryChange.query.filter_by(project_id=project_id).delete()
    # 10. NovelMemory
    NovelMemory.query.filter_by(project_id=project_id).delete()

    db.session.delete(project)
    db.session.commit()
    return '', 204
