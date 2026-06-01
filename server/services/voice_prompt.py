GENDER_LABELS = {
    'female': '女声',
    'male': '男声',
    'neutral': '中性声线',
}

SPEED_LABELS = {
    'slow': '慢速',
    'medium_slow': '中等偏慢',
    'medium': '中速',
    'medium_fast': '中等偏快',
    'fast': '快速',
}

EMOTION_LABELS = {
    'gentle': '温和',
    'calm': '稳重',
    'lively': '轻快',
    'restrained': '克制',
    'healing': '治愈',
    'powerful': '有力',
    'natural': '自然',
    'professional': '专业',
}

SCENE_LABELS = {
    'xianxia_character': '修仙角色',
    'short_video': '短视频旁白',
    'course': '课程讲解',
    'story': '故事朗读',
    'news': '新闻资讯',
    'business': '商务介绍',
    'ad': '广告口播',
    'vlog': 'vlog',
}

DEFAULT_NEGATIVE_PROMPT = '不要播音腔，不要夸张喊叫，不要综艺感'

DEFAULT_AUDITION_TEXT = (
    '（平静旁白）三百年前，他被宗门废去灵根，扔进万丈寒渊。\n'
    '（高燃冲突）可没人知道，那一夜，他在深渊里睁开了第三只眼。\n'
    '（悬念收尾）而今日，山门大开，那个被所有人遗忘的名字，回来了。'
)


def build_voice_prompt(
    profile: dict | None = None,
    *,
    raw_description: str = '',
    fallback_description: str = '',
) -> str:
    """Build a stable TTS voice prompt from profile metadata or raw text."""
    profile = profile or {}
    identity = _first_text(
        profile.get('canonical_prompt'),
        profile.get('raw_description'),
        raw_description,
        fallback_description,
    )

    sections = []
    identity_lines = [identity] if identity else []
    identity_lines.extend(_profile_identity_lines(profile))
    if _is_voice_clone(profile):
        identity_lines.append('参考音频中的声线身份优先，文字提示只用于补充表演方式。')
    if _looks_like_sectioned_prompt(identity):
        sections.append(identity)
        if _is_voice_clone(profile):
            sections.append('复刻约束：参考音频中的声线身份优先，文字提示只用于补充表演方式。')
    elif identity_lines:
        sections.append(_format_section('声音身份', identity_lines))

    performance_lines = _profile_performance_lines(profile)
    if not performance_lines:
        performance_lines = ['语速自然稳定，吐字清楚，按文本语义和标点做停顿。']
    if performance_lines:
        sections.append(_format_section('播讲风格', performance_lines))

    stability_lines = [
        '同一次任务内保持同一声线、同一年龄感、同一口音和相近语速。',
        '根据文本标点自然停顿，句尾收束清楚，避免每句都用相同腔调。',
    ]
    if _is_voice_clone(profile):
        stability_lines.append('不要把提示词表演成另一个人。')
    sections.append(_format_section('稳定性要求', stability_lines))

    negative = _first_text(profile.get('negative_prompt'), DEFAULT_NEGATIVE_PROMPT)
    sections.append(f'负向约束：{negative}')

    return '\n'.join(sections)


def build_audition_text(profile: dict | None = None, text: str = '') -> str:
    """Return provided/profile audition text or a fixed multi-style benchmark."""
    profile = profile or {}
    return _first_text(text, profile.get('audition_text'), DEFAULT_AUDITION_TEXT)


def _profile_identity_lines(profile: dict) -> list[str]:
    lines = []
    if profile.get('language'):
        lines.append(f"语言：{profile['language']}")
    if profile.get('gender'):
        lines.append(f"性别：{GENDER_LABELS.get(profile['gender'], profile['gender'])}")
    if profile.get('age_group'):
        lines.append(f"年龄感：{profile['age_group']}")
    if profile.get('accent'):
        lines.append(f"口音：{profile['accent']}")
    if profile.get('timbre'):
        lines.append(f"音色质感：{profile['timbre']}")
    return lines


def _profile_performance_lines(profile: dict) -> list[str]:
    lines = []
    if profile.get('scene'):
        lines.append(f"使用场景：{SCENE_LABELS.get(profile['scene'], profile['scene'])}")
    if profile.get('speed'):
        lines.append(f"语速：{SPEED_LABELS.get(profile['speed'], profile['speed'])}")
    if profile.get('emotion'):
        lines.append(f"情绪：{EMOTION_LABELS.get(profile['emotion'], profile['emotion'])}")
    if profile.get('style_tags'):
        lines.append(f"音频标签：{profile['style_tags']}")
    return lines


def _format_section(title: str, lines: list[str]) -> str:
    body = '\n'.join(f'- {line}' for line in lines if str(line).strip())
    return f'{title}：\n{body}'


def _first_text(*values) -> str:
    for value in values:
        text = str(value or '').strip()
        if text:
            return text
    return ''


def _is_voice_clone(profile: dict) -> bool:
    return (
        profile.get('source_type') == 'voice_clone'
        or profile.get('model') == 'mimo-v2.5-tts-voiceclone'
        or bool(profile.get('voice_sample_data_uri'))
    )


def _looks_like_sectioned_prompt(text: str) -> bool:
    return any(
        marker in text
        for marker in ('声音身份：', '人物人设：', '播讲预期：', '负向约束：')
    )
