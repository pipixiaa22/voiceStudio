from server.models.base import db
from server.models.discovery import DiscoverySource

BUILTIN_SOURCES = [
    {'platform_key': 'manual', 'display_name': '手动链接', 'is_enabled': True},
    {'platform_key': 'youtube', 'display_name': 'YouTube', 'is_enabled': True},
    {'platform_key': 'douyin', 'display_name': '抖音', 'is_enabled': False},
    {'platform_key': 'bilibili', 'display_name': 'B站', 'is_enabled': False},
    {'platform_key': 'kuaishou', 'display_name': '快手', 'is_enabled': False},
]


def seed_discovery_sources():
    for src in BUILTIN_SOURCES:
        existing = DiscoverySource.query.filter_by(platform_key=src['platform_key']).first()
        if not existing:
            db.session.add(DiscoverySource(**src))
    db.session.commit()
