import json
from datetime import datetime, timezone
from server.models.base import db


def _now():
    return datetime.now(timezone.utc)


def _json_loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _json_dumps(value):
    return json.dumps(value or {}, ensure_ascii=False)


class NovelOutlineNode(db.Model):
    __tablename__ = 'novel_outline_nodes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('novel_outline_nodes.id'), nullable=True)
    node_type = db.Column(db.String(20), nullable=False, default='chapter')
    title = db.Column(db.String(200), nullable=False, default='未命名节点')
    summary = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    target_words = db.Column(db.Integer, nullable=True)
    plot_goal = db.Column(db.Text, nullable=True)
    conflict_goal = db.Column(db.Text, nullable=True)
    characters_json = db.Column(db.Text, nullable=True)
    events_json = db.Column(db.Text, nullable=True)
    foreshadowing_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='planning')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    children = db.relationship(
        'NovelOutlineNode',
        backref=db.backref('parent', remote_side='NovelOutlineNode.id'),
        lazy=True,
        cascade='all, delete-orphan',
        order_by='NovelOutlineNode.order_index',
    )

    @property
    def characters(self):
        return _json_loads(self.characters_json, [])

    @characters.setter
    def characters(self, value):
        self.characters_json = _json_dumps(value)

    @property
    def events(self):
        return _json_loads(self.events_json, [])

    @events.setter
    def events(self, value):
        self.events_json = _json_dumps(value)

    @property
    def foreshadowing(self):
        return _json_loads(self.foreshadowing_json, [])

    @foreshadowing.setter
    def foreshadowing(self, value):
        self.foreshadowing_json = _json_dumps(value)

    def to_dict(self, include_children=False):
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'node_type': self.node_type,
            'title': self.title,
            'summary': self.summary,
            'order_index': self.order_index,
            'target_words': self.target_words,
            'plot_goal': self.plot_goal,
            'conflict_goal': self.conflict_goal,
            'characters': self.characters,
            'events': self.events,
            'foreshadowing': self.foreshadowing,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            data['children'] = [c.to_dict(include_children=True) for c in self.children]
        return data

    def to_tree_dict(self):
        """Return tree structure with nested children."""
        data = self.to_dict()
        data['children'] = [c.to_tree_dict() for c in self.children]
        return data
