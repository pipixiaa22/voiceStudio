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
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


class NovelChapter(db.Model):
    __tablename__ = 'novel_chapters'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    outline_node_id = db.Column(db.Integer, db.ForeignKey('novel_outline_nodes.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False, default='未命名章节')
    content_markdown = db.Column(db.Text, nullable=False, default='')
    summary = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    target_words = db.Column(db.Integer, nullable=True)
    word_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    versions = db.relationship(
        'NovelChapterVersion',
        backref='chapter',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='NovelChapterVersion.created_at.desc()',
    )

    def to_dict(self, include_content=True, include_versions=False):
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'outline_node_id': self.outline_node_id,
            'title': self.title,
            'summary': self.summary,
            'order_index': self.order_index,
            'target_words': self.target_words,
            'word_count': self.word_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data['content_markdown'] = self.content_markdown
        if include_versions:
            data['versions'] = [v.to_dict() for v in self.versions]
        return data


class NovelChapterVersion(db.Model):
    __tablename__ = 'novel_chapter_versions'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=False)
    version_type = db.Column(db.String(30), nullable=False, default='custom')
    title = db.Column(db.String(200), nullable=True)
    content_markdown = db.Column(db.Text, nullable=False, default='')
    prompt_json = db.Column(db.Text, nullable=True)
    context_snapshot_json = db.Column(db.Text, nullable=True)
    model = db.Column(db.String(100), nullable=True)
    accepted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=_now)

    @property
    def prompt(self):
        return _json_loads(self.prompt_json, {})

    @prompt.setter
    def prompt(self, value):
        self.prompt_json = _json_dumps(value)

    @property
    def context_snapshot(self):
        return _json_loads(self.context_snapshot_json, {})

    @context_snapshot.setter
    def context_snapshot(self, value):
        self.context_snapshot_json = _json_dumps(value)

    def to_dict(self):
        data = {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'version_type': self.version_type,
            'title': self.title,
            'content_markdown': self.content_markdown,
            'model': self.model,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        snapshot = self.context_snapshot
        if snapshot and isinstance(snapshot, dict) and snapshot.get('chapter_state'):
            data['chapter_state'] = snapshot['chapter_state']
        if hasattr(self, 'generated_graph_changes'):
            data['generated_graph_changes'] = self.generated_graph_changes
        if hasattr(self, 'generated_memory_changes'):
            data['generated_memory_changes'] = self.generated_memory_changes
        return data
