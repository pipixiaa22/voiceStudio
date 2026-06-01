from flask import Blueprint, request, jsonify
from server.services import voice_profile_repository as repo
from server.services.tts_provider import TTSProvider
from server.services.voice_prompt import build_audition_text, build_voice_prompt
from server.services.voice_profile_normalizer import normalize_voice_profile_payload

voice_profiles_bp = Blueprint('voice_profiles', __name__)


@voice_profiles_bp.route('/api/voice-profiles', methods=['GET'])
def list_profiles():
    """查询音色档案列表。"""
    active = request.args.get('active')
    builtin = request.args.get('builtin')
    scene = request.args.get('scene')
    q = request.args.get('q')

    kwargs = {}
    if active is not None:
        kwargs['active'] = active == '1'
    if builtin is not None:
        kwargs['builtin'] = builtin == '1'
    if scene:
        kwargs['scene'] = scene
    if q:
        kwargs['q'] = q

    profiles = repo.query_profiles(**kwargs)
    return jsonify(profiles)


@voice_profiles_bp.route('/api/voice-profiles/<int:profile_id>', methods=['GET'])
def get_profile(profile_id):
    """获取单个音色档案。"""
    profile = repo.get_profile_by_id(profile_id)
    if not profile:
        return jsonify({'error': '音色档案不存在'}), 404
    return jsonify(profile)


@voice_profiles_bp.route('/api/voice-profiles', methods=['POST'])
def create_profile():
    """创建自定义音色。"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    if not data.get('name'):
        return jsonify({'error': '请填写音色名称'}), 400

    data, error = normalize_voice_profile_payload(data)
    if error:
        return jsonify({'error': error}), 400

    error = _validate_and_normalize_voice_source(data)
    if error:
        return jsonify({'error': error}), 400

    try:
        profile = repo.create_profile(data)
        return jsonify(profile), 201
    except Exception as e:
        return jsonify({'error': f'创建失败: {str(e)}'}), 500


@voice_profiles_bp.route('/api/voice-profiles/<int:profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """更新自定义音色。"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    try:
        profile = repo.update_profile(profile_id, data)
        if not profile:
            return jsonify({'error': '音色档案不存在'}), 404
        return jsonify(profile)
    except ValueError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500


@voice_profiles_bp.route('/api/voice-profiles/<int:profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    """删除自定义音色（逻辑删除）。"""
    try:
        success = repo.deactivate_profile(profile_id)
        if not success:
            return jsonify({'error': '音色档案不存在'}), 404
        return '', 204
    except ValueError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@voice_profiles_bp.route('/api/voice-profiles/<int:profile_id>/audition', methods=['POST'])
def audition_profile(profile_id):
    """生成试听音频。"""
    profile = repo.get_profile_by_id(profile_id)
    if not profile:
        return jsonify({'error': '音色档案不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    api_key = data.get('api_key')
    audition_text = build_audition_text(profile, data.get('text') or '')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not audition_text:
        return jsonify({'error': '请填写试听文本'}), 400

    # 创建试听记录
    audition = repo.create_audition(profile_id, audition_text)

    try:
        provider = TTSProvider(api_key)
        audio_b64 = provider.synthesize(
            voice_description=build_voice_prompt(profile),
            text=audition_text,
            style_tags=profile.get('style_tags'),
            model=profile.get('model') or 'mimo-v2.5-tts-voicedesign',
            voice=_audio_voice_from_profile(profile),
            optimize_text_preview=True,
        )

        # 更新试听记录
        repo.update_audition(audition['id'], status='completed')

        return jsonify({
            'audio_base64': audio_b64,
            'audition_id': audition['id'],
        })
    except Exception as e:
        # 更新试听记录为失败
        repo.update_audition(audition['id'], status='failed', error_message=str(e))
        return jsonify({'error': f'试听生成失败: {str(e)}'}), 502


def _validate_and_normalize_voice_source(data):
    source_type = data.get('source_type') or 'voice_design'
    data['source_type'] = source_type

    if source_type == 'voice_clone':
        if not data.get('consent_confirmed'):
            return '请确认样音已获得授权后再创建音色复刻档案'
        sample = data.get('voice_sample_data_uri') or ''
        if not _is_supported_voice_sample(sample):
            return '请上传 mp3 或 wav 格式的授权样音'
        if _base64_payload_too_large(sample):
            return '样音 Base64 编码不能超过 10MB'
        data['model'] = 'mimo-v2.5-tts-voiceclone'
        return None

    if source_type == 'builtin':
        if not data.get('builtin_voice'):
            return '请选择预置音色'
        data['model'] = 'mimo-v2.5-tts'
        return None

    data['model'] = data.get('model') or 'mimo-v2.5-tts-voicedesign'
    return None


def _is_supported_voice_sample(data_uri):
    return (
        data_uri.startswith('data:audio/wav;base64,')
        or data_uri.startswith('data:audio/mp3;base64,')
        or data_uri.startswith('data:audio/mpeg;base64,')
    )


def _base64_payload_too_large(data_uri):
    if ',' not in data_uri:
        return True
    return len(data_uri.split(',', 1)[1]) > 10 * 1024 * 1024


def _audio_voice_from_profile(profile):
    if (
        profile.get('source_type') == 'voice_clone'
        or profile.get('model') == 'mimo-v2.5-tts-voiceclone'
        or profile.get('voice_sample_data_uri')
    ):
        return profile.get('voice_sample_data_uri')
    return profile.get('builtin_voice')
