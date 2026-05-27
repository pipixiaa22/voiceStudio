import json
import os
from datetime import datetime, timezone
from server.models.base import db


class VideoTemplate(db.Model):
    __tablename__ = 'video_templates'

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    config_json = db.Column(db.Text, nullable=False, default='{}')
    is_builtin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'template_key': self.template_key,
            'name': self.name,
            'config': json.loads(self.config_json) if self.config_json else {},
            'is_builtin': self.is_builtin,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoJob(db.Model):
    __tablename__ = 'video_jobs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False, default='未命名')
    status = db.Column(db.String(20), nullable=False, default='queued')
    progress = db.Column(db.Float, default=0.0)
    stage = db.Column(db.String(50))
    message = db.Column(db.String(500))
    request_json = db.Column(db.Text, nullable=False, default='{}')
    manifest_json = db.Column(db.Text)
    output_path = db.Column(db.String(500))
    video_path = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'stage': self.stage,
            'message': self.message,
            'error_message': self.error_message,
            'has_video': bool(self.video_path and os.path.exists(self.video_path)),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoAsset(db.Model):
    __tablename__ = 'video_assets'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'asset_type': self.asset_type,
            'filename': self.filename,
            'path': self.path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
