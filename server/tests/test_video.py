import pytest
from server.routes.video import generate_ass_subtitle, get_resolution


def test_get_resolution_9_16():
    width, height = get_resolution('9:16')
    assert width == 1080
    assert height == 1920


def test_get_resolution_16_9():
    width, height = get_resolution('16:9')
    assert width == 1920
    assert height == 1080


def test_get_resolution_1_1():
    width, height = get_resolution('1:1')
    assert width == 1080
    assert height == 1080


def test_get_resolution_invalid():
    with pytest.raises(ValueError):
        get_resolution('invalid')


def test_generate_ass_subtitle():
    timeline = [
        {'start': 0.0, 'end': 3.0, 'text': '这是第一段字幕'},
        {'start': 3.0, 'end': 6.0, 'text': '这是第二段字幕'},
    ]
    ass_content = generate_ass_subtitle(timeline, 1920, 1080)

    assert '[Script Info]' in ass_content
    assert '[V4+ Styles]' in ass_content
    assert '[Events]' in ass_content
    assert '0:00:00.00' in ass_content
    assert '0:00:03.00' in ass_content
    assert '这是第一段字幕' in ass_content
    assert '这是第二段字幕' in ass_content


def test_generate_ass_subtitle_empty():
    ass_content = generate_ass_subtitle([], 1920, 1080)
    assert '[Script Info]' in ass_content
    assert 'Dialogue' not in ass_content
