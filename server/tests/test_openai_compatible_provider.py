import pytest
from server.services.providers.openai_compatible_provider import OpenAICompatibleProvider


def test_provider_init():
    provider = OpenAICompatibleProvider(
        provider_id='deepseek',
        api_key='test-key',
        base_url='https://api.deepseek.com',
    )
    assert provider.provider_id == 'deepseek'
    assert provider.base_url == 'https://api.deepseek.com'


def test_provider_capabilities():
    provider = OpenAICompatibleProvider(
        provider_id='deepseek',
        api_key='test-key',
        base_url='https://api.deepseek.com',
    )
    assert 'llm_text' in provider.capabilities
