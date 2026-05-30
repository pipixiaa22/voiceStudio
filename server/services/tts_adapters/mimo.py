import base64

from server.services.tts_provider import TTSProvider
from server.services.tts_adapters.base import TTSSegmentRequest, TTSResult
from server.services.audio_package import read_wav_info


class MiMoAdapter:
    provider_id = 'mimo'

    def synthesize(self, request: TTSSegmentRequest, api_key: str) -> TTSResult:
        provider = TTSProvider(api_key)
        audio_b64 = provider.synthesize(
            voice_description=request.voice_description,
            text=request.text,
            style_tags=request.style_tags,
            model=request.model or 'mimo-v2.5-tts-voicedesign',
            voice=request.voice,
            optimize_text_preview=False,
        )
        audio_bytes = base64.b64decode(audio_b64)
        info = read_wav_info(audio_bytes)
        duration = info['frames'] / info['framerate']
        return TTSResult(
            audio_bytes=audio_bytes,
            duration=duration,
            model=request.model or 'mimo-v2.5-tts-voicedesign',
            provider='mimo',
        )
