import json


def test_create_folder(client):
    response = client.post('/api/folders', json={'name': '测试文件夹'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == '测试文件夹'
    assert data['id'] is not None


def test_get_folders(client):
    client.post('/api/folders', json={'name': '文件夹1'})
    client.post('/api/folders', json={'name': '文件夹2'})
    response = client.get('/api/folders')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_create_nested_folder(client):
    parent = client.post('/api/folders', json={'name': '父文件夹'}).get_json()
    response = client.post('/api/folders', json={'name': '子文件夹', 'parent_id': parent['id']})
    assert response.status_code == 201
    data = response.get_json()
    assert data['parent_id'] == parent['id']


def test_delete_folder(client):
    folder = client.post('/api/folders', json={'name': '待删除'}).get_json()
    response = client.delete(f"/api/folders/{folder['id']}")
    assert response.status_code == 204
    response = client.get('/api/folders')
    assert len(response.get_json()) == 0
