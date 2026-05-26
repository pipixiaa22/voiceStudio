from server.services.model_provider_base import ModelProvider, ProviderPreset, ModelInfo
from server.services.providers.mimo_provider import MimoProvider
from server.services.providers.openai_compatible_provider import OpenAICompatibleProvider
from server.services.providers.openai_provider import OpenAIProvider


BUILTIN_PRESETS = [
    ProviderPreset(
        provider_key='mimo',
        display_name='MiMo',
        provider_type='mimo',
        base_url='',
        capabilities=['tts_voice_design', 'tts_voice_clone', 'tts_builtin_voice', 'llm_text', 'llm_voice_prompt_polish'],
        models=[
            ModelInfo(model_key='mimo-v2.5-tts-voicedesign', display_name='MiMo 音色设计', capabilities=['tts_voice_design']),
            ModelInfo(model_key='mimo-v2.5-tts-voiceclone', display_name='MiMo 音色复刻', capabilities=['tts_voice_clone']),
            ModelInfo(model_key='mimo-v2.5-tts', display_name='MiMo 预置音色', capabilities=['tts_builtin_voice']),
            ModelInfo(model_key='mimo-v2.5-pro', display_name='MiMo Pro', capabilities=['llm_text', 'llm_voice_prompt_polish']),
        ],
    ),
    ProviderPreset(
        provider_key='deepseek',
        display_name='DeepSeek',
        provider_type='openai_compatible',
        base_url='https://api.deepseek.com',
        capabilities=['llm_text', 'llm_voice_prompt_polish', 'scene_planning', 'script_polish'],
        models=[
            ModelInfo(model_key='deepseek-chat', display_name='DeepSeek Chat', capabilities=['llm_text', 'llm_voice_prompt_polish', 'scene_planning']),
        ],
    ),
    ProviderPreset(
        provider_key='openai',
        display_name='ChatGPT / OpenAI',
        provider_type='openai',
        base_url='https://api.openai.com/v1',
        capabilities=['llm_text', 'tts_plain', 'scene_planning', 'script_polish'],
        models=[
            ModelInfo(model_key='gpt-4.1-mini', display_name='GPT-4.1 Mini', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='gpt-4.1', display_name='GPT-4.1', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='tts-1', display_name='OpenAI TTS', capabilities=['tts_plain']),
        ],
    ),
    ProviderPreset(
        provider_key='minimax',
        display_name='MiniMax',
        provider_type='openai_compatible',
        base_url='https://api.minimax.chat/v1',
        capabilities=['llm_text', 'tts_plain'],
        models=[
            ModelInfo(model_key='minimax-text-default', display_name='MiniMax 文本模型', capabilities=['llm_text']),
            ModelInfo(model_key='minimax-tts-default', display_name='MiniMax TTS', capabilities=['tts_plain']),
        ],
    ),
]


class ModelRegistry:
    """Registry for model providers."""

    def __init__(self):
        self._presets = {p.provider_key: p for p in BUILTIN_PRESETS}

    def get_presets(self) -> list[ProviderPreset]:
        return list(self._presets.values())

    def get_preset(self, provider_key: str) -> ProviderPreset | None:
        return self._presets.get(provider_key)

    def create_provider(
        self,
        provider_key: str,
        api_key: str,
        base_url: str = '',
        provider_type: str = '',
        **kwargs,
    ) -> ModelProvider:
        """Create a provider instance."""
        preset = self._presets.get(provider_key)

        if provider_key == 'mimo' or (preset and preset.provider_type == 'mimo'):
            return MimoProvider(api_key=api_key)

        if provider_key == 'openai' or (preset and preset.provider_type == 'openai'):
            url = base_url or (preset.base_url if preset else 'https://api.openai.com/v1')
            return OpenAIProvider(api_key=api_key, base_url=url)

        if preset and preset.provider_type == 'openai_compatible':
            return OpenAICompatibleProvider(
                provider_id=provider_key,
                api_key=api_key,
                base_url=base_url or preset.base_url,
            )

        if provider_type == 'openai_compatible':
            return OpenAICompatibleProvider(
                provider_id=provider_key,
                api_key=api_key,
                base_url=base_url,
            )

        raise ValueError(f'Unknown provider: {provider_key}')

    def get_all_models(self) -> list[dict]:
        """Return all available models grouped by provider."""
        result = []
        for preset in self._presets.values():
            for model in preset.models:
                result.append({
                    'provider_key': preset.provider_key,
                    'provider_name': preset.display_name,
                    'model_key': model.model_key,
                    'model_name': model.display_name,
                    'capabilities': model.capabilities,
                })
        return result
