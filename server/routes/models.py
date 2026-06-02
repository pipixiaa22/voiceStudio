import json
import uuid
from flask import Blueprint, request, jsonify
from server.services.model_registry import ModelRegistry
from server.models import db, CustomProvider
from server.services.redis_client import rate_limit

models_bp = Blueprint('models', __name__)
registry = ModelRegistry()


@models_bp.route('/api/model-providers/presets', methods=['GET'])
def get_presets():
    presets = registry.get_presets()
    return jsonify([
        {
            'provider_key': p.provider_key,
            'display_name': p.display_name,
            'provider_type': p.provider_type,
            'base_url': p.base_url,
            'capabilities': p.capabilities,
            'models': [
                {
                    'model_key': m.model_key,
                    'display_name': m.display_name,
                    'capabilities': m.capabilities,
                }
                for m in p.models
            ],
        }
        for p in presets
    ])


@models_bp.route('/api/models', methods=['GET'])
def get_all_models():
    result = registry.get_all_models()
    for cp in CustomProvider.query.all():
        for m in (cp.models_json and json.loads(cp.models_json) or []):
            result.append({
                'provider_key': cp.provider_key,
                'provider_name': cp.display_name,
                'model_key': m['model_key'],
                'model_name': m.get('display_name', m['model_key']),
                'capabilities': m.get('capabilities', []),
                'is_custom': True,
            })
    return jsonify(result)


@models_bp.route('/api/model-providers/test', methods=['POST'])
@rate_limit('provider-test', 10, 60)
def test_connection():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    provider_key = data.get('provider_key', '')
    provider_type = data.get('provider_type', '')
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    capability = data.get('capability', '')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    try:
        provider = registry.create_provider(
            provider_key or provider_type,
            api_key=api_key,
            base_url=base_url,
            provider_type=provider_type,
        )
        result = provider.test_connection(model=model, capability=capability)
        return jsonify({
            'ok': result.ok,
            'latency_ms': result.latency_ms,
            'message': result.message,
        })
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500


@models_bp.route('/api/models/llm/complete', methods=['POST'])
@rate_limit('llm', 10, 60)
def llm_complete():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    provider_key = data.get('provider_key', '')
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    messages = data.get('messages', [])
    system_prompt = data.get('system_prompt', '')
    max_tokens = data.get('max_tokens', 1024)

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not messages:
        return jsonify({'error': '请提供消息'}), 400

    try:
        provider = registry.create_provider(
            provider_key, api_key=api_key, base_url=base_url,
        )
        result = provider.complete(
            messages, model,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )
        return jsonify({'text': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@models_bp.route('/api/models/tts/synthesize', methods=['POST'])
@rate_limit('tts', 20, 60)
def tts_synthesize():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    provider_key = data.get('provider_key', '')
    api_key = data.get('api_key', '')
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    text = data.get('text', '')
    voice_description = data.get('voice_description', '')
    voice = data.get('voice', '')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not text:
        return jsonify({'error': '请提供文本'}), 400

    try:
        import base64
        provider = registry.create_provider(
            provider_key, api_key=api_key, base_url=base_url,
        )
        audio_bytes = provider.synthesize(
            text, model,
            voice_description=voice_description,
            voice=voice,
        )
        return jsonify({'audio_base64': base64.b64encode(audio_bytes).decode()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@models_bp.route('/api/model-providers/custom', methods=['GET'])
def list_custom_providers():
    providers = CustomProvider.query.order_by(CustomProvider.created_at.desc()).all()
    return jsonify([p.to_dict() for p in providers])


@models_bp.route('/api/model-providers/custom', methods=['POST'])
def create_custom_provider():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    display_name = data.get('display_name', '').strip()
    base_url = data.get('base_url', '').strip()
    models = data.get('models', [])

    if not display_name:
        return jsonify({'error': '请输入供应商名称'}), 400
    if not base_url:
        return jsonify({'error': '请输入 Base URL'}), 400
    if not models:
        return jsonify({'error': '请至少添加一个模型'}), 400

    provider_key = f'custom_{uuid.uuid4().hex[:8]}'
    cp = CustomProvider(
        provider_key=provider_key,
        display_name=display_name,
        base_url=base_url,
        models_json=json.dumps(models, ensure_ascii=False),
    )
    db.session.add(cp)
    db.session.commit()
    return jsonify(cp.to_dict()), 201


@models_bp.route('/api/model-providers/custom/<int:cp_id>', methods=['PUT'])
def update_custom_provider(cp_id):
    cp = CustomProvider.query.get_or_404(cp_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    if 'display_name' in data:
        cp.display_name = data['display_name'].strip()
    if 'base_url' in data:
        cp.base_url = data['base_url'].strip()
    if 'models' in data:
        cp.models_json = json.dumps(data['models'], ensure_ascii=False)

    db.session.commit()
    return jsonify(cp.to_dict())


@models_bp.route('/api/model-providers/custom/<int:cp_id>', methods=['DELETE'])
def delete_custom_provider(cp_id):
    cp = CustomProvider.query.get_or_404(cp_id)
    db.session.delete(cp)
    db.session.commit()
    return jsonify({'ok': True})
