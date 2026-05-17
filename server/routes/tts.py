import io
import json
import re
import zipfile
import base64
import wave
from urllib.parse import quote

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


def _safe_filename(name):
    filename = re.sub(r'[\\/:*?"<>|]+', '_', (name or '').strip())
    return filename or '语音合成'


def _read_wav_info(audio_bytes):
    with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
        return {
            'channels': wav.getnchannels(),
            'sample_width': wav.getsampwidth(),
            'framerate': wav.getframerate(),
            'frames': wav.getnframes(),
            'params': wav.getparams(),
            'frame_bytes': wav.readframes(wav.getnframes()),
        }


def _duration_from_info(info):
    return info['frames'] / info['framerate']


def _format_srt_timestamp(seconds):
    total_millis = round(seconds * 1000)
    hours = total_millis // 3600000
    minutes = (total_millis % 3600000) // 60000
    secs = (total_millis % 60000) // 1000
    millis = total_millis % 1000
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def _build_timed_srt(items):
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_timestamp(item['start'])} --> {_format_srt_timestamp(item['end'])}")
        lines.append(item['text'].replace('\n', ' '))
        lines.append('')
    return '\n'.join(lines)


def _concat_wavs(wav_infos, gap):
    if not wav_infos:
        return b''

    base = wav_infos[0]
    for info in wav_infos[1:]:
        if (
            info['channels'] != base['channels']
            or info['sample_width'] != base['sample_width']
            or info['framerate'] != base['framerate']
        ):
            raise ValueError('音频参数不一致，无法拼接完整音频')

    silence_frames = round(gap * base['framerate'])
    silence = b'\x00' * silence_frames * base['channels'] * base['sample_width']
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(base['channels'])
        wav.setsampwidth(base['sample_width'])
        wav.setframerate(base['framerate'])
        for index, info in enumerate(wav_infos):
            if index:
                wav.writeframes(silence)
            wav.writeframes(info['frame_bytes'])
    return output.getvalue()


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


@tts_bp.route('/api/tts/sync-package', methods=['POST'])
def sync_package():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    api_key = data.get('api_key')
    title = _safe_filename(data.get('title'))
    default_voice = data.get('default_voice_description', '')
    segments = data.get('segments', [])
    gap = float(data.get('gap', 0.3))

    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if gap < 0:
        return jsonify({'error': '静音间隔不能小于 0'}), 400
    if not segments:
        return jsonify({'error': '没有需要合成的片段'}), 400

    segment_files = []
    wav_infos = []
    timeline = []
    current_time = 0.0

    for i, seg in enumerate(segments):
        text = (seg.get('text') or '').strip()
        voice = (seg.get('voice_description') or default_voice).strip()
        if not text or not voice:
            return jsonify({'error': f'片段 {i + 1}: 缺少文本或音色描述'}), 400

        try:
            audio_b64 = _call_tts(api_key, voice, text)
            audio_bytes = base64.b64decode(audio_b64)
            wav_info = _read_wav_info(audio_bytes)
        except requests.RequestException as e:
            return jsonify({'error': f'片段 {i + 1}: 请求 MiMo API 失败: {e}'}), 502
        except (ValueError, wave.Error, KeyError):
            return jsonify({'error': f'片段 {i + 1}: 音频数据异常'}), 502

        duration = _duration_from_info(wav_info)
        start = current_time
        end = start + duration
        filename = f'segments/{i + 1:03d}.wav'

        segment_files.append((filename, audio_bytes))
        wav_infos.append(wav_info)
        timeline.append({
            'index': i + 1,
            'text': text,
            'filename': filename,
            'start': round(start, 3),
            'end': round(end, 3),
            'duration': round(duration, 3),
        })
        current_time = end + gap

    try:
        full_audio = _concat_wavs(wav_infos, gap)
    except ValueError as e:
        return jsonify({'error': str(e)}), 502

    total_duration = 0 if not timeline else timeline[-1]['end']
    srt_content = _build_timed_srt(timeline)
    manifest = {
        'title': title,
        'gap': gap,
        'total_duration': round(total_duration, 3),
        'segments': timeline,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{title}_完整音频.wav', full_audio)
        zf.writestr(f'{title}_同步字幕.srt', srt_content)
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for filename, audio_bytes in segment_files:
            zf.writestr(filename, audio_bytes)

    buf.seek(0)
    download_name = f'{title}_同步包.zip'
    encoded_filename = quote(download_name)
    response = send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name,
    )
    response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
    return response


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
