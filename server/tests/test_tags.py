def test_create_tag(client):
    response = client.post('/api/tags', json={'name': '测试标签'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == '测试标签'


def test_get_tags(client):
    client.post('/api/tags', json={'name': '标签1'})
    client.post('/api/tags', json={'name': '标签2'})
    response = client.get('/api/tags')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_create_duplicate_tag(client):
    client.post('/api/tags', json={'name': '重复标签'})
    response = client.post('/api/tags', json={'name': '重复标签'})
    assert response.status_code == 409
