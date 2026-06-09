# server/tests/test_novel_prompt_templates.py
from server.services.novel.prompt_templates import (
    get_genre_template,
    get_version_modifier,
    build_chapter_system_prompt,
    build_chapter_user_prompt,
    build_extract_prompt,
    build_review_prompt,
)


def test_get_genre_template():
    template = get_genre_template('玄幻')
    assert 'system' in template
    assert 'chapter_prompt' in template


def test_get_genre_template_unknown():
    template = get_genre_template('未知类型')
    assert template == get_genre_template('玄幻')


def test_get_version_modifier():
    modifier = get_version_modifier('conflict')
    assert '冲突' in modifier


def test_get_version_modifier_unknown():
    modifier = get_version_modifier('unknown')
    assert modifier == ''


def test_build_chapter_system_prompt():
    prompt = build_chapter_system_prompt('玄幻', version_type='conflict')
    assert '玄幻' in prompt
    assert '冲突' in prompt


def test_build_chapter_system_prompt_with_style():
    prompt = build_chapter_system_prompt('都市', style_guide={
        'pov': '第三人称有限',
        'taboos': ['不要让主角突然无脑'],
    })
    assert '第三人称有限' in prompt
    assert '不要让主角突然无脑' in prompt


def test_build_chapter_user_prompt():
    context = {
        'outline': '本章大纲内容',
        'text_tail': '上一章结尾',
        'target_words': 3000,
    }
    prompt = build_chapter_user_prompt(context)
    assert '本章大纲内容' in prompt
    assert '3000' in prompt


def test_build_extract_prompt():
    prompt = build_extract_prompt('章节正文内容')
    assert '章节正文内容' in prompt
    assert 'JSON' in prompt


def test_build_review_prompt():
    prompt = build_review_prompt('章节正文', {'characters': '人物设定'})
    assert '章节正文' in prompt
    assert '人物设定' in prompt


def test_build_review_prompt_includes_outline_context():
    from server.services.novel.prompt_templates import build_review_prompt

    context = {
        'characters': '人物设定',
        'world_rules': '世界观规则',
        'previous_summaries': '前文摘要',
        'overall_outline': '全书主线：少年成长',
        'volume_outline': '卷大纲：第一卷开篇',
        'outline': '章大纲：第一章踏上旅途',
    }
    prompt = build_review_prompt('章节正文', context)
    assert '少年成长' in prompt
    assert '第一卷开篇' in prompt
    assert '踏上旅途' in prompt
    assert '偏离' in prompt
