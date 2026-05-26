import pytest
from server.services.model_registry import ModelRegistry


def test_registry_get_presets():
    registry = ModelRegistry()
    presets = registry.get_presets()
    assert len(presets) >= 3
    keys = [p.provider_key for p in presets]
    assert 'mimo' in keys
    assert 'deepseek' in keys
    assert 'openai' in keys


def test_registry_create_provider_mimo():
    registry = ModelRegistry()
    provider = registry.create_provider('mimo', api_key='test-key')
    assert provider.provider_id == 'mimo'


def test_registry_create_provider_deepseek():
    registry = ModelRegistry()
    provider = registry.create_provider('deepseek', api_key='test-key')
    assert provider.provider_id == 'deepseek'
    assert provider.base_url == 'https://api.deepseek.com'


def test_registry_create_provider_custom():
    registry = ModelRegistry()
    provider = registry.create_provider(
        'custom',
        api_key='test-key',
        base_url='https://my-api.com/v1',
        provider_type='openai_compatible',
    )
    assert provider.provider_id == 'custom'
    assert provider.base_url == 'https://my-api.com/v1'


def test_registry_get_all_models():
    registry = ModelRegistry()
    models = registry.get_all_models()
    assert len(models) > 0
    mimo_models = [m for m in models if m['provider_key'] == 'mimo']
    assert len(mimo_models) > 0
