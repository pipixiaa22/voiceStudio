def test_create_text(client):
    response = client.post('/api/texts', json={
        'title': '测试标题',
        'content': '测试内容'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == '测试标题'
    assert data['content'] == '测试内容'


def test_get_texts(client):
    client.post('/api/texts', json={'title': '标题1', 'content': '内容1'})
    client.post('/api/texts', json={'title': '标题2', 'content': '内容2'})
    response = client.get('/api/texts')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_get_texts_by_folder(client):
    folder = client.post('/api/folders', json={'name': '文件夹'}).get_json()
    client.post('/api/texts', json={'title': '标题', 'content': '内容', 'folder_id': folder['id']})
    response = client.get(f"/api/texts?folder_id={folder['id']}")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1


def test_get_texts_by_tag(client):
    tag = client.post('/api/tags', json={'name': '标签'}).get_json()
    client.post('/api/texts', json={'title': '标题', 'content': '内容', 'tag_ids': [tag['id']]})
    response = client.get('/api/texts?tag=标签')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1


def test_update_text(client):
    text = client.post('/api/texts', json={'title': '原标题', 'content': '原内容'}).get_json()
    response = client.put(f"/api/texts/{text['id']}", json={'title': '新标题'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == '新标题'


def test_delete_text(client):
    text = client.post('/api/texts', json={'title': '待删除', 'content': '内容'}).get_json()
    response = client.delete(f"/api/texts/{text['id']}")
    assert response.status_code == 204


def test_sort_texts(client):
    client.post('/api/texts', json={'title': '第一个', 'content': '内容'})
    client.post('/api/texts', json={'title': '第二个', 'content': '内容'})
    response = client.get('/api/texts?sort_by=created_at&order=desc')
    data = response.get_json()
    assert data[0]['title'] == '第二个'
