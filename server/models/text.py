from datetime import datetime, timezone
from server.models.base import db

text_tags = db.Table(
    'text_tags',
    db.Column('text_id', db.Integer, db.ForeignKey('texts.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True),
)


class Text(db.Model):
    __tablename__ = 'texts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='未命名')
    content = db.Column(db.Text, nullable=False, default='')
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    folder = db.relationship('Folder', backref=db.backref('texts', lazy=True))
    tags = db.relationship('Tag', secondary=text_tags, backref=db.backref('texts', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'folder_id': self.folder_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': [tag.to_dict() for tag in self.tags],
        }


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}
