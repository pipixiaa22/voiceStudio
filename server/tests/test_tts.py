import base64
import io
import json
import wave
import zipfile


def _make_wav(duration_seconds: float, framerate: int = 8000) -> bytes:
    frame_count = int(duration_seconds * framerate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(b'\x00\x00' * frame_count)
    return buf.getvalue()


def _wav_duration(data: bytes) -> float:
    with wave.open(io.BytesIO(data), 'rb') as wav:
        return wav.getnframes() / wav.getframerate()


def test_sync_package_exports_full_audio_timed_srt_and_segments(client, monkeypatch):
    wavs = [_make_wav(1.0), _make_wav(2.0)]
    calls = []

    def fake_call_tts(api_key, voice_description, text):
        calls.append((api_key, voice_description, text))
        return base64.b64encode(wavs[len(calls) - 1]).decode('ascii')

    monkeypatch.setattr('server.routes.tts._call_tts', fake_call_tts)

    response = client.post('/api/tts/sync-package', json={
        'api_key': 'test-key',
        'title': '测试作品',
        'default_voice_description': '温柔女声',
        'gap': 0.3,
        'segments': [
            {'text': '第一句', 'voice_description': ''},
            {'text': '第二句', 'voice_description': '沉稳男声'},
        ],
    })

    assert response.status_code == 200
    assert response.mimetype == 'application/zip'
    assert calls == [
        ('test-key', '温柔女声', '第一句'),
        ('test-key', '沉稳男声', '第二句'),
    ]

    with zipfile.ZipFile(io.BytesIO(response.data)) as zf:
        names = set(zf.namelist())
        assert '测试作品_完整音频.wav' in names
        assert '测试作品_同步字幕.srt' in names
        assert 'segments/001.wav' in names
        assert 'segments/002.wav' in names
        assert 'manifest.json' in names

        assert _wav_duration(zf.read('测试作品_完整音频.wav')) == 3.3
        assert _wav_duration(zf.read('segments/001.wav')) == 1.0
        assert _wav_duration(zf.read('segments/002.wav')) == 2.0

        srt = zf.read('测试作品_同步字幕.srt').decode('utf-8')
        assert '00:00:00,000 --> 00:00:01,000' in srt
        assert '00:00:01,300 --> 00:00:03,300' in srt
        assert '第一句' in srt
        assert '第二句' in srt

        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert manifest['title'] == '测试作品'
        assert manifest['gap'] == 0.3
        assert manifest['total_duration'] == 3.3
        assert manifest['segments'][0]['filename'] == 'segments/001.wav'
        assert manifest['segments'][1]['start'] == 1.3
