import base64
from flask import Blueprint, request, jsonify
from server.services import voice_profile_repository as repo
from server.services.tts_provider import TTSProvider

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

    if not data.get('raw_description'):
        return jsonify({'error': '请填写音色描述'}), 400

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
    audition_text = data.get('text', '')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not audition_text:
        return jsonify({'error': '请填写试听文本'}), 400

    # 创建试听记录
    audition = repo.create_audition(profile_id, audition_text)

    try:
        # 使用 canonical_prompt 作为音色描述
        provider = TTSProvider(api_key)
        audio_b64 = provider.synthesize(profile['canonical_prompt'], audition_text)

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
