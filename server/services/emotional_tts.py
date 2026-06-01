import base64

from server.services.audio_package import read_wav_info
from server.services.emotion_planner import build_segment_delivery_instruction
from server.services.tts_provider import TTSProvider
from server.services.voice_prompt import build_voice_prompt
from server.services.voice_workflow_service import build_audio_fingerprint


def synthesize_emotion_segment(
    api_key: str,
    segment: dict,
    *,
    voice_profile: dict | None = None,
    fallback_voice_description: str = '',
    style_tags: str | None = None,
    model: str = 'mimo-v2.5-tts-voicedesign',
    voice: str | None = None,
) -> dict:
    prompt_profile = dict(voice_profile or {})
    if style_tags and not prompt_profile.get('style_tags'):
        prompt_profile['style_tags'] = style_tags
    base_prompt = build_voice_prompt(prompt_profile, fallback_description=fallback_voice_description)
    instruction = build_segment_delivery_instruction(segment)
    voice_description = '\n'.join([base_prompt, '本段表演：', instruction]).strip()
    provider = TTSProvider(api_key)
    audio_b64 = provider.synthesize(
        voice_description=voice_description,
        text=segment['text'],
        style_tags=None,
        model=model,
        voice=voice,
        optimize_text_preview=False,
        emotion_options=segment,
    )
    audio_bytes = base64.b64decode(audio_b64)
    info = read_wav_info(audio_bytes)
    duration = info['frames'] / info['framerate']
    fingerprint = build_audio_fingerprint({**segment, 'model': model})
    return {
        'audio_base64': audio_b64,
        'audio_bytes': audio_bytes,
        'wav_info': info,
        'duration': duration,
        'fingerprint': fingerprint,
    }
