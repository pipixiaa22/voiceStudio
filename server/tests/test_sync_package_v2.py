import json


def test_sync_package_v2_missing_params(client):
    response = client.post('/api/tts/sync-package-v2', json={})
    assert response.status_code == 400
    assert '请求数据不能为空' in response.get_json()['error']


def test_sync_package_v2_missing_api_key(client):
    response = client.post('/api/tts/sync-package-v2', json={
        'title': '测试',
        'content': '测试内容',
        'voice_description': '温柔女声',
    })
    assert response.status_code == 400
    assert 'API Key' in response.get_json()['error']


def test_sync_package_v2_missing_content(client):
    response = client.post('/api/tts/sync-package-v2', json={
        'api_key': 'test-key',
        'title': '测试',
        'voice_description': '温柔女声',
    })
    assert response.status_code == 400
    assert '文本内容' in response.get_json()['error']
