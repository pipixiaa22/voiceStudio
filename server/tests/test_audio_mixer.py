import struct
import wave
import io
import pytest


def _make_wav_bytes(duration_sec=1.0, frequency=440, sample_rate=16000):
    """Create a simple sine wave WAV for testing."""
    import math
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(16000 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', value))
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(samples))
    return buf.getvalue()


def test_mix_audio_basic():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(2.0)
    result = mix_audio(voice_wav=voice)
    assert len(result) > 0
    with wave.open(io.BytesIO(result), 'rb') as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000


def test_mix_audio_with_bgm():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(2.0)
    bgm = _make_wav_bytes(5.0, frequency=220)
    result = mix_audio(voice_wav=voice, bgm_wav=bgm, bgm_volume=0.2)
    assert len(result) > 0
    assert result != voice


def test_mix_audio_bgm_loops_when_shorter():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(3.0)
    bgm = _make_wav_bytes(1.0, frequency=220)
    result = mix_audio(voice_wav=voice, bgm_wav=bgm, bgm_volume=0.2)
    with wave.open(io.BytesIO(result), 'rb') as wav:
        duration = wav.getnframes() / wav.getframerate()
        assert duration >= 2.9


def test_mix_audio_with_ambient():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(2.0)
    ambient = _make_wav_bytes(3.0, frequency=100)
    result = mix_audio(voice_wav=voice, ambient_wav=ambient, ambient_volume=0.1)
    assert len(result) > 0


def test_mix_audio_fade_in_out():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(3.0)
    bgm = _make_wav_bytes(5.0, frequency=220)
    result = mix_audio(voice_wav=voice, bgm_wav=bgm, bgm_volume=0.2, fade_in=0.5, fade_out=0.5)
    assert len(result) > 0
