import re
from dataclasses import dataclass, field

from splitter import _merge_with_delimiters, _split_by_comma


EMOTION_PRESETS = {
    'neutral': {'intensity': 0.5, 'rate': 1.0, 'pitch': 0, 'volume_db': 0, 'pause_after_ms': 250},
    'calm': {'intensity': 0.25, 'rate': 0.95, 'pitch': -1, 'volume_db': -1, 'pause_after_ms': 250},
    'suppressed': {'intensity': 0.55, 'rate': 0.9, 'pitch': -1, 'volume_db': -2, 'pause_after_ms': 350},
    'angry_burst': {'intensity': 1.6, 'rate': 1.15, 'pitch': 2, 'volume_db': 3, 'pause_after_ms': 180},
    'sad': {'intensity': 0.8, 'rate': 0.85, 'pitch': -2, 'volume_db': -1, 'pause_after_ms': 500},
    'cold': {'intensity': 0.7, 'rate': 0.8, 'pitch': -2, 'volume_db': -2, 'pause_after_ms': 450},
    'excited': {'intensity': 1.2, 'rate': 1.12, 'pitch': 1, 'volume_db': 2, 'pause_after_ms': 180},
    'whisper': {'intensity': 0.4, 'rate': 0.85, 'pitch': -2, 'volume_db': -4, 'pause_after_ms': 420},
}


@dataclass
class EmotionSegment:
    index: int
    text: str
    subtitle_indices: list[int] = field(default_factory=list)
    emotion: str = 'neutral'
    intensity: float = 0.5
    rate: float = 1.0
    pitch: float = 0.0
    volume_db: float = 0.0
    pause_before_ms: int = 0
    pause_after_ms: int = 250
    transition: str = 'normal'
    delivery_instruction: str = ''
    voice_profile_id: int | None = None


def _split_preserving_punct(text: str, max_chars: int = 80) -> list[str]:
    """Split text by punctuation like split_text but preserve trailing punctuation for TTS."""
    text = text.strip()
    if not text:
        return []

    sentences = re.split(r'([。？！…]+)', text)
    merged = _merge_with_delimiters(sentences)

    result = []
    for sentence in merged:
        if not sentence.strip():
            continue
        if len(sentence) <= max_chars:
            result.append(sentence)
        else:
            result.extend(_split_by_comma(sentence, max_chars))

    return [s for s in result if s.strip()]


def _detect_emotion(text: str) -> str:
    if re.search(r'[!！]{1,}|[?？][!！]|[!！][?？]', text):
        return 'angry_burst'
    if any(word in text for word in ('为什么', '凭什么', '你怎么敢')):
        return 'angry_burst'
    if any(word in text for word in ('算了', '不必了', '我没事')):
        return 'cold'
    if '……' in text or text.count('.') >= 3:
        return 'suppressed'
    return 'calm'


def _preset_payload(emotion: str) -> dict:
    preset = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS['neutral'])
    return {
        'emotion': emotion,
        'intensity': preset['intensity'],
        'rate': preset['rate'],
        'pitch': preset['pitch'],
        'volume_db': preset['volume_db'],
        'pause_before_ms': 80 if emotion == 'angry_burst' else 0,
        'pause_after_ms': preset['pause_after_ms'],
        'transition': 'burst' if emotion == 'angry_burst' else 'normal',
        'delivery_instruction': '',
    }


def plan_workflow_segments(content: str, max_chars: int = 80) -> list[dict]:
    segments = []
    for index, text in enumerate(_split_preserving_punct(content or '', max_chars=max_chars), 1):
        clean_text = text.strip()
        if not clean_text:
            continue
        emotion = _detect_emotion(clean_text)
        payload = _preset_payload(emotion)
        payload.update({
            'order_index': index,
            'text': clean_text,
            'node_x': 80 + (index - 1) * 240,
            'node_y': 120 + ((index - 1) % 2) * 80,
            'voice_profile_id': None,
            'audio_status': 'missing',
        })
        segments.append(payload)
    return segments


def build_segment_delivery_instruction(segment: EmotionSegment | dict) -> str:
    get = segment.get if isinstance(segment, dict) else lambda key, default=None: getattr(segment, key, default)
    emotion = get('emotion', 'neutral')
    transition = get('transition', 'normal')
    rate = float(get('rate', 1.0))
    volume_db = float(get('volume_db', 0.0))
    custom = (get('delivery_instruction', '') or '').strip()

    emotion_text = {
        'calm': '平静、克制、自然',
        'suppressed': '压抑、低声、保留情绪',
        'angry_burst': '情绪突然爆发，重音更强',
        'sad': '悲伤、放慢、带停顿',
        'cold': '冷漠、疏离、压低声音',
        'excited': '兴奋、明亮、节奏更快',
        'whisper': '接近耳语，气声更明显',
    }.get(emotion, '自然中性')
    transition_text = '这句话紧接上一句，仍使用同一个说话人音色。'
    if transition == 'burst':
        transition_text = '这句话从上一句突然爆发，但仍使用同一个说话人音色。'

    rate_text = '语速保持自然。'
    if rate > 1.05:
        rate_text = '语速加快，但吐字保持清楚。'
    elif rate < 0.95:
        rate_text = '语速放慢，停顿更明显。'

    volume_text = '音量保持自然。'
    if volume_db > 1:
        volume_text = '音量提高，重音更强。'
    elif volume_db < -1:
        volume_text = '音量压低，表达更内收。'

    lines = [
        transition_text,
        f'表演方式：{emotion_text}。',
        rate_text,
        volume_text,
        '边界：不要破音，不要像换了一个人，不要夸张到卡通化。',
    ]
    if custom:
        lines.append(f'用户补充：{custom}')
    return '\n'.join(lines)
