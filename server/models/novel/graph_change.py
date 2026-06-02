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


class NovelGraphChange(db.Model):
    __tablename__ = 'novel_graph_changes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=True)
    change_type = db.Column(db.String(10), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(20), nullable=False, default='manual')
    confidence = db.Column(db.Float, nullable=True)
    accepted = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)

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
            'chapter_id': self.chapter_id,
            'change_type': self.change_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'before': self.before,
            'after': self.after,
            'source': self.source,
            'confidence': self.confidence,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class NovelGeneration(db.Model):
    __tablename__ = 'novel_generations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    generation_type = db.Column(db.String(30), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    progress = db.Column(db.Integer, nullable=False, default=0)
    result_json = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    completed_at = db.Column(db.DateTime, nullable=True)

    @property
    def result(self):
        return _json_loads(self.result_json, None)

    @result.setter
    def result(self, value):
        self.result_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'generation_type': self.generation_type,
            'target_id': self.target_id,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'model': self.model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
