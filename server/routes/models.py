from flask import Blueprint, request, jsonify
from server.services.model_registry import ModelRegistry

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
    return jsonify(registry.get_all_models())


@models_bp.route('/api/model-providers/test', methods=['POST'])
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
