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


class NovelProject(db.Model):
    __tablename__ = 'novel_projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='未命名小说')
    genre = db.Column(db.String(50), nullable=False, default='玄幻')
    premise = db.Column(db.Text, nullable=True)
    target_total_words = db.Column(db.Integer, nullable=False, default=300000)
    target_chapters = db.Column(db.Integer, nullable=False, default=100)
    words_per_chapter = db.Column(db.Integer, nullable=False, default=3000)
    volume_count = db.Column(db.Integer, nullable=False, default=1)
    style_guide_json = db.Column(db.Text, nullable=True)
    settings_json = db.Column(db.Text, nullable=True)
    knowledge_update_mode = db.Column(db.String(20), nullable=False, default='ai_confirm')
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    @property
    def style_guide(self):
        return _json_loads(self.style_guide_json, {})

    @style_guide.setter
    def style_guide(self, value):
        self.style_guide_json = _json_dumps(value)

    @property
    def settings(self):
        return _json_loads(self.settings_json, {})

    @settings.setter
    def settings(self, value):
        self.settings_json = _json_dumps(value)

    def to_dict(self, include_stats=False):
        data = {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'premise': self.premise,
            'target_total_words': self.target_total_words,
            'target_chapters': self.target_chapters,
            'words_per_chapter': self.words_per_chapter,
            'volume_count': self.volume_count,
            'style_guide': self.style_guide,
            'settings': self.settings,
            'knowledge_update_mode': self.knowledge_update_mode,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_stats:
            from server.models.novel.chapter import NovelChapter
            chapters = NovelChapter.query.filter_by(project_id=self.id).all()
            data['stats'] = {
                'chapter_count': len(chapters),
                'total_words': sum(c.word_count for c in chapters),
                'confirmed_chapters': sum(1 for c in chapters if c.status == 'confirmed'),
            }
        return data
