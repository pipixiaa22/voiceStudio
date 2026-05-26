import pytest
from server.services.providers.mimo_provider import MimoProvider


def test_mimo_provider_init():
    provider = MimoProvider(api_key='test-key')
    assert provider.provider_id == 'mimo'
    assert provider.api_key == 'test-key'


def test_mimo_provider_get_models():
    provider = MimoProvider(api_key='test-key')
    models = provider.get_models()
    assert len(models) > 0
    model_keys = [m.model_key for m in models]
    assert 'mimo-v2.5-tts-voicedesign' in model_keys
    assert 'mimo-v2.5-pro' in model_keys


def test_mimo_provider_capabilities():
    provider = MimoProvider(api_key='test-key')
    assert 'tts_voice_design' in provider.capabilities
    assert 'llm_text' in provider.capabilities
