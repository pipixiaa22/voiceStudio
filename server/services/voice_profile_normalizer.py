from server.services.voice_prompt import (
    EMOTION_LABELS,
    GENDER_LABELS,
    SCENE_LABELS,
    SPEED_LABELS,
    DEFAULT_NEGATIVE_PROMPT,
)


PERSONA_FIELDS = (
    'role_name',
    'archetype',
    'personality',
    'speaking_habit',
    'relationship_to_listener',
    'persona_prompt',
)


def normalize_voice_profile_payload(data: dict) -> tuple[dict, str | None]:
    """Normalize a create/update payload into a production-ready voice profile."""
    normalized = dict(data or {})
    _strip_strings(normalized)

    if not _has_enough_expectation_signal(normalized):
        return normalized, '请至少填写声音描述，或补充音色质感、角色人设、说话习惯等关键信息'

    raw_description = normalized.get('raw_description') or _compose_raw_description(normalized)
    if not raw_description:
        return normalized, '请至少填写声音描述，或补充音色质感、角色人设、说话习惯等关键信息'
    normalized['raw_description'] = raw_description

    normalized['negative_prompt'] = (
        normalized.get('negative_prompt') or DEFAULT_NEGATIVE_PROMPT
    )
    normalized['canonical_prompt'] = normalized.get('canonical_prompt') or build_canonical_voice_profile_prompt(normalized)
    normalized['description'] = normalized.get('description') or build_voice_profile_summary(normalized)
    normalized['audition_text'] = normalized.get('audition_text') or build_profile_audition_text(normalized)

    return normalized, None


def build_canonical_voice_profile_prompt(profile: dict) -> str:
    sections = []

    identity_lines = _compact([
        profile.get('raw_description'),
        _field_line('语言', profile.get('language') or 'zh-CN'),
        _field_line('性别', _label(GENDER_LABELS, profile.get('gender'))),
        _field_line('年龄感', profile.get('age_group')),
        _field_line('口音', profile.get('accent')),
        _field_line('音色质感', profile.get('timbre')),
    ])
    if identity_lines:
        sections.append(_format_section('声音身份', identity_lines))

    persona_lines = _compact([
        _field_line('角色或身份', profile.get('role_name')),
        _field_line('角色类型', profile.get('archetype')),
        _field_line('性格', profile.get('personality')),
        _field_line('说话习惯', profile.get('speaking_habit')),
        _field_line('听众关系', profile.get('relationship_to_listener')),
        profile.get('persona_prompt'),
    ])
    if persona_lines:
        sections.append(_format_section('人物人设', persona_lines))

    delivery_lines = _compact([
        _field_line('使用场景', _label(SCENE_LABELS, profile.get('scene'))),
        _field_line('基础情绪', _label(EMOTION_LABELS, profile.get('emotion'))),
        _field_line('基础语速', _label(SPEED_LABELS, profile.get('speed'))),
        _field_line('音频标签', profile.get('style_tags')),
        '合成时正文应与该角色、场景和情绪一致；不要把短期表演情绪改写成新的声线身份。',
    ])
    sections.append(_format_section('播讲预期', delivery_lines))

    negative = profile.get('negative_prompt') or DEFAULT_NEGATIVE_PROMPT
    sections.append(f'负向约束：{negative}')

    return '\n'.join(sections)


def build_voice_profile_summary(profile: dict) -> str:
    parts = _compact([
        _label(GENDER_LABELS, profile.get('gender')),
        profile.get('age_group'),
        profile.get('timbre'),
        _label(SCENE_LABELS, profile.get('scene')),
        profile.get('role_name') or profile.get('archetype'),
    ])
    return ' / '.join(parts[:5]) or (profile.get('raw_description') or '')[:80]


def build_profile_audition_text(profile: dict) -> str:
    scene = profile.get('scene')
    role = profile.get('role_name') or profile.get('archetype')

    if scene == 'course':
        return '（课程讲解）这一节我们先抓住核心概念，再用一个简单例子，把复杂问题拆成三步。'
    if scene == 'news':
        return '（资讯播报）最新消息显示，相关方案已经进入执行阶段，后续进展仍需持续关注。'
    if scene == 'ad':
        return '（自然口播）如果你也想把效率提上来，可以先从这个小工具开始试试。'
    if scene == 'xianxia_character' or role:
        name = role or '这个角色'
        return f'（平静）{name}缓缓开口，把每个字都压得很稳。\n（冲突）可到了这一刻，他终于不再退让。\n（收束）风声停下时，答案已经写在众人眼前。'
    return '（自然旁白）先用一句平静的话建立信任。\n（情绪推进）随后稍微加强语气，让重点变得更清楚。\n（收束）最后放慢一点，把余味留给听众。'


def _compose_raw_description(profile: dict) -> str:
    if _is_voice_clone(profile) and not any(profile.get(field) for field in ('timbre', 'role_name', 'archetype', 'personality', 'speaking_habit')):
        return '以授权样音中的声线身份为准，文字提示只补充场景和表演方式'

    lines = _compact([
        profile.get('timbre'),
        _label(GENDER_LABELS, profile.get('gender')),
        profile.get('age_group'),
        profile.get('accent'),
        profile.get('role_name'),
        profile.get('archetype'),
        profile.get('personality'),
        profile.get('speaking_habit'),
        _label(SCENE_LABELS, profile.get('scene')),
    ])
    return '，'.join(lines)


def _has_enough_expectation_signal(profile: dict) -> bool:
    if _is_voice_clone(profile) and profile.get('voice_sample_data_uri'):
        return True

    raw = profile.get('raw_description') or ''
    if len(raw) >= 6:
        return True

    strong_fields = (
        'timbre',
        'role_name',
        'archetype',
        'personality',
        'speaking_habit',
        'persona_prompt',
    )
    if any(profile.get(field) for field in strong_fields):
        return True

    weak_fields = (
        'gender',
        'age_group',
        'accent',
        'speed',
        'emotion',
        'scene',
        'style_tags',
    )
    return sum(1 for field in weak_fields if profile.get(field)) >= 3


def _is_voice_clone(profile: dict) -> bool:
    return profile.get('source_type') == 'voice_clone' or bool(profile.get('voice_sample_data_uri'))


def _strip_strings(data: dict):
    for key, value in list(data.items()):
        if isinstance(value, str):
            data[key] = value.strip()


def _field_line(label: str, value: str | None) -> str:
    return f'{label}：{value}' if value else ''


def _label(labels: dict, value: str | None) -> str:
    if not value:
        return ''
    return labels.get(value, value)


def _compact(values) -> list[str]:
    return [str(value).strip() for value in values if str(value or '').strip()]


def _format_section(title: str, lines: list[str]) -> str:
    body = '\n'.join(f'- {line}' for line in lines)
    return f'{title}：\n{body}'
