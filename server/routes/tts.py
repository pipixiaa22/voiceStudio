import io
import zipfile

import requests
from flask import Blueprint, request, jsonify, send_file

tts_bp = Blueprint('tts', __name__)

MIMO_TTS_URL = 'https://api.xiaomimimo.com/v1/chat/completions'
MIMO_LLM_URL = 'https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages'


def _call_tts(api_key, voice_description, text):
    """Call MiMo TTS API. Returns base64 audio data or raises with error message."""
    payload = {
        'model': 'mimo-v2.5-tts-voicedesign',
        'messages': [
            {'role': 'user', 'content': voice_description},
            {'role': 'assistant', 'content': text},
        ],
        'audio': {'format': 'wav'},
    }
    resp = requests.post(
        MIMO_TTS_URL,
        headers={'api-key': api_key, 'Content-Type': 'application/json'},
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise ValueError(f'MiMo API 返回错误: {resp.status_code}')
    result = resp.json()
    return result['choices'][0]['message']['audio']['data']


@tts_bp.route('/api/tts/synthesize', methods=['POST'])
def synthesize():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    api_key = data.get('api_key')
    voice_description = data.get('voice_description')
    text = data.get('text')

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not voice_description:
        return jsonify({'error': '请填写音色描述'}), 400
    if not text:
        return jsonify({'error': '请填写合成文本'}), 400

    try:
        audio_data = _call_tts(api_key, voice_description, text)
    except requests.RequestException as e:
        return jsonify({'error': f'请求 MiMo API 失败: {e}'}), 502
    except ValueError as e:
        return jsonify({'error': str(e)}), 502

    return jsonify({'audio_base64': audio_data})


@tts_bp.route('/api/tts/batch-synthesize', methods=['POST'])
def batch_synthesize():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    api_key = data.get('api_key')
    default_voice = data.get('default_voice_description', '')
    segments = data.get('segments', [])

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not segments:
        return jsonify({'error': '没有需要合成的片段'}), 400

    buf = io.BytesIO()
    errors = []

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, seg in enumerate(segments):
            text = seg.get('text', '')
            voice = seg.get('voice_description') or default_voice
            if not text or not voice:
                errors.append(f'片段 {i + 1}: 缺少文本或音色描述')
                continue
            try:
                import base64
                audio_b64 = _call_tts(api_key, voice, text)
                audio_bytes = base64.b64decode(audio_b64)
                zf.writestr(f'{i + 1:03d}.wav', audio_bytes)
            except requests.RequestException:
                errors.append(f'片段 {i + 1}: 网络错误')
            except ValueError:
                errors.append(f'片段 {i + 1}: API 返回异常')

    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name='语音合成.zip',
    )


@tts_bp.route('/api/tts/polish', methods=['POST'])
def polish():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    api_key = data.get('api_key')
    voice_description = data.get('voice_description')
    system_prompt = data.get('system_prompt')

    if not api_key:
        return jsonify({'error': '请填写文本润色 API Key'}), 400
    if not voice_description:
        return jsonify({'error': '请填写音色描述'}), 400

    payload = {
        'model': 'mimo-v2.5-pro',
        'max_tokens': 1024,
        'system': system_prompt or '你是一个专业的语音合成音色描述润色专家。',
        'messages': [
            {'role': 'user', 'content': [{'type': 'text', 'text': voice_description}]},
        ],
    }

    try:
        resp = requests.post(
            MIMO_LLM_URL,
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException as e:
        return jsonify({'error': f'请求 MiMo API 失败: {e}'}), 502

    if resp.status_code != 200:
        return jsonify({'error': f'MiMo API 返回错误: {resp.status_code}', 'detail': resp.text}), resp.status_code

    try:
        result = resp.json()
        polished = result['content'][0]['text']
    except (KeyError, IndexError, ValueError):
        return jsonify({'error': 'MiMo API 返回数据格式异常'}), 502

    return jsonify({'polished': polished})
