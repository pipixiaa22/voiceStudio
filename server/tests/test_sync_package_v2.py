import json
import base64
import io
import wave
import zipfile


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


def _make_wav(duration_seconds: float, framerate: int = 8000) -> bytes:
    frame_count = int(duration_seconds * framerate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(b'\x00\x00' * frame_count)
    return buf.getvalue()


def test_sync_package_v2_resolves_voice_profile_and_records_manifest(client, monkeypatch):
    calls = []

    monkeypatch.setattr('server.routes.tts.repo.get_profile_by_id', lambda profile_id: {
        'id': profile_id,
        'profile_key': 'xianxia_cold_yujie',
        'name': '冷淡御姐声',
        'canonical_prompt': '成熟清冷的中文女性角色声线',
        'raw_description': '冷淡御姐声',
        'negative_prompt': '不要暧昧',
        'provider': 'mimo',
        'model': 'mimo-v2.5-tts-voicedesign',
        'style_tags': '高冷 凌厉 平静',
        'builtin_voice': None,
        'source_type': 'voice_design',
    })

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            calls.append(kwargs)
            return base64.b64encode(_make_wav(1.0)).decode('ascii')

    monkeypatch.setattr('server.routes.tts.TTSProvider', FakeProvider)

    response = client.post('/api/tts/sync-package-v2', json={
        'api_key': 'test-key',
        'title': '试剑',
        'content': '此剑一出，便再无回头之路。你，可想好了？',
        'voice_profile_id': 9,
        'subtitle_options': {'max_chars': 20, 'gap': 0.2},
        'synthesis_options': {'mode': 'chunked', 'chunk_max_chars': 200},
    })

    assert response.status_code == 200
    assert calls
    assert calls[0]['voice_description'] == '成熟清冷的中文女性角色声线'
    assert calls[0]['style_tags'] == '高冷 凌厉 平静'
    assert calls[0]['optimize_text_preview'] is False

    with zipfile.ZipFile(io.BytesIO(response.data)) as zf:
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert manifest['voice_profile'] == {
            'id': 9,
            'profile_key': 'xianxia_cold_yujie',
            'name': '冷淡御姐声',
            'provider': 'mimo',
            'model': 'mimo-v2.5-tts-voicedesign',
            'source_type': 'voice_design',
        }


def test_sync_package_v2_uses_voice_clone_sample_as_audio_voice(client, monkeypatch):
    calls = []
    sample = 'data:audio/wav;base64,UklGRg=='

    monkeypatch.setattr('server.routes.tts.repo.get_profile_by_id', lambda profile_id: {
        'id': profile_id,
        'profile_key': 'clone_cold_master',
        'name': '复刻冷淡师尊',
        'canonical_prompt': '保持样音中的清冷女性声线，语气克制。',
        'raw_description': '冷淡师尊',
        'provider': 'mimo',
        'model': 'mimo-v2.5-tts-voiceclone',
        'style_tags': '古风 高冷 平静',
        'builtin_voice': None,
        'voice_sample_data_uri': sample,
        'source_type': 'voice_clone',
    })

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            calls.append(kwargs)
            return base64.b64encode(_make_wav(1.0)).decode('ascii')

    monkeypatch.setattr('server.routes.tts.TTSProvider', FakeProvider)

    response = client.post('/api/tts/sync-package-v2', json={
        'api_key': 'test-key',
        'title': '复刻试音',
        'content': '云海之上，玄霜峰今日开山收徒。',
        'voice_profile_id': 12,
    })

    assert response.status_code == 200
    assert calls[0]['model'] == 'mimo-v2.5-tts-voiceclone'
    assert calls[0]['voice'] == sample

    with zipfile.ZipFile(io.BytesIO(response.data)) as zf:
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert manifest['voice_profile']['source_type'] == 'voice_clone'
