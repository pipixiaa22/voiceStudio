import json
import pytest


def test_get_builtin_templates():
    from server.services.video_template import get_builtin_templates
    templates = get_builtin_templates()
    assert len(templates) == 5
    assert templates[0]['template_key'] == 'xianxia_narration'


def test_seed_templates(app, db):
    from server.services.video_template import seed_builtin_templates, get_all_templates
    seed_builtin_templates()
    templates = get_all_templates()
    assert len(templates) == 5
    assert templates[0].template_key == 'xianxia_narration'
    assert templates[0].is_builtin is True


def test_seed_templates_idempotent(app, db):
    from server.services.video_template import seed_builtin_templates, get_all_templates
    seed_builtin_templates()
    seed_builtin_templates()
    templates = get_all_templates()
    assert len(templates) == 5


def test_get_template_by_key(app, db):
    from server.services.video_template import seed_builtin_templates, get_template_by_key
    seed_builtin_templates()
    template = get_template_by_key('xianxia_narration')
    assert template is not None
    assert template.name == '修仙旁白'


def test_get_template_by_key_not_found(app, db):
    from server.services.video_template import get_template_by_key
    template = get_template_by_key('nonexistent')
    assert template is None
