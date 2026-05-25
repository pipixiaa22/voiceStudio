import pytest


def test_get_motion_function_slow_zoom_in():
    from server.services.video_renderer import get_motion_function
    fn = get_motion_function('slow_zoom_in')
    assert fn is not None
    result = fn(0.5, 1080, 1920, 0.0, 10.0)
    assert 'position' in result
    assert 'size' in result


def test_get_motion_function_unknown():
    from server.services.video_renderer import get_motion_function
    fn = get_motion_function('unknown_motion')
    assert fn is not None
    result = fn(0.5, 1080, 1920, 0.0, 10.0)
    assert 'position' in result


def test_motion_slow_zoom_in():
    from server.services.video_renderer import motion_slow_zoom_in
    result = motion_slow_zoom_in(0.0, 1080, 1920, 0.0, 10.0)
    assert result['scale'] == 1.0
    result = motion_slow_zoom_in(1.0, 1080, 1920, 0.0, 10.0)
    assert result['scale'] > 1.0


def test_motion_breathing_zoom():
    from server.services.video_renderer import motion_breathing_zoom
    result = motion_breathing_zoom(0.0, 1080, 1920, 0.0, 10.0)
    assert result['scale'] >= 1.0


def test_motion_pan_left_right():
    from server.services.video_renderer import motion_pan_left_right
    result = motion_pan_left_right(0.0, 1080, 1920, 0.0, 10.0)
    assert 'position' in result
