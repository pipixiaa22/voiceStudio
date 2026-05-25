import pytest
from server.services.tts_provider import TTSProvider


def test_tts_provider_init():
    provider = TTSProvider(api_key='test-key')
    assert provider.api_key == 'test-key'


def test_tts_provider_missing_key():
    with pytest.raises(ValueError, match='API Key'):
        TTSProvider(api_key='')


def test_synthesize_places_style_tags_in_assistant_text_and_disables_text_optimization(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {'choices': [{'message': {'audio': {'data': 'abc'}}}]}

    def fake_post(url, headers, json, timeout):
        captured['payload'] = json
        return FakeResponse()

    monkeypatch.setattr('server.services.tts_provider.requests.post', fake_post)

    provider = TTSProvider(api_key='test-key')
    audio = provider.synthesize(
        voice_description='年轻女性，清冷克制',
        text='此剑一出，便再无回头之路。',
        style_tags='高冷 凌厉 平静',
    )

    assert audio == 'abc'
    assert captured['payload']['model'] == 'mimo-v2.5-tts-voicedesign'
    assert captured['payload']['messages'] == [
        {'role': 'user', 'content': '年轻女性，清冷克制'},
        {'role': 'assistant', 'content': '（高冷 凌厉 平静）此剑一出，便再无回头之路。'},
    ]
    assert captured['payload']['audio'] == {
        'format': 'wav',
        'optimize_text_preview': False,
    }


def test_synthesize_can_enable_text_optimization_for_audition(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {'choices': [{'message': {'audio': {'data': 'audition'}}}]}

    def fake_post(url, headers, json, timeout):
        captured['payload'] = json
        return FakeResponse()

    monkeypatch.setattr('server.services.tts_provider.requests.post', fake_post)

    provider = TTSProvider(api_key='test-key')
    audio = provider.synthesize(
        voice_description='青春少女，明亮清甜',
        text='师姐师姐！你看，我真的引气入体了！',
        style_tags='清亮 稚嫩 活泼',
        optimize_text_preview=True,
    )

    assert audio == 'audition'
    assert captured['payload']['audio']['optimize_text_preview'] is True


def test_synthesize_supports_builtin_voice_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {'choices': [{'message': {'audio': {'data': 'builtin'}}}]}

    def fake_post(url, headers, json, timeout):
        captured['payload'] = json
        return FakeResponse()

    monkeypatch.setattr('server.services.tts_provider.requests.post', fake_post)

    provider = TTSProvider(api_key='test-key')
    provider.synthesize(
        voice_description='温柔叙述',
        text='云海翻涌，仙门将启。',
        model='mimo-v2.5-tts',
        voice='冰糖',
    )

    assert captured['payload']['model'] == 'mimo-v2.5-tts'
    assert captured['payload']['messages'] == [
        {'role': 'user', 'content': '温柔叙述'},
        {'role': 'assistant', 'content': '云海翻涌，仙门将启。'},
    ]
    assert captured['payload']['audio']['voice'] == '冰糖'
