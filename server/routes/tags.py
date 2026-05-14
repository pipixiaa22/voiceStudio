from flask import Blueprint, request, jsonify
from server.models import db, Tag

tags_bp = Blueprint('tags', __name__)


@tags_bp.route('/api/tags', methods=['GET'])
def get_tags():
    tags = Tag.query.order_by(Tag.name).all()
    return jsonify([t.to_dict() for t in tags])


@tags_bp.route('/api/tags', methods=['POST'])
def create_tag():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '标签名称不能为空'}), 400

    if Tag.query.filter_by(name=data['name']).first():
        return jsonify({'error': '标签已存在'}), 409

    tag = Tag(name=data['name'])
    db.session.add(tag)
    db.session.commit()
    return jsonify(tag.to_dict()), 201
