from flask import Blueprint, request, jsonify
from server.models import db, Folder

folders_bp = Blueprint('folders', __name__)


@folders_bp.route('/api/folders', methods=['GET'])
def get_folders():
    folders = Folder.query.order_by(Folder.created_at).all()
    return jsonify([f.to_dict() for f in folders])


@folders_bp.route('/api/folders', methods=['POST'])
def create_folder():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '文件夹名称不能为空'}), 400

    folder = Folder(name=data['name'], parent_id=data.get('parent_id'))
    db.session.add(folder)
    db.session.commit()
    return jsonify(folder.to_dict()), 201


@folders_bp.route('/api/folders/<int:folder_id>', methods=['PUT'])
def update_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    data = request.get_json()

    if 'name' in data:
        folder.name = data['name']
    if 'parent_id' in data:
        folder.parent_id = data['parent_id']

    db.session.commit()
    return jsonify(folder.to_dict())


@folders_bp.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    db.session.delete(folder)
    db.session.commit()
    return '', 204
