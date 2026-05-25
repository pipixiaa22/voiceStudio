import json
from server.models import db, VideoTemplate

BUILTIN_TEMPLATES = [
    {
        'template_key': 'xianxia_narration',
        'name': '修仙旁白',
        'sort_order': 1,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': 'mist',
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.18,
                'voice_volume': 1.0,
                'ambient_volume': 0.12,
                'fade_in': 1.0,
                'fade_out': 1.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'character_monologue',
        'name': '角色独白',
        'sort_order': 2,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': None,
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.10,
                'voice_volume': 1.0,
                'ambient_volume': 0.08,
                'fade_in': 0.5,
                'fade_out': 1.0,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'chapter_title',
        'name': '章节标题',
        'sort_order': 3,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'fixed',
            'fixed_duration': 5.0,
            'visual_effects': {
                'motion': 'fade_in',
                'overlay': None,
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.15,
                'voice_volume': 1.0,
                'ambient_volume': 0.0,
                'fade_in': 0.5,
                'fade_out': 1.0,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'battle_transition',
        'name': '战斗转场',
        'sort_order': 4,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 30,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'shake',
                'overlay': 'flash',
                'transition': 'cut',
            },
            'audio': {
                'bgm_volume': 0.25,
                'voice_volume': 1.0,
                'ambient_volume': 0.20,
                'fade_in': 0.3,
                'fade_out': 0.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'technique_explain',
        'name': '功法讲解',
        'sort_order': 5,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': None,
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.12,
                'voice_volume': 1.0,
                'ambient_volume': 0.05,
                'fade_in': 1.0,
                'fade_out': 1.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
]


def get_builtin_templates() -> list[dict]:
    return BUILTIN_TEMPLATES


def seed_builtin_templates():
    for tmpl in BUILTIN_TEMPLATES:
        existing = VideoTemplate.query.filter_by(template_key=tmpl['template_key']).first()
        if not existing:
            db.session.add(VideoTemplate(
                template_key=tmpl['template_key'],
                name=tmpl['name'],
                config_json=json.dumps(tmpl['config'], ensure_ascii=False),
                is_builtin=True,
                sort_order=tmpl.get('sort_order', 0),
            ))
    db.session.commit()


def get_all_templates() -> list[VideoTemplate]:
    return VideoTemplate.query.filter_by(is_active=True).order_by(VideoTemplate.sort_order).all()


def get_template_by_key(key: str) -> VideoTemplate | None:
    return VideoTemplate.query.filter_by(template_key=key, is_active=True).first()


def get_template_config(key: str) -> dict | None:
    template = get_template_by_key(key)
    if not template:
        return None
    return json.loads(template.config_json)
