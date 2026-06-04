import json
import os
import logging

logger = logging.getLogger(__name__)


def get_llm_provider(model_config=None):
    """Resolve the active LLM provider for novel generation.

    Priority:
    1. Explicit request model config from the frontend
    2. Custom provider with llm_text capability (first one found)
    3. Built-in provider matching MIMO_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY env vars
    4. Fallback to mimo provider with empty key (will fail at call time if no key)

    Returns (provider, model_key) tuple.
    """
    from server.services.model_registry import ModelRegistry
    registry = ModelRegistry()

    if model_config and model_config.get('api_key'):
        provider_key = model_config.get('provider_key') or 'mimo'
        model_key = model_config.get('model_key') or 'mimo-v2.5-pro'
        provider = registry.create_provider(
            provider_key,
            api_key=model_config.get('api_key', ''),
            base_url=model_config.get('base_url', ''),
            provider_type=model_config.get('provider_type', ''),
        )
        return provider, model_key

    # 2. Check custom providers with llm_text capability AND valid API key
    try:
        from server.models.provider import CustomProvider
        for cp in CustomProvider.query.all():
            models = json.loads(cp.models_json) if cp.models_json else []
            has_llm = any('llm_text' in m.get('capabilities', []) for m in models)
            if not has_llm:
                continue
            api_key = os.environ.get(f'{cp.provider_key.upper()}_API_KEY', '')
            if not api_key:
                continue  # Skip custom provider without API key
            for m in models:
                if 'llm_text' in m.get('capabilities', []):
                    provider = registry.create_provider(
                        cp.provider_key,
                        api_key=api_key,
                        base_url=cp.base_url,
                        provider_type='openai_compatible',
                    )
                    return provider, m['model_key']
    except Exception:
        pass

    # 3. Check env vars for built-in providers
    env_providers = [
        ('mimo', 'MIMO_API_KEY', 'mimo-v2.5-pro'),
        ('deepseek', 'DEEPSEEK_API_KEY', 'deepseek-chat'),
        ('openai', 'OPENAI_API_KEY', 'gpt-4.1-mini'),
    ]
    for provider_key, env_key, default_model in env_providers:
        api_key = os.environ.get(env_key, '')
        if api_key:
            try:
                provider = registry.create_provider(provider_key, api_key=api_key)
                return provider, default_model
            except Exception:
                continue

    # 4. Fallback: try mimo with empty key
    provider = registry.create_provider('mimo', api_key='')
    return provider, 'mimo-v2.5-pro'
