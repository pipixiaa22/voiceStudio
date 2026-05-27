import json
from unittest.mock import patch, MagicMock
from server.models import DiscoveryItem, db


def test_get_sources(client):
    resp = client.get('/api/discovery/sources')
    assert resp.status_code == 200
    sources = resp.get_json()
    assert isinstance(sources, list)
    platform_keys = [s['platform_key'] for s in sources]
    assert 'manual' in platform_keys
    assert 'youtube' in platform_keys


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
def test_search_success(mock_get, client):
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
