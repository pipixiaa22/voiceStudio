# server/routes/novels/chapters.py
from flask import request, jsonify
from server.models import db
from server.models.novel.chapter import NovelChapter, NovelChapterVersion
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/chapters', methods=['GET'])
def list_chapters(project_id):
    NovelProject.query.get_or_404(project_id)
    chapters = NovelChapter.query.filter_by(
        project_id=project_id
    ).order_by(NovelChapter.order_index).all()
    return jsonify([c.to_dict(include_content=False) for c in chapters])


@novels_bp.route('/api/novels/<int:project_id>/chapters', methods=['POST'])
def create_chapter(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}

    # Validate outline node belongs to this project
    if data.get('outline_node_id'):
        node = NovelOutlineNode.query.get(data['outline_node_id'])
        if not node or node.project_id != project_id:
            return jsonify({'error': '大纲节点不属于该项目'}), 400

    max_order = db.session.query(db.func.max(NovelChapter.order_index)).filter_by(
        project_id=project_id
    ).scalar() or 0

    content = data.get('content_markdown', '')
    chapter = NovelChapter(
        project_id=project_id,
        outline_node_id=data.get('outline_node_id'),
        title=data.get('title', '未命名章节'),
        content_markdown=content,
        order_index=data.get('order_index', max_order + 1),
        target_words=data.get('target_words'),
        word_count=len(content.replace(' ', '').replace('\n', '')),
        status=data.get('status', 'draft'),
    )
    db.session.add(chapter)
    db.session.commit()
    return jsonify(chapter.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    return jsonify(chapter.to_dict(include_versions=True))


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>', methods=['PUT'])
def update_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    if 'title' in data:
        chapter.title = data['title']
    if 'content_markdown' in data:
        chapter.content_markdown = data['content_markdown']
        chapter.word_count = len(data['content_markdown'].replace(' ', '').replace('\n', ''))
    if 'order_index' in data:
        chapter.order_index = data['order_index']
    if 'target_words' in data:
        chapter.target_words = data['target_words']
    if 'outline_node_id' in data and data['outline_node_id']:
        node = NovelOutlineNode.query.get(data['outline_node_id'])
        if not node or node.project_id != project_id:
            return jsonify({'error': '大纲节点不属于该项目'}), 400
        chapter.outline_node_id = data['outline_node_id']
    elif 'outline_node_id' in data:
        chapter.outline_node_id = None

    db.session.commit()
    return jsonify(chapter.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>', methods=['DELETE'])
def delete_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    db.session.delete(chapter)
    db.session.commit()
    return '', 204


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/confirm', methods=['POST'])
def confirm_chapter(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    chapter.status = 'confirmed'
    db.session.commit()
    # Auto-generate summary in background
    try:
        from server.services.novel.summarizer import generate_summary
        generate_summary(chapter_id)
    except Exception:
        pass  # Summary generation failure should not block confirmation
    # Trigger memory extraction in background
    if chapter.content_markdown:
        try:
            from server.services.memory.memory_writer import extract_and_create_changes
            import threading
            threading.Thread(
                target=extract_and_create_changes,
                args=(project_id, chapter_id, chapter.content_markdown),
                daemon=True,
            ).start()
        except Exception:
            pass
    return jsonify(chapter.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/generate-versions', methods=['POST'])
def generate_versions(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400

    data = request.get_json() or {}
    from server.services.novel.generation_runner import start_generation
    gen = start_generation(
        project_id=project_id,
        generation_type='chapter_version',
        target_id=chapter_id,
        params=data,
    )
    return jsonify(gen.to_dict()), 202


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/versions', methods=['GET'])
def list_versions(project_id, chapter_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    versions = NovelChapterVersion.query.filter_by(
        chapter_id=chapter_id
    ).order_by(NovelChapterVersion.created_at.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/versions/<int:version_id>/accept', methods=['POST'])
def accept_version(project_id, chapter_id, version_id):
    chapter = NovelChapter.query.get_or_404(chapter_id)
    if chapter.project_id != project_id:
        return jsonify({'error': '章节不属于该项目'}), 400
    version = NovelChapterVersion.query.get_or_404(version_id)
    if version.chapter_id != chapter_id:
        return jsonify({'error': '版本不属于该章节'}), 400

    # Unaccept all other versions
    NovelChapterVersion.query.filter_by(chapter_id=chapter_id).update({'accepted': False})
    version.accepted = True

    # Copy version content to chapter
    chapter.content_markdown = version.content_markdown
    chapter.word_count = len(version.content_markdown.replace(' ', '').replace('\n', ''))

    db.session.commit()
    return jsonify(chapter.to_dict(include_versions=True))


@novels_bp.route('/api/novels/<int:project_id>/chapters/<int:chapter_id>/versions/<int:version_id>', methods=['DELETE'])
def delete_version(project_id, chapter_id, version_id):
    version = NovelChapterVersion.query.get_or_404(version_id)
    if version.chapter_id != chapter_id:
        return jsonify({'error': '版本不属于该章节'}), 400
    db.session.delete(version)
    db.session.commit()
    return '', 204
