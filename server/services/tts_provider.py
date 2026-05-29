import requests

MIMO_TTS_URL = 'https://api.xiaomimimo.com/v1/chat/completions'


class TTSProvider:
    """封装 MiMo TTS API 调用。"""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError('API Key 不能为空')
        self.api_key = api_key

    def synthesize(
        self,
        voice_description: str,
        text: str,
        *,
        style_tags: str | None = None,
        model: str = 'mimo-v2.5-tts-voicedesign',
        voice: str | None = None,
        optimize_text_preview: bool = False,
        emotion_options: dict | None = None,
    ) -> bytes:
        """调用 TTS 合成语音，返回 base64 编码的音频数据。"""
        assistant_text = _apply_style_tags(text, style_tags)
        messages = [
            {'role': 'user', 'content': voice_description or ''},
            {'role': 'assistant', 'content': assistant_text},
        ]

        audio = {
            'format': 'wav',
            'optimize_text_preview': optimize_text_preview,
        }
        if voice:
            audio['voice'] = voice

        payload = {
            'model': model,
            'messages': messages,
            'audio': audio,
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


def _apply_style_tags(text: str, style_tags: str | None) -> str:
    """Place MiMo audio style tags at the beginning of assistant content."""
    cleaned_tags = (style_tags or '').strip()
    if not cleaned_tags:
        return text
    if cleaned_tags[0] in '([（［【':
        return f'{cleaned_tags}{text}'
    return f'（{cleaned_tags}）{text}'
