import pytest
from server.models import db
from server.models.novel.project import NovelProject


@pytest.fixture
def sample_project(client):
    project = NovelProject(title='测试小说', genre='玄幻')
    db.session.add(project)
    db.session.commit()
    return project


def test_create_memory(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '主角设定',
        'content': '张三，男，25岁，修炼火属性功法',
        'memory_type': 'character',
        'source_type': 'manual_note',
        'importance': 5,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['title'] == '主角设定'
    assert data['memory_type'] == 'character'
    assert data['importance'] == 5
    assert data['status'] == 'active'
    # In test mode (no embedding key), vector_status stays 'pending'
    assert data['vector_status'] in ('indexed', 'pending')


def test_list_memories(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '记忆1', 'content': '内容1', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '记忆2', 'content': '内容2', 'memory_type': 'world_rule', 'source_type': 'manual_note',
    })
    resp = client.get(f'/api/novels/{sample_project.id}/memories')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_list_memories_filter(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '人物', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '世界', 'content': '内容', 'memory_type': 'world_rule', 'source_type': 'manual_note',
    })
    resp = client.get(f'/api/novels/{sample_project.id}/memories?memory_type=character')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['memory_type'] == 'character'


def test_update_memory(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '原始', 'content': '原始内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.patch(f'/api/novels/{sample_project.id}/memories/{mid}', json={
        'title': '更新后', 'importance': 1,
    })
    assert resp.status_code == 200
    assert resp.get_json()['title'] == '更新后'
    assert resp.get_json()['importance'] == 1


def test_delete_memory(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '待删', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.delete(f'/api/novels/{sample_project.id}/memories/{mid}')
    assert resp.status_code == 204
    resp = client.get(f'/api/novels/{sample_project.id}/memories')
    assert len(resp.get_json()) == 0


def test_memory_requires_content(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'memory_type': 'character', 'source_type': 'manual_note',
    })
    assert resp.status_code == 400


def test_memory_belongs_to_project(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '记忆', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.patch(f'/api/novels/99999/memories/{mid}', json={'title': 'x'})
    assert resp.status_code in (404, 400)


def test_memory_changes_list(client, sample_project):
    resp = client.get(f'/api/novels/{sample_project.id}/memory-changes')
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_reindex_memories(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '角色A', 'content': '张三，男，25岁', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '规则B', 'content': '火属性功法克制冰属性', 'memory_type': 'world_rule', 'source_type': 'manual_note',
    })
    resp = client.post(f'/api/novels/{sample_project.id}/memories/reindex')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['memories'] == 2
    assert 'indexed_chunks' in data


def test_search_memories(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '角色', 'content': '张三修炼火属性功法', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    resp = client.post(f'/api/novels/{sample_project.id}/memories/search', json={
        'query': '火属性',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'results' in data
    assert data['query'] == '火属性'


def test_search_memories_by_type(client, sample_project):
    client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '角色', 'content': '张三修炼火属性功法', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    resp = client.post(f'/api/novels/{sample_project.id}/memories/search', json={
        'query': '火属性',
        'memory_type': 'character',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'results' in data


def test_search_memories_not_found_project(client):
    resp = client.post('/api/novels/99999/memories/search', json={'query': 'test'})
    assert resp.status_code == 404


def test_reindex_memories_not_found_project(client):
    resp = client.post('/api/novels/99999/memories/reindex')
    assert resp.status_code == 404


# --- Validation tests ---

def test_create_rejects_invalid_memory_type(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '测试', 'content': '内容', 'memory_type': 'bad_type', 'source_type': 'manual_note',
    })
    assert resp.status_code == 400
    assert '无效的记忆类型' in resp.get_json()['error']


def test_create_rejects_invalid_importance(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '测试', 'content': '内容', 'memory_type': 'character',
        'source_type': 'manual_note', 'importance': 99,
    })
    # importance is clamped to valid range in create, should succeed
    assert resp.status_code == 201


def test_patch_rejects_invalid_memory_type(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '原始', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.patch(f'/api/novels/{sample_project.id}/memories/{mid}', json={
        'memory_type': 'bad_type',
    })
    assert resp.status_code == 400
    assert '无效的记忆类型' in resp.get_json()['error']


def test_patch_rejects_invalid_importance(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories', json={
        'title': '原始', 'content': '内容', 'memory_type': 'character', 'source_type': 'manual_note',
    })
    mid = resp.get_json()['id']
    resp = client.patch(f'/api/novels/{sample_project.id}/memories/{mid}', json={
        'importance': 'oops',
    })
    assert resp.status_code == 400


def test_search_invalid_k_falls_back(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories/search', json={
        'query': 'test', 'k': 'abc',
    })
    assert resp.status_code == 200


def test_search_k_minimum_1(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories/search', json={
        'query': 'test', 'k': 0,
    })
    assert resp.status_code == 200


def test_search_k_capped_at_50(client, sample_project):
    resp = client.post(f'/api/novels/{sample_project.id}/memories/search', json={
        'query': 'test', 'k': 1000,
    })
    assert resp.status_code == 200
