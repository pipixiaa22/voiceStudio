def test_create_voice_workflow_from_content(client):
    response = client.post('/api/voice-workflows', json={
        'title': '试音工程',
        'source_content': '我知道了。可是你为什么现在才告诉我！',
        'default_voice_profile_id': 9,
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == '试音工程'
    assert len(data['segments']) == 2
    assert data['segments'][1]['emotion'] == 'angry_burst'
    assert len(data['edges']) == 1


def test_update_voice_workflow_snapshot(client):
    created = client.post('/api/voice-workflows', json={
        'title': '旧工程',
        'source_content': '旧内容。',
    }).get_json()

    response = client.put(f"/api/voice-workflows/{created['id']}", json={
        'workflow': {'title': '新工程', 'source_content': '新内容。'},
        'segments': [
            {'order_index': 1, 'text': '新内容。', 'emotion': 'calm', 'node_x': 80, 'node_y': 120},
        ],
        'edges': [],
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == '新工程'
    assert data['segments'][0]['text'] == '新内容。'


def test_plan_segments_endpoint_returns_rule_segments(client):
    created = client.post('/api/voice-workflows', json={'title': '空工程'}).get_json()

    response = client.post(f"/api/voice-workflows/{created['id']}/segments/plan", json={
        'content': '算了，不必解释。可是你为什么现在才告诉我！',
        'max_chars': 80,
    })

    assert response.status_code == 200
    data = response.get_json()
    assert [segment['emotion'] for segment in data['segments']] == ['cold', 'angry_burst']


def test_delete_voice_workflow(client):
    created = client.post('/api/voice-workflows', json={'title': '待删除'}).get_json()

    response = client.delete(f"/api/voice-workflows/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/voice-workflows/{created['id']}").status_code == 404
