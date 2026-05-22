import io
import wave
import pytest
from server.services.audio_package import read_wav_info, concat_wavs, build_srt


def _make_wav(duration_ms=1000, sample_rate=44100):
    """创建测试用 WAV 数据。"""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = int(sample_rate * duration_ms / 1000)
        wav.writeframes(b'\x00\x00' * frames)
    return buf.getvalue()


def test_read_wav_info():
    wav_bytes = _make_wav(1000)
    info = read_wav_info(wav_bytes)
    assert info['channels'] == 1
    assert info['sample_width'] == 2
    assert info['framerate'] == 44100
    assert info['frames'] == 44100


def test_concat_wavs():
    wav1 = _make_wav(1000)
    wav2 = _make_wav(1000)
    info1 = read_wav_info(wav1)
    info2 = read_wav_info(wav2)
    result = concat_wavs([info1, info2], gap=0.0)
    result_info = read_wav_info(result)
    assert result_info['frames'] == 88200


def test_concat_wavs_with_gap():
    wav1 = _make_wav(1000)
    wav2 = _make_wav(1000)
    info1 = read_wav_info(wav1)
    info2 = read_wav_info(wav2)
    result = concat_wavs([info1, info2], gap=0.5)
    result_info = read_wav_info(result)
    expected_frames = 44100 + int(0.5 * 44100) + 44100
    assert result_info['frames'] == expected_frames


def test_build_srt():
    timeline = [
        {'index': 1, 'text': '你好', 'start': 0.0, 'end': 1.0},
        {'index': 2, 'text': '世界', 'start': 1.0, 'end': 2.0},
    ]
    srt = build_srt(timeline)
    assert '00:00:00,000 --> 00:00:01,000' in srt
    assert '你好' in srt
    assert '世界' in srt
