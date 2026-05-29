import io
import wave

from server.services.audio_package import read_wav_info
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline


def _make_wav(duration_ms=100, sample_rate=8000, amplitude=1000):
    frames = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        sample = int(amplitude).to_bytes(2, byteorder='little', signed=True)
        wav.writeframes(sample * frames)
    return buf.getvalue()


def test_concat_emotional_wavs_applies_individual_pauses():
    wav1 = read_wav_info(_make_wav(100))
    wav2 = read_wav_info(_make_wav(100))

    audio = concat_emotional_wavs([
        {'wav_info': wav1, 'segment': {'pause_before_ms': 0, 'pause_after_ms': 250, 'volume_db': 0}},
        {'wav_info': wav2, 'segment': {'pause_before_ms': 80, 'pause_after_ms': 0, 'volume_db': 0}},
    ])

    info = read_wav_info(audio)
    assert info['frames'] == 800 + 2000 + 640 + 800


def test_build_emotional_subtitle_timeline_uses_pauses():
    timeline = build_emotional_subtitle_timeline([
        {'id': 1, 'text': '我知道了。', 'pause_before_ms': 0, 'pause_after_ms': 250},
        {'id': 2, 'text': '可是你为什么现在才告诉我！', 'pause_before_ms': 80, 'pause_after_ms': 180},
    ], [1.0, 2.0])

    assert timeline[0]['start'] == 0
    assert timeline[0]['end'] == 1
    assert timeline[1]['start'] == 1.33
    assert timeline[1]['end'] == 3.33
