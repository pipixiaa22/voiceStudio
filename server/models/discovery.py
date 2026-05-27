from datetime import datetime, timezone
from server.models.base import db


class DiscoverySource(db.Model):
    __tablename__ = 'discovery_sources'

    id = db.Column(db.Integer, primary_key=True)
    platform_key = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    config_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'platform_key': self.platform_key,
            'display_name': self.display_name,
            'is_enabled': self.is_enabled,
            'config': json.loads(self.config_json) if self.config_json else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DiscoveryQuery(db.Model):
    __tablename__ = 'discovery_queries'

    id = db.Column(db.Integer, primary_key=True)
    query_type = db.Column(db.String(20), nullable=False)
    platform_key = db.Column(db.String(50), nullable=False)
    query_text = db.Column(db.String(500), nullable=False)
    filters_json = db.Column(db.Text, default='{}')
    status = db.Column(db.String(20), default='pending')
    item_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'query_type': self.query_type,
            'platform_key': self.platform_key,
            'query_text': self.query_text,
            'filters': json.loads(self.filters_json) if self.filters_json else {},
            'status': self.status,
            'item_count': self.item_count,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DiscoveryItem(db.Model):
    __tablename__ = 'discovery_items'

    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('discovery_queries.id'), nullable=True)
    platform_key = db.Column(db.String(50), nullable=False)
    source_url = db.Column(db.String(1000), nullable=False)
    source_id = db.Column(db.String(200))
    title = db.Column(db.String(500))
    author_name = db.Column(db.String(200))
    cover_url = db.Column(db.String(1000))
    published_at = db.Column(db.DateTime)
    duration = db.Column(db.Float)
    stats_json = db.Column(db.Text, default='{}')
    tags_json = db.Column(db.Text, default='[]')
    raw_json = db.Column(db.Text, default='{}')
    is_favorited = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    query = db.relationship('DiscoveryQuery', backref=db.backref('items', lazy=True))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'query_id': self.query_id,
            'platform_key': self.platform_key,
            'source_url': self.source_url,
            'source_id': self.source_id,
            'title': self.title,
            'author_name': self.author_name,
            'cover_url': self.cover_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'duration': self.duration,
            'stats': json.loads(self.stats_json) if self.stats_json else {},
            'tags': json.loads(self.tags_json) if self.tags_json else [],
            'is_favorited': self.is_favorited,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DiscoveryAnalysis(db.Model):
    __tablename__ = 'discovery_analyses'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('discovery_items.id'), unique=True, nullable=False)
    xianxia_score = db.Column(db.Float, default=0.0)
    hot_score = db.Column(db.Float, default=0.0)
    format_score = db.Column(db.Float, default=0.0)
    is_static_image_style = db.Column(db.Boolean, default=False)
    score_reasons_json = db.Column(db.Text, default='[]')
    analysis_json = db.Column(db.Text, default='{}')
    generated_title = db.Column(db.String(500))
    generated_content = db.Column(db.Text)
    recommended_template = db.Column(db.String(50))
    recommended_voice_desc = db.Column(db.String(200))
    recommended_max_chars = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    item = db.relationship('DiscoveryItem', backref=db.backref('analysis', uselist=False))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'item_id': self.item_id,
            'xianxia_score': self.xianxia_score,
            'hot_score': self.hot_score,
            'format_score': self.format_score,
            'is_static_image_style': self.is_static_image_style,
            'score_reasons': json.loads(self.score_reasons_json) if self.score_reasons_json else [],
            'analysis': json.loads(self.analysis_json) if self.analysis_json else {},
            'generated_title': self.generated_title,
            'generated_content': self.generated_content,
            'recommended_template': self.recommended_template,
            'recommended_voice_desc': self.recommended_voice_desc,
            'recommended_max_chars': self.recommended_max_chars,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
