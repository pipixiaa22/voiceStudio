def test_audition_profile_uses_voice_clone_sample(client, monkeypatch):
    calls = []
    sample = 'data:audio/mp3;base64,AAAA'

    monkeypatch.setattr('server.routes.voice_profiles.repo.get_profile_by_id', lambda profile_id: {
        'id': profile_id,
        'canonical_prompt': '保持样音中的温婉女声。',
        'raw_description': '温婉女声',
        'model': 'mimo-v2.5-tts-voiceclone',
        'style_tags': '古风 温婉 柔和',
        'builtin_voice': None,
        'voice_sample_data_uri': sample,
        'audition_text': '（古风 温婉）孩子，修行路远，莫急。',
    })
    monkeypatch.setattr('server.routes.voice_profiles.repo.create_audition', lambda profile_id, text: {
        'id': 77,
        'voice_profile_id': profile_id,
        'audition_text': text,
        'status': 'created',
    })
    monkeypatch.setattr('server.routes.voice_profiles.repo.update_audition', lambda *args, **kwargs: None)

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            calls.append(kwargs)
            return 'audio-data'

    monkeypatch.setattr('server.routes.voice_profiles.TTSProvider', FakeProvider)

    response = client.post('/api/voice-profiles/7/audition', json={'api_key': 'test-key'})

    assert response.status_code == 200
    assert response.get_json()['audition_id'] == 77
    assert calls == [{
        'voice_description': '保持样音中的温婉女声。',
        'text': '（古风 温婉）孩子，修行路远，莫急。',
        'style_tags': '古风 温婉 柔和',
        'model': 'mimo-v2.5-tts-voiceclone',
        'voice': sample,
        'optimize_text_preview': True,
    }]


def test_create_voice_clone_requires_authorized_sample(client, monkeypatch):
    response = client.post('/api/voice-profiles', json={
        'name': '复刻师尊',
        'raw_description': '清冷女性声线',
        'source_type': 'voice_clone',
        'voice_sample_data_uri': 'data:audio/wav;base64,UklGRg==',
    })

    assert response.status_code == 400
    assert '授权' in response.get_json()['error']


def test_create_voice_clone_accepts_authorized_sample(client, monkeypatch):
    created = {}

    def fake_create_profile(data):
        created.update(data)
        return {'id': 1, **data}

    monkeypatch.setattr('server.routes.voice_profiles.repo.create_profile', fake_create_profile)

    response = client.post('/api/voice-profiles', json={
        'name': '复刻师尊',
        'raw_description': '清冷女性声线',
        'source_type': 'voice_clone',
        'voice_sample_data_uri': 'data:audio/wav;base64,UklGRg==',
        'voice_sample_mime': 'audio/wav',
        'voice_sample_filename': 'master.wav',
        'consent_confirmed': True,
    })

    assert response.status_code == 201
    assert created['model'] == 'mimo-v2.5-tts-voiceclone'
    assert created['voice_sample_data_uri'].startswith('data:audio/wav;base64,')
