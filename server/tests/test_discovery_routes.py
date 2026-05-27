import json
from unittest.mock import patch, MagicMock
from server.models import DiscoveryItem, DiscoverySource, db


def test_get_sources(client):
    resp = client.get('/api/discovery/sources')
    assert resp.status_code == 200
    sources = resp.get_json()
    assert isinstance(sources, list)
    platform_keys = [s['platform_key'] for s in sources]
    assert 'manual' in platform_keys
    assert 'youtube' in platform_keys


def test_get_sources_reports_config_state_without_secret(client, app):
    with app.app_context():
        source = DiscoverySource.query.filter_by(platform_key='youtube').first()
        source.config_json = '{"api_key": "secret-youtube-key"}'
        db.session.commit()

    resp = client.get('/api/discovery/sources')

    assert resp.status_code == 200
    youtube = next(s for s in resp.get_json() if s['platform_key'] == 'youtube')
    assert youtube['needs_api_key'] is True
    assert youtube['is_configured'] is True
    assert youtube['config_fields'][0]['key'] == 'api_key'
    assert youtube['config'] == {}


def test_update_source_config_saves_required_api_key(client, app):
    resp = client.put('/api/discovery/sources/youtube/config', json={
        'config': {'api_key': 'new-youtube-key'},
        'is_enabled': True,
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['platform_key'] == 'youtube'
    assert data['is_configured'] is True
    assert data['config'] == {}

    with app.app_context():
        source = DiscoverySource.query.filter_by(platform_key='youtube').first()
        assert json.loads(source.config_json) == {'api_key': 'new-youtube-key'}
        assert source.is_enabled is True


def test_update_source_config_preserves_existing_key_when_omitted(client, app):
    with app.app_context():
        source = DiscoverySource.query.filter_by(platform_key='youtube').first()
        source.config_json = '{"api_key": "existing-youtube-key"}'
        db.session.commit()

    resp = client.put('/api/discovery/sources/youtube/config', json={
        'is_enabled': False,
        'config': {},
    })

    assert resp.status_code == 200
    with app.app_context():
        source = DiscoverySource.query.filter_by(platform_key='youtube').first()
        assert json.loads(source.config_json) == {'api_key': 'existing-youtube-key'}
        assert source.is_enabled is False


@patch('server.routes.discovery.ConnectorRegistry.get')
def test_search_youtube_missing_api_key_returns_config_hint(mock_get, client):
    mock_get.return_value = MagicMock()

    resp = client.post('/api/discovery/search', json={
        'platform': 'youtube',
        'query': '修仙小说',
    })

    assert resp.status_code == 400
    data = resp.get_json()
    assert data['code'] == 'missing_config'
    assert data['platform_key'] == 'youtube'
    assert 'YouTube' in data['message']


def test_search_missing_platform(client):
    resp = client.post('/api/discovery/search', json={'query': '修仙', 'platform': ''})
    assert resp.status_code == 400
    assert '平台' in resp.get_json()['error']


def test_search_empty_body(client):
    resp = client.post('/api/discovery/search', json={})
    assert resp.status_code == 400
    assert '不能为空' in resp.get_json()['error']


def test_search_empty_query(client):
    resp = client.post('/api/discovery/search', json={'platform': 'youtube', 'query': ''})
    assert resp.status_code == 400


def test_search_disabled_platform(client):
    resp = client.post('/api/discovery/search', json={'platform': 'douyin', 'query': '修仙'})
    assert resp.status_code == 400
    assert '未启用' in resp.get_json()['error']


@patch('server.routes.discovery.ConnectorRegistry.get')
def test_search_success(mock_get, client, app):
    with app.app_context():
        source = DiscoverySource.query.filter_by(platform_key='youtube').first()
        source.config_json = '{"api_key": "test-youtube-key"}'
        db.session.commit()

    mock_connector = MagicMock()
    mock_connector.search.return_value = [
        {
            'platform_key': 'youtube',
            'source_url': 'https://youtube.com/watch?v=abc',
            'source_id': 'abc',
            'title': '修仙小说 有声',
            'author_name': '测试频道',
            'stats': {'views': 50000, 'likes': 2000, 'comments': 100},
            'tags': ['修仙'],
            'duration': 120,
        },
    ]
    mock_get.return_value = mock_connector

    resp = client.post('/api/discovery/search', json={
        'platform': 'youtube',
        'query': '修仙小说',
        'limit': 10,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['items'][0]['title'] == '修仙小说 有声'
    assert data['items'][0]['xianxia_score'] > 0
    assert 'query_id' in data


@patch('server.routes.discovery.ConnectorRegistry.get')
def test_resolve_url_success(mock_get, client):
    mock_connector = MagicMock()
    mock_connector.resolve_url.return_value = {
        'platform_key': 'youtube',
        'source_url': 'https://youtube.com/watch?v=xyz',
        'source_id': 'xyz',
        'title': '测试视频',
        'stats': {'views': 10000, 'likes': 500},
    }
    mock_get.return_value = mock_connector

    resp = client.post('/api/discovery/resolve-url', json={
        'url': 'https://youtube.com/watch?v=xyz',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['title'] == '测试视频'


def test_resolve_url_missing_url(client):
    resp = client.post('/api/discovery/resolve-url', json={})
    assert resp.status_code == 400


def test_list_items_empty(client):
    resp = client.get('/api/discovery/items')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['items'] == []
    assert data['total'] == 0


def test_get_item_not_found(client):
    resp = client.get('/api/discovery/items/999')
    assert resp.status_code == 404


def test_toggle_favorite(client, app):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.put(f'/api/discovery/items/{item_id}/favorite')
    assert resp.status_code == 200
    assert resp.get_json()['is_favorited'] is True

    resp = client.put(f'/api/discovery/items/{item_id}/favorite')
    assert resp.status_code == 200
    assert resp.get_json()['is_favorited'] is False


def test_create_text_without_analysis(client, app):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.post(f'/api/discovery/items/{item_id}/create-text', json={})
    assert resp.status_code == 400
    assert '请先分析' in resp.get_json()['error']


def test_delete_item(client, app):
    with app.app_context():
        item = DiscoveryItem(platform_key='manual', source_url='https://example.com')
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    resp = client.delete(f'/api/discovery/items/{item_id}')
    assert resp.status_code == 204

    resp = client.get(f'/api/discovery/items/{item_id}')
    assert resp.status_code == 404


def test_list_queries(client):
    resp = client.get('/api/discovery/queries')
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
