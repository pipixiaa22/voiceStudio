from flask import Blueprint, request, jsonify
from server.models import db, Text, Tag

texts_bp = Blueprint('texts', __name__)


@texts_bp.route('/api/texts', methods=['GET'])
def get_texts():
    query = Text.query

    folder_id = request.args.get('folder_id')
    if folder_id:
        query = query.filter_by(folder_id=folder_id)

    tag_name = request.args.get('tag')
    if tag_name:
        query = query.filter(Text.tags.any(Tag.name == tag_name))

    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    sort_column = getattr(Text, sort_by, Text.created_at)
    query = query.order_by(sort_column.desc() if order == 'desc' else sort_column.asc())

    texts = query.all()
    return jsonify([t.to_dict() for t in texts])


@texts_bp.route('/api/texts', methods=['POST'])
def create_text():
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': '内容不能为空'}), 400

    text = Text(
        title=data.get('title', '未命名'),
        content=data['content'],
        folder_id=data.get('folder_id'),
    )

    tag_ids = data.get('tag_ids', [])
    if tag_ids:
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        text.tags = tags

    db.session.add(text)
    db.session.commit()
    return jsonify(text.to_dict()), 201


@texts_bp.route('/api/texts/<int:text_id>', methods=['PUT'])
def update_text(text_id):
    text = Text.query.get_or_404(text_id)
    data = request.get_json()

    if 'title' in data:
        text.title = data['title']
    if 'content' in data:
        text.content = data['content']
    if 'folder_id' in data:
        text.folder_id = data['folder_id']
    if 'tag_ids' in data:
        tags = Tag.query.filter(Tag.id.in_(data['tag_ids'])).all()
        text.tags = tags

    db.session.commit()
    return jsonify(text.to_dict())


@texts_bp.route('/api/texts/<int:text_id>', methods=['DELETE'])
def delete_text(text_id):
    text = Text.query.get_or_404(text_id)
    db.session.delete(text)
    db.session.commit()
    return '', 204
