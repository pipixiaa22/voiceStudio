import requests
from server.services.providers.openai_compatible_provider import OpenAICompatibleProvider
from server.services.model_provider_base import ModelInfo, ConnectionResult


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider with TTS support."""

    provider_id = 'openai'
    provider_type = 'openai'
    capabilities = ['llm_text', 'tts_plain', 'scene_planning', 'script_polish']

    def __init__(self, api_key: str, base_url: str = 'https://api.openai.com/v1', **kwargs):
        super().__init__(provider_id='openai', api_key=api_key, base_url=base_url, **kwargs)

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(model_key='gpt-4.1-mini', display_name='GPT-4.1 Mini', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='gpt-4.1', display_name='GPT-4.1', capabilities=['llm_text', 'scene_planning', 'script_polish']),
            ModelInfo(model_key='gpt-4o-mini-tts', display_name='GPT-4o Mini TTS', capabilities=['tts_plain']),
            ModelInfo(model_key='tts-1', display_name='OpenAI TTS (Legacy)', capabilities=['tts_plain']),
        ]

    def synthesize(self, text: str, model: str, voice_description: str = '', **options) -> bytes:
        voice = options.get('voice', 'alloy')
        speed = options.get('speed')
        url = f'{self.base_url.rstrip("/")}/audio/speech'

        payload = {
            'model': model or 'gpt-4o-mini-tts',
            'input': text,
            'voice': voice,
            'response_format': 'wav',
        }

        # Only send instructions for models that support it
        if voice_description and model in ('gpt-4o-mini-tts', 'gpt-4o-tts'):
            payload['instructions'] = voice_description

        if speed is not None:
            payload['speed'] = max(0.25, min(4.0, float(speed)))

        resp = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise ValueError(f'OpenAI TTS API 返回错误: {resp.status_code}')
        return resp.content
