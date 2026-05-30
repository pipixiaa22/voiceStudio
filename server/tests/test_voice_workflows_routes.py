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


import base64
import io
import json
import wave
import zipfile


def _make_wav(duration_seconds=1.0, framerate=8000):
    frame_count = int(duration_seconds * framerate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(b'\x00\x00' * frame_count)
    return buf.getvalue()


def test_audition_segment_returns_audio(client, monkeypatch):
    created = client.post('/api/voice-workflows', json={
        'title': '试听工程',
        'source_content': '我知道了。',
    }).get_json()
    segment_id = created['segments'][0]['id']

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda profile_id: None)

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', FakeProvider)

    response = client.post(f"/api/voice-workflows/{created['id']}/segments/{segment_id}/audition", json={
        'api_key': 'test-key',
        'voice_description': '温柔女声',
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['audio_base64']
    assert data['duration'] == 1.0
    assert data['fingerprint'].startswith('sha256:')


def test_export_voice_workflow_zip(client, monkeypatch):
    created = client.post('/api/voice-workflows', json={
        'title': '导出工程',
        'source_content': '我知道了。可是你为什么现在才告诉我！',
    }).get_json()

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda profile_id: None)

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', FakeProvider)

    response = client.post(f"/api/voice-workflows/{created['id']}/export", json={
        'api_key': 'test-key',
        'voice_description': '温柔女声',
        'export_options': {'include_segment_wavs': True},
    })

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as zf:
        names = zf.namelist()
        assert 'manifest.json' in names
        assert any(name.endswith('_完整音频.wav') for name in names)
        assert any(name.endswith('_同步字幕.srt') for name in names)
        assert 'segments/001.wav' in names
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert manifest['source'] == 'voice_workflow'
        assert len(manifest['segments']) == 2


def test_audition_path_returns_full_audio(client, monkeypatch):
    created = client.post('/api/voice-workflows', json={
        'title': '路径试听',
        'source_content': '我知道了。可是你为什么现在才告诉我！',
    }).get_json()

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda pid: None)

    class FakeProvider:
        def __init__(self, api_key):
            pass
        def synthesize(self, **kwargs):
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', FakeProvider)

    response = client.post(f"/api/voice-workflows/{created['id']}/audition-path", json={
        'api_key': 'test-key',
        'voice_description': '温柔女声',
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['audio_base64']
    assert data['segment_count'] == 2
    assert data['total_duration'] > 0
    assert len(data['timeline']) == 2


def test_export_reuses_cache_on_second_call(client, monkeypatch, tmp_path):
    """Second export with same params should not re-synthesize."""
    call_count = [0]

    created = client.post('/api/voice-workflows', json={
        'title': '缓存测试',
        'source_content': '测试句。',
    }).get_json()

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda pid: None)
    monkeypatch.setattr('server.routes.voice_workflows.CACHE_DIR', str(tmp_path))

    class CountingProvider:
        def __init__(self, api_key):
            pass

        def synthesize(self, **kwargs):
            call_count[0] += 1
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', CountingProvider)

    # First export - should synthesize
    resp1 = client.post(f"/api/voice-workflows/{created['id']}/export", json={
        'api_key': 'test-key',
        'voice_description': 'test',
    })
    assert resp1.status_code == 200
    first_count = call_count[0]
    assert first_count > 0

    # Second export - should use cache
    resp2 = client.post(f"/api/voice-workflows/{created['id']}/export", json={
        'api_key': 'test-key',
        'voice_description': 'test',
    })
    assert resp2.status_code == 200
    assert call_count[0] == first_count  # no new synthesize calls


def test_audition_writes_cache(client, monkeypatch, tmp_path):
    created = client.post('/api/voice-workflows', json={
        'title': '缓存试听',
        'source_content': '测试句。',
    }).get_json()
    segment_id = created['segments'][0]['id']

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda pid: None)
    monkeypatch.setattr('server.routes.voice_workflows.CACHE_DIR', str(tmp_path))

    class FakeProvider:
        def __init__(self, api_key): pass
        def synthesize(self, **kwargs):
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', FakeProvider)

    response = client.post(f"/api/voice-workflows/{created['id']}/segments/{segment_id}/audition", json={
        'api_key': 'test-key',
        'voice_description': 'test',
    })

    assert response.status_code == 200
    data = response.get_json()

    # Verify cache was written
    workflow_dir = tmp_path / str(created['id'])
    assert workflow_dir.exists()
    wav_files = list(workflow_dir.glob('*.wav'))
    assert len(wav_files) == 1

    # Verify segment was updated
    get_resp = client.get(f"/api/voice-workflows/{created['id']}")
    segment = get_resp.get_json()['segments'][0]
    assert segment['audio_status'] == 'ready'
    assert segment['audio_fingerprint'] == data['fingerprint']


def test_clear_workflow_cache(client, monkeypatch, tmp_path):
    monkeypatch.setattr('server.routes.voice_workflows.CACHE_DIR', str(tmp_path))

    created = client.post('/api/voice-workflows', json={
        'title': '清理测试',
        'source_content': '测试。',
    }).get_json()

    # Create cache dir with a file
    cache_dir = tmp_path / str(created['id'])
    cache_dir.mkdir(parents=True)
    (cache_dir / 'test.wav').write_bytes(b'fake')

    response = client.delete(f"/api/voice-workflows/{created['id']}/cache")
    assert response.status_code == 204
    assert not cache_dir.exists()
