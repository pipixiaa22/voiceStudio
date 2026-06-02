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


class NovelEvent(db.Model):
    __tablename__ = 'novel_events'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('novel_chapters.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(20), nullable=False, default='event')
    timeline_order = db.Column(db.Float, nullable=False, default=0)
    participants_json = db.Column(db.Text, nullable=True)
    location_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=True)
    effects_json = db.Column(db.Text, nullable=True)
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    location_entity = db.relationship('NovelEntity', foreign_keys=[location_entity_id])

    @property
    def participants(self):
        return _json_loads(self.participants_json, [])

    @participants.setter
    def participants(self, value):
        self.participants_json = _json_dumps(value)

    @property
    def effects(self):
        return _json_loads(self.effects_json, [])

    @effects.setter
    def effects(self, value):
        self.effects_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'chapter_id': self.chapter_id,
            'title': self.title,
            'summary': self.summary,
            'event_type': self.event_type,
            'timeline_order': self.timeline_order,
            'participants': self.participants,
            'location_entity_id': self.location_entity_id,
            'location_name': self.location_entity.name if self.location_entity else None,
            'effects': self.effects,
            'node_x': self.node_x,
            'node_y': self.node_y,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NovelEventRelation(db.Model):
    __tablename__ = 'novel_event_relations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    source_event_id = db.Column(db.Integer, db.ForeignKey('novel_events.id'), nullable=False)
    target_event_id = db.Column(db.Integer, db.ForeignKey('novel_events.id'), nullable=False)
    relation_type = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    source_event = db.relationship('NovelEvent', foreign_keys=[source_event_id], backref='outgoing_event_relations')
    target_event = db.relationship('NovelEvent', foreign_keys=[target_event_id], backref='incoming_event_relations')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'source_event_id': self.source_event_id,
            'target_event_id': self.target_event_id,
            'relation_type': self.relation_type,
            'label': self.label,
            'description': self.description,
            'confidence': self.confidence,
            'source_title': self.source_event.title if self.source_event else None,
            'target_title': self.target_event.title if self.target_event else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
