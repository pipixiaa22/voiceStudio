import requests

from server.services.tts_adapters.base import TTSSegmentRequest, TTSResult
from server.services.audio_package import read_wav_info

SUPPORTED_INSTRUCTIONS_MODELS = {'gpt-4o-mini-tts', 'gpt-4o-tts'}


class OpenAIAdapter:
    provider_id = 'openai'

    def __init__(self, api_key: str, base_url: str = 'https://api.openai.com/v1'):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    def synthesize(self, request: TTSSegmentRequest) -> TTSResult:
        model = request.model or 'gpt-4o-mini-tts'
        payload = {
            'model': model,
            'input': request.text,
            'voice': request.voice or 'alloy',
            'response_format': 'wav',
        }
        # Only send instructions for models that support it
        if model in SUPPORTED_INSTRUCTIONS_MODELS and request.voice_description:
            payload['instructions'] = request.voice_description

        resp = requests.post(
            f'{self.base_url}/audio/speech',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise ValueError(f'OpenAI TTS API 返回错误: {resp.status_code}')

        audio_bytes = resp.content
        info = read_wav_info(audio_bytes)
        duration = info['frames'] / info['framerate']
        return TTSResult(
            audio_bytes=audio_bytes,
            duration=duration,
            model=model,
            provider='openai',
        )
