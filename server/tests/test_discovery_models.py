import json
from datetime import datetime, timezone, timedelta
from server.models import (
    db, DiscoverySource, DiscoveryQuery, DiscoveryItem, DiscoveryAnalysis,
)


def test_discovery_source_create(app, db):
    with app.app_context():
        src = DiscoverySource(platform_key='test_platform', display_name='Test Platform')
        db.session.add(src)
        db.session.commit()
        assert src.id is not None
        assert src.is_enabled is True


def test_discovery_source_to_dict(app, db):
    with app.app_context():
        src = DiscoverySource(
            platform_key='test_platform_2', display_name='Test Platform 2',
            config_json='{"api_key": "test"}',
        )
        db.session.add(src)
        db.session.commit()
        d = src.to_dict()
        assert d['platform_key'] == 'test_platform_2'
        assert d['config'] == {'api_key': 'test'}


def test_discovery_query_create(app, db):
    with app.app_context():
        q = DiscoveryQuery(
            query_type='keyword', platform_key='youtube',
            query_text='修仙小说', status='pending',
        )
        db.session.add(q)
        db.session.commit()
        assert q.id is not None
        assert q.status == 'pending'
        assert q.item_count == 0


def test_discovery_item_with_query(app, db):
    with app.app_context():
        q = DiscoveryQuery(
            query_type='keyword', platform_key='youtube', query_text='修仙',
        )
        db.session.add(q)
        db.session.flush()

        item = DiscoveryItem(
            query_id=q.id, platform_key='youtube',
            source_url='https://youtube.com/watch?v=abc',
            title='测试视频',
            stats_json='{"views": 1000, "likes": 50}',
            tags_json='["修仙", "重生"]',
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        assert d['stats'] == {'views': 1000, 'likes': 50}
        assert d['tags'] == ['修仙', '重生']
        assert item.query_id == q.id


def test_discovery_item_without_query(app, db):
    with app.app_context():
        item = DiscoveryItem(
            platform_key='manual',
            source_url='https://bilibili.com/video/BV123',
        )
        db.session.add(item)
        db.session.commit()
        assert item.query_id is None


def test_discovery_analysis_one_to_one(app, db):
    with app.app_context():
        item = DiscoveryItem(
            platform_key='manual',
            source_url='https://bilibili.com/video/BV123',
        )
        db.session.add(item)
        db.session.flush()

        analysis = DiscoveryAnalysis(
            item_id=item.id,
            xianxia_score=0.86,
            hot_score=0.72,
            format_score=0.5,
            score_reasons_json=json.dumps(['标题命中仙帝/重生']),
            generated_title='原创标题',
            generated_content='原创脚本内容',
            recommended_template='xianxia_narration',
            recommended_voice_desc='沉稳男声',
            recommended_max_chars=16,
        )
        db.session.add(analysis)
        db.session.commit()

        d = analysis.to_dict()
        assert d['xianxia_score'] == 0.86
        assert d['score_reasons'] == ['标题命中仙帝/重生']
        assert d['generated_title'] == '原创标题'

        # Verify one-to-one relationship
        assert item.analysis is not None
        assert item.analysis.id == analysis.id


def test_discovery_analysis_to_dict_empty(app, db):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.flush()

        analysis = DiscoveryAnalysis(item_id=item.id)
        db.session.add(analysis)
        db.session.commit()

        d = analysis.to_dict()
        assert d['score_reasons'] == []
        assert d['analysis'] == {}
        assert d['generated_title'] is None
