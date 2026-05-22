import pytest
from server.services.tts_provider import TTSProvider


def test_tts_provider_init():
    provider = TTSProvider(api_key='test-key')
    assert provider.api_key == 'test-key'


def test_tts_provider_missing_key():
    with pytest.raises(ValueError, match='API Key'):
        TTSProvider(api_key='')
