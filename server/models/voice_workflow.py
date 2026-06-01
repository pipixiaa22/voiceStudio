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


class VoiceWorkflow(db.Model):
    __tablename__ = 'voice_workflows'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='未命名配音工程')
    source_text_id = db.Column(db.Integer, db.ForeignKey('texts.id'), nullable=True)
    source_content = db.Column(db.Text, nullable=False, default='')
    default_voice_profile_id = db.Column(db.Integer, nullable=True)
    settings_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    segments = db.relationship(
        'VoiceWorkflowSegment',
        backref='workflow',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='VoiceWorkflowSegment.order_index',
    )
    edges = db.relationship(
        'VoiceWorkflowEdge',
        backref='workflow',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='VoiceWorkflowEdge.order_index',
    )

    @property
    def settings(self):
        return _json_loads(self.settings_json, {})

    @settings.setter
    def settings(self, value):
        self.settings_json = _json_dumps(value)

    def to_dict(self, include_children=False):
        data = {
            'id': self.id,
            'title': self.title,
            'source_text_id': self.source_text_id,
            'source_content': self.source_content,
            'default_voice_profile_id': self.default_voice_profile_id,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            data['segments'] = [segment.to_dict() for segment in self.segments]
            data['edges'] = [edge.to_dict() for edge in self.edges]
        else:
            data['segment_count'] = len(self.segments)
            data['edge_count'] = len(self.edges)
        return data


class VoiceWorkflowSegment(db.Model):
    __tablename__ = 'voice_workflow_segments'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('voice_workflows.id'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=1)
    text = db.Column(db.Text, nullable=False, default='')
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    emotion = db.Column(db.String(50), nullable=False, default='neutral')
    intensity = db.Column(db.Float, nullable=False, default=0.5)
    rate = db.Column(db.Float, nullable=False, default=1.0)
    pitch = db.Column(db.Float, nullable=False, default=0.0)
    volume_db = db.Column(db.Float, nullable=False, default=0.0)
    pause_before_ms = db.Column(db.Integer, nullable=False, default=0)
    pause_after_ms = db.Column(db.Integer, nullable=False, default=250)
    transition = db.Column(db.String(50), nullable=False, default='normal')
    delivery_instruction = db.Column(db.Text, nullable=False, default='')
    voice_profile_id = db.Column(db.Integer, nullable=True)
    audio_status = db.Column(db.String(30), nullable=False, default='missing')
    audio_path = db.Column(db.Text, nullable=True)
    audio_fingerprint = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'order_index': self.order_index,
            'text': self.text,
            'node_x': self.node_x,
            'node_y': self.node_y,
            'emotion': self.emotion,
            'intensity': self.intensity,
            'rate': self.rate,
            'pitch': self.pitch,
            'volume_db': self.volume_db,
            'pause_before_ms': self.pause_before_ms,
            'pause_after_ms': self.pause_after_ms,
            'transition': self.transition,
            'delivery_instruction': self.delivery_instruction,
            'voice_profile_id': self.voice_profile_id,
            'audio_status': self.audio_status,
            'audio_path': self.audio_path,
            'audio_fingerprint': self.audio_fingerprint,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VoiceWorkflowEdge(db.Model):
    __tablename__ = 'voice_workflow_edges'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('voice_workflows.id'), nullable=False)
    source_segment_id = db.Column(db.Integer, db.ForeignKey('voice_workflow_segments.id'), nullable=False)
    target_segment_id = db.Column(db.Integer, db.ForeignKey('voice_workflow_segments.id'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'source_segment_id': self.source_segment_id,
            'target_segment_id': self.target_segment_id,
            'order_index': self.order_index,
        }
