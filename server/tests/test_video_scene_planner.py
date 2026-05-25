import pytest


def test_plan_scenes_single_image():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=['你好', '世界'],
        chunk_durations=[1.0, 1.0],
        images=['scene1.png'],
        motion='slow_zoom_in',
        gap=0.3,
    )
    assert len(scenes) == 1
    assert scenes[0]['image'] == 'scene1.png'
    assert scenes[0]['start'] == 0.0


def test_plan_scenes_multiple_images():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=['你好', '世界', '测试'],
        chunk_durations=[1.0, 1.0, 1.0],
        images=['scene1.png', 'scene2.png'],
        motion='slow_zoom_in',
        gap=0.3,
    )
    assert len(scenes) == 2
    assert scenes[0]['image'] == 'scene1.png'
    assert scenes[1]['image'] == 'scene2.png'


def test_plan_scenes_default_motion():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=['你好'],
        chunk_durations=[2.0],
        images=['scene1.png'],
    )
    assert scenes[0]['motion'] == 'slow_zoom_in'


def test_plan_scenes_empty():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=[],
        chunk_durations=[],
        images=[],
    )
    assert len(scenes) == 0
