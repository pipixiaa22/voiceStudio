# server/routes/novels/outline.py
from flask import request, jsonify
from server.models import db
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.project import NovelProject
from server.routes.novels import novels_bp


@novels_bp.route('/api/novels/<int:project_id>/outline', methods=['GET'])
def get_outline(project_id):
    NovelProject.query.get_or_404(project_id)
    roots = NovelOutlineNode.query.filter_by(
        project_id=project_id, parent_id=None
    ).order_by(NovelOutlineNode.order_index).all()
    return jsonify([r.to_tree_dict() for r in roots])


@novels_bp.route('/api/novels/<int:project_id>/outline', methods=['POST'])
def create_outline_node(project_id):
    NovelProject.query.get_or_404(project_id)
    data = request.get_json() or {}
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400

    # Validate parent belongs to same project
    parent_id = data.get('parent_id')
    if parent_id:
        parent = NovelOutlineNode.query.get_or_404(parent_id)
        if parent.project_id != project_id:
            return jsonify({'error': '父节点不属于该项目'}), 400

    # Auto-calculate order_index
    max_order = db.session.query(db.func.max(NovelOutlineNode.order_index)).filter_by(
        project_id=project_id, parent_id=parent_id
    ).scalar() or 0

    node = NovelOutlineNode(
        project_id=project_id,
        parent_id=parent_id,
        node_type=data.get('node_type', 'chapter'),
        title=data['title'],
        summary=data.get('summary'),
        order_index=data.get('order_index', max_order + 1),
        target_words=data.get('target_words'),
        plot_goal=data.get('plot_goal'),
        conflict_goal=data.get('conflict_goal'),
        status=data.get('status', 'planning'),
    )
    if 'characters' in data:
        node.characters = data['characters']
    if 'events' in data:
        node.events = data['events']
    if 'foreshadowing' in data:
        node.foreshadowing = data['foreshadowing']

    db.session.add(node)
    db.session.commit()
    return jsonify(node.to_dict()), 201


@novels_bp.route('/api/novels/<int:project_id>/outline/<int:node_id>', methods=['PUT'])
def update_outline_node(project_id, node_id):
    node = NovelOutlineNode.query.get_or_404(node_id)
    if node.project_id != project_id:
        return jsonify({'error': '节点不属于该项目'}), 400

    data = request.get_json() or {}
    for field in ('title', 'summary', 'order_index', 'target_words', 'plot_goal',
                  'conflict_goal', 'node_type', 'status'):
        if field in data:
            setattr(node, field, data[field])
    if 'characters' in data:
        node.characters = data['characters']
    if 'events' in data:
        node.events = data['events']
    if 'foreshadowing' in data:
        node.foreshadowing = data['foreshadowing']

    db.session.commit()
    return jsonify(node.to_dict())


@novels_bp.route('/api/novels/<int:project_id>/outline/<int:node_id>', methods=['DELETE'])
def delete_outline_node(project_id, node_id):
    node = NovelOutlineNode.query.get_or_404(node_id)
    if node.project_id != project_id:
        return jsonify({'error': '节点不属于该项目'}), 400

    db.session.delete(node)
    db.session.commit()
    return '', 204
