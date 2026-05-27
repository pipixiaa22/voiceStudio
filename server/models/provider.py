import json
from datetime import datetime, timezone
from server.models.base import db


class CustomProvider(db.Model):
    __tablename__ = 'custom_providers'

    id = db.Column(db.Integer, primary_key=True)
    provider_key = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(500), nullable=False, default='')
    models_json = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'provider_key': self.provider_key,
            'display_name': self.display_name,
            'base_url': self.base_url,
            'models': json.loads(self.models_json) if self.models_json else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
