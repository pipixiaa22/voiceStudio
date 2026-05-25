import uuid
from server.services.mysql import get_cursor


def _generate_profile_key(name: str) -> str:
    """生成唯一的 profile_key。"""
    base = name.strip().lower().replace(' ', '_')
    # 移除非字母数字和下划线
    base = ''.join(c for c in base if c.isalnum() or c == '_')
    if not base:
        base = 'voice'
    suffix = uuid.uuid4().hex[:8]
    return f"{base}_{suffix}"


def query_profiles(
    active: bool | None = None,
    builtin: bool | None = None,
    scene: str | None = None,
    q: str | None = None,
) -> list[dict]:
    """查询音色档案列表。"""
    conditions = []
    params = []

    if active is not None:
        conditions.append("is_active = %s")
        params.append(int(active))
    if builtin is not None:
        conditions.append("is_builtin = %s")
        params.append(int(builtin))
    if scene:
        conditions.append("scene = %s")
        params.append(scene)
    if q:
        conditions.append("(name LIKE %s OR description LIKE %s OR raw_description LIKE %s)")
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q])

    where = " AND ".join(conditions) if conditions else "1=1"
    sql = f"""
        SELECT id, profile_key, name, description, raw_description, canonical_prompt,
               negative_prompt, provider, model, language, gender, age_group, accent,
               speed, emotion, scene, timbre, source_type, builtin_voice, style_tags,
               audition_text, voice_sample_data_uri, voice_sample_mime,
               voice_sample_filename, consent_confirmed, is_builtin, is_active, sort_order,
               created_at, updated_at
        FROM voice_profiles
        WHERE {where}
        ORDER BY is_builtin DESC, sort_order ASC, created_at DESC
    """

    with get_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def get_profile_by_id(profile_id: int) -> dict | None:
    """根据 ID 获取音色档案。"""
    sql = """
        SELECT id, profile_key, name, description, raw_description, canonical_prompt,
               negative_prompt, provider, model, language, gender, age_group, accent,
               speed, emotion, scene, timbre, source_type, builtin_voice, style_tags,
               audition_text, voice_sample_data_uri, voice_sample_mime,
               voice_sample_filename, consent_confirmed, is_builtin, is_active, sort_order,
               created_at, updated_at
        FROM voice_profiles
        WHERE id = %s
    """
    with get_cursor() as cursor:
        cursor.execute(sql, (profile_id,))
        return cursor.fetchone()


def create_profile(data: dict) -> dict:
    """创建自定义音色档案。"""
    profile_key = _generate_profile_key(data['name'])

    sql = """
        INSERT INTO voice_profiles (
            profile_key, name, description, raw_description, canonical_prompt,
            negative_prompt, provider, model, language, gender, age_group, accent,
            speed, emotion, scene, timbre, source_type, builtin_voice, style_tags,
            audition_text, voice_sample_data_uri, voice_sample_mime,
            voice_sample_filename, consent_confirmed, is_builtin, is_active, sort_order
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, 0, 1, 100
        )
    """
    params = (
        profile_key,
        data['name'],
        data.get('description', ''),
        data['raw_description'],
        data.get('canonical_prompt', data['raw_description']),  # 默认使用 raw_description
        data.get('negative_prompt', ''),
        data.get('provider', 'mimo'),
        data.get('model', 'mimo-v2.5-tts-voicedesign'),
        data.get('language', 'zh-CN'),
        data.get('gender'),
        data.get('age_group'),
        data.get('accent'),
        data.get('speed'),
        data.get('emotion'),
        data.get('scene'),
        data.get('timbre'),
        data.get('source_type', 'voice_design'),
        data.get('builtin_voice'),
        data.get('style_tags'),
        data.get('audition_text'),
        data.get('voice_sample_data_uri'),
        data.get('voice_sample_mime'),
        data.get('voice_sample_filename'),
        int(bool(data.get('consent_confirmed'))),
    )

    with get_cursor() as cursor:
        cursor.execute(sql, params)
        profile_id = cursor.lastrowid

    return get_profile_by_id(profile_id)


def update_profile(profile_id: int, data: dict) -> dict | None:
    """更新自定义音色档案。"""
    # 检查是否是系统预设
    profile = get_profile_by_id(profile_id)
    if not profile:
        return None
    if profile['is_builtin']:
        raise ValueError('系统预设不能编辑')

    fields = []
    params = []

    updatable_fields = [
        'name', 'description', 'raw_description', 'canonical_prompt',
        'negative_prompt', 'gender', 'age_group', 'accent', 'speed',
        'emotion', 'scene', 'timbre', 'source_type', 'builtin_voice',
        'style_tags', 'audition_text', 'voice_sample_data_uri',
        'voice_sample_mime', 'voice_sample_filename', 'consent_confirmed'
    ]

    for field in updatable_fields:
        if field in data:
            fields.append(f"{field} = %s")
            params.append(data[field])

    if not fields:
        return profile

    params.append(profile_id)
    sql = f"UPDATE voice_profiles SET {', '.join(fields)} WHERE id = %s"

    with get_cursor() as cursor:
        cursor.execute(sql, params)

    return get_profile_by_id(profile_id)


def deactivate_profile(profile_id: int) -> bool:
    """逻辑删除自定义音色档案。"""
    profile = get_profile_by_id(profile_id)
    if not profile:
        return False
    if profile['is_builtin']:
        raise ValueError('系统预设不能删除')

    sql = "UPDATE voice_profiles SET is_active = 0 WHERE id = %s"
    with get_cursor() as cursor:
        cursor.execute(sql, (profile_id,))
    return True


def create_audition(profile_id: int, audition_text: str) -> dict:
    """创建试听记录。"""
    sql = """
        INSERT INTO voice_profile_auditions (voice_profile_id, audition_text, status)
        VALUES (%s, %s, 'created')
    """
    with get_cursor() as cursor:
        cursor.execute(sql, (profile_id, audition_text))
        audition_id = cursor.lastrowid

    return {'id': audition_id, 'voice_profile_id': profile_id, 'audition_text': audition_text, 'status': 'created'}


def update_audition(audition_id: int, audio_url: str | None = None, status: str = 'completed', error_message: str | None = None):
    """更新试听记录。"""
    sql = "UPDATE voice_profile_auditions SET audio_url = %s, status = %s, error_message = %s WHERE id = %s"
    with get_cursor() as cursor:
        cursor.execute(sql, (audio_url, status, error_message, audition_id))
