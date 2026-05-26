import pytest


def test_get_presets(client):
    response = client.get('/api/model-providers/presets')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 3
    keys = [p['provider_key'] for p in data]
    assert 'mimo' in keys
    assert 'deepseek' in keys


def test_get_all_models(client):
    response = client.get('/api/models')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0
    assert 'provider_key' in data[0]
    assert 'model_key' in data[0]


def test_test_connection_missing_params(client):
    response = client.post('/api/model-providers/test', json={})
    assert response.status_code == 400


def test_llm_complete_missing_params(client):
    response = client.post('/api/models/llm/complete', json={})
    assert response.status_code == 400


def test_tts_synthesize_missing_params(client):
    response = client.post('/api/models/tts/synthesize', json={})
    assert response.status_code == 400
