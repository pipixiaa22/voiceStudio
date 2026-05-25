import json
import zipfile
import io
import pytest


def test_build_manifest():
    from server.services.capcut_package import build_manifest
    manifest = build_manifest(
        title='测试视频',
        template_key='xianxia_narration',
        duration=10.0,
        resolution=[1080, 1920],
        scenes=[{'index': 1, 'image': 'scene1.png'}],
        voice_chunks=[{'index': 1, 'text': '你好'}],
        subtitles=[{'index': 1, 'text': '你好', 'start': 0.0, 'end': 1.0}],
        audio={'voice': 'voice.wav', 'mixed': 'mixed.wav', 'bgm': 'bgm.mp3'},
    )
    assert manifest['title'] == '测试视频'
    assert manifest['template_key'] == 'xianxia_narration'
    assert manifest['duration'] == 10.0


def test_build_capcut_zip():
    from server.services.capcut_package import build_capcut_zip
    zip_bytes = build_capcut_zip(
        title='测试视频',
        video_bytes=b'fake-video',
        voice_audio=b'fake-voice',
        mixed_audio=b'fake-mixed',
        srt_content='1\n00:00:00,000 --> 00:00:01,000\n你好\n',
        manifest={'title': '测试', 'duration': 1.0},
        scene_files=[('scenes/001.png', b'fake-image')],
        bgm_bytes=b'fake-bgm',
    )
    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        names = zf.namelist()
        assert '测试视频_成片.mp4' in names
        assert '测试视频_完整旁白.wav' in names
        assert '测试视频_同步字幕.srt' in names
        assert 'manifest.json' in names
        assert 'scenes/001.png' in names
