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


class NovelEntity(db.Model):
    __tablename__ = 'novel_entities'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False, default='character')
    name = db.Column(db.String(100), nullable=False)
    aliases_json = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    attributes_json = db.Column(db.Text, nullable=True)
    importance = db.Column(db.Integer, nullable=False, default=5)
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    @property
    def aliases(self):
        return _json_loads(self.aliases_json, [])

    @aliases.setter
    def aliases(self, value):
        self.aliases_json = _json_dumps(value)

    @property
    def attributes(self):
        return _json_loads(self.attributes_json, {})

    @attributes.setter
    def attributes(self, value):
        self.attributes_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'entity_type': self.entity_type,
            'name': self.name,
            'aliases': self.aliases,
            'summary': self.summary,
            'attributes': self.attributes,
            'importance': self.importance,
            'node_x': self.node_x,
            'node_y': self.node_y,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NovelRelation(db.Model):
    __tablename__ = 'novel_relations'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('novel_projects.id'), nullable=False)
    source_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=False)
    target_entity_id = db.Column(db.Integer, db.ForeignKey('novel_entities.id'), nullable=False)
    relation_type = db.Column(db.String(30), nullable=False)
    label = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    strength = db.Column(db.Float, nullable=False, default=0.5)
    status = db.Column(db.String(20), nullable=False, default='active')
    evidence_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    source_entity = db.relationship('NovelEntity', foreign_keys=[source_entity_id], backref='outgoing_relations')
    target_entity = db.relationship('NovelEntity', foreign_keys=[target_entity_id], backref='incoming_relations')

    @property
    def evidence(self):
        return _json_loads(self.evidence_json, [])

    @evidence.setter
    def evidence(self, value):
        self.evidence_json = _json_dumps(value)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'source_entity_id': self.source_entity_id,
            'target_entity_id': self.target_entity_id,
            'relation_type': self.relation_type,
            'label': self.label,
            'description': self.description,
            'strength': self.strength,
            'status': self.status,
            'evidence': self.evidence,
            'source_name': self.source_entity.name if self.source_entity else None,
            'target_name': self.target_entity.name if self.target_entity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
