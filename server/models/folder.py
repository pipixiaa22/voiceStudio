from datetime import datetime, timezone
from server.models.base import db


class Folder(db.Model):
    __tablename__ = 'folders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    parent = db.relationship('Folder', remote_side=[id], backref=db.backref('children', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
