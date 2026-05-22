import requests

MIMO_TTS_URL = 'https://api.xiaomimimo.com/v1/chat/completions'


class TTSProvider:
    """封装 MiMo TTS API 调用。"""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError('API Key 不能为空')
        self.api_key = api_key

    def synthesize(self, voice_description: str, text: str) -> bytes:
        """调用 TTS 合成语音，返回 base64 编码的音频数据。"""
        import base64

        payload = {
            'model': 'mimo-v2.5-tts-voicedesign',
            'messages': [
                {'role': 'user', 'content': voice_description},
                {'role': 'assistant', 'content': text},
            ],
            'audio': {'format': 'wav'},
        }

        resp = requests.post(
            MIMO_TTS_URL,
            headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
            json=payload,
            timeout=60,
        )

        if resp.status_code != 200:
            raise ValueError(f'MiMo API 返回错误: {resp.status_code}')

        result = resp.json()
        return result['choices'][0]['message']['audio']['data']
