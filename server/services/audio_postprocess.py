import io
import math
import struct
import wave


def _silence(info: dict, duration_ms: int) -> bytes:
    frames = round(info['framerate'] * duration_ms / 1000)
    return b'\x00' * frames * info['channels'] * info['sample_width']


def _apply_gain(frame_bytes: bytes, sample_width: int, volume_db: float) -> bytes:
    if not volume_db:
        return frame_bytes
    factor = math.pow(10, volume_db / 20)
    fmt_map = {1: 'b', 2: 'h', 4: 'i'}
    fmt_char = fmt_map.get(sample_width)
    if not fmt_char:
        return frame_bytes
    sample_count = len(frame_bytes) // sample_width
    fmt = f'<{sample_count}{fmt_char}'
    samples = list(struct.unpack(fmt, frame_bytes))
    max_val = (1 << (sample_width * 8 - 1)) - 1
    min_val = -(1 << (sample_width * 8 - 1))
    samples = [max(min_val, min(max_val, round(s * factor))) for s in samples]
    return struct.pack(fmt, *samples)


def concat_emotional_wavs(items: list[dict]) -> bytes:
    if not items:
        return b''
    base = items[0]['wav_info']
    for item in items[1:]:
        info = item['wav_info']
        if info['channels'] != base['channels'] or info['sample_width'] != base['sample_width'] or info['framerate'] != base['framerate']:
            raise ValueError('音频参数不一致，无法拼接')

    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(base['channels'])
        wav.setsampwidth(base['sample_width'])
        wav.setframerate(base['framerate'])
        for item in items:
            info = item['wav_info']
            segment = item['segment']
            wav.writeframes(_silence(info, int(segment.get('pause_before_ms') or 0)))
            frames = _apply_gain(info['frame_bytes'], info['sample_width'], float(segment.get('volume_db') or 0))
            wav.writeframes(frames)
            wav.writeframes(_silence(info, int(segment.get('pause_after_ms') or 0)))
    return output.getvalue()


def build_emotional_subtitle_timeline(segments: list[dict], durations: list[float]) -> list[dict]:
    timeline = []
    current_time = 0.0
    for index, (segment, duration) in enumerate(zip(segments, durations), 1):
        current_time += int(segment.get('pause_before_ms') or 0) / 1000
        start = current_time
        end = start + duration
        timeline.append({
            'index': index,
            'segment_id': segment.get('id'),
            'text': segment.get('text', ''),
            'start': round(start, 3),
            'end': round(end, 3),
        })
        current_time = end + int(segment.get('pause_after_ms') or 0) / 1000
    return timeline
