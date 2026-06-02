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


class NovelMemory(db.Model):
    __tablename__ = 'novel_memories'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False, index=True)
    source_type = db.Column(db.String(40), nullable=False)
    source_id = db.Column(db.Integer, nullable=True)
    memory_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    importance = db.Column(db.Integer, nullable=False, default=3)
    status = db.Column(db.String(20), nullable=False, default='active')
    vector_status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    @property
    def metadata_(self):
        return _json_loads(self.metadata_json, None)

    @metadata_.setter
    def metadata_(self, value):
        self.metadata_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'memory_type': self.memory_type,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'metadata': self.metadata_,
            'importance': self.importance,
            'status': self.status,
            'vector_status': self.vector_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NovelMemoryChange(db.Model):
    __tablename__ = 'novel_memory_changes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False, index=True)
    memory_id = db.Column(db.Integer, nullable=True, index=True)
    change_type = db.Column(db.String(30), nullable=False)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(30), nullable=False, default='user_manual')
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=_now)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    @property
    def before(self):
        return _json_loads(self.before_json, None)

    @before.setter
    def before(self, value):
        self.before_json = _json_dumps(value)

    @property
    def after(self):
        return _json_loads(self.after_json, None)

    @after.setter
    def after(self, value):
        self.after_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'memory_id': self.memory_id,
            'change_type': self.change_type,
            'before': self.before,
            'after': self.after,
            'source': self.source,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
