import requests
from server.services.model_provider_base import ModelProvider, ModelInfo, ConnectionResult


MIMO_TTS_URL = 'https://api.xiaomimimo.com/v1/chat/completions'
MIMO_LLM_URL = 'https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages'


class MimoProvider(ModelProvider):
    """MiMo provider for TTS and LLM."""

    provider_id = 'mimo'
    provider_type = 'mimo'
    capabilities = ['tts_voice_design', 'tts_voice_clone', 'tts_builtin_voice', 'llm_text', 'llm_voice_prompt_polish']

    def __init__(self, api_key: str, **kwargs):
        super().__init__(provider_id='mimo', api_key=api_key, **kwargs)

    def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(model_key='mimo-v2.5-tts-voicedesign', display_name='MiMo 音色设计', capabilities=['tts_voice_design']),
            ModelInfo(model_key='mimo-v2.5-tts-voiceclone', display_name='MiMo 音色复刻', capabilities=['tts_voice_clone']),
            ModelInfo(model_key='mimo-v2.5-tts', display_name='MiMo 预置音色', capabilities=['tts_builtin_voice']),
            ModelInfo(model_key='mimo-v2.5-pro', display_name='MiMo Pro', capabilities=['llm_text', 'llm_voice_prompt_polish']),
        ]

    def test_connection(self, model: str = '', capability: str = '') -> ConnectionResult:
        import time
        start = time.time()
        try:
            resp = requests.post(
                MIMO_TTS_URL,
                headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
                json={
                    'model': model or 'mimo-v2.5-tts-voicedesign',
                    'messages': [
                        {'role': 'user', 'content': 'test'},
                        {'role': 'assistant', 'content': 'test'},
                    ],
                    'audio': {'format': 'wav'},
                },
                timeout=10,
            )
            if resp.status_code == 200:
                latency = int((time.time() - start) * 1000)
                return ConnectionResult(ok=True, latency_ms=latency, message='连接成功')
            return ConnectionResult(ok=False, message=f'API 返回错误: {resp.status_code}')
        except requests.RequestException as e:
            return ConnectionResult(ok=False, message=f'连接失败: {str(e)}')

    def synthesize(self, text: str, model: str, voice_description: str = '', **options) -> bytes:
        import base64
        style_tags = options.get('style_tags', '')
        voice = options.get('voice', '')

        assistant_text = text
        if style_tags:
            tags = style_tags.strip()
            assistant_text = f'{tags}{text}' if tags[0] in '([（［【' else f'（{tags}）{text}'

        audio_config = {'format': 'wav'}
        if voice:
            audio_config['voice'] = voice

        resp = requests.post(
            MIMO_TTS_URL,
            headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
            json={
                'model': model or 'mimo-v2.5-tts-voicedesign',
                'messages': [
                    {'role': 'user', 'content': voice_description or ''},
                    {'role': 'assistant', 'content': assistant_text},
                ],
                'audio': audio_config,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise ValueError(f'MiMo API 返回错误: {resp.status_code}')
        result = resp.json()
        audio_b64 = result['choices'][0]['message']['audio']['data']
        return base64.b64decode(audio_b64)

    def complete(self, messages: list[dict], model: str, **options) -> str:
        system_prompt = options.get('system_prompt', '')
        max_tokens = options.get('max_tokens', 1024)

        payload = {
            'model': model or 'mimo-v2.5-pro',
            'max_tokens': max_tokens,
            'messages': messages,
        }
        if system_prompt:
            payload['system'] = system_prompt

        resp = requests.post(
            MIMO_LLM_URL,
            headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise ValueError(f'MiMo API 返回错误: {resp.status_code}')
        result = resp.json()
        return result['content'][0]['text']
