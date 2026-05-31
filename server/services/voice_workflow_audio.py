import base64
from pathlib import Path

from server.models import db
from server.models.voice_workflow import VoiceWorkflow
from server.services import voice_profile_repository as repo
from server.services.audio_package import read_wav_info
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline
from server.services.emotional_tts import synthesize_emotion_segment
from server.services.voice_workflow_service import build_audio_fingerprint, build_workflow_manifest, ordered_segments

CACHE_DIR = 'outputs/voice_workflow_cache'


def _parse_int_option(value, minimum, maximum, default=None):
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < minimum or parsed > maximum:
        return None
    return parsed


def subtitle_max_chars_for_workflow(workflow, data):
    requested = ((data.get('subtitle_options') or {}).get('max_chars'))
    parsed = _parse_int_option(requested, 1, 200, None)
    if requested is not None and parsed is None:
        raise ValueError('subtitle_options.max_chars 必须是 1 到 200 之间的整数')
    return parsed or (workflow.settings or {}).get('subtitle_max_chars', 20)


def profile_audio_voice(profile):
    if not profile:
        return None
    if profile.get('source_type') == 'voice_clone':
        return profile.get('voice_sample_data_uri')
    return profile.get('builtin_voice')


def cache_path_for_fingerprint(workflow_id, fingerprint):
    """Use fingerprint-based path so cache survives segment ID changes."""
    safe_name = fingerprint.replace('sha256:', '')[:16]
    return Path(CACHE_DIR) / str(workflow_id) / f'{safe_name}.wav'


def synthesize_or_cache_segment(
    workflow,
    segment,
    api_key,
    data,
    *,
    reuse_cache=True,
    persist_cache=True,
):
    profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
    profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
    model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    segment_dict = segment.to_dict()
    expected_fingerprint = build_audio_fingerprint({**segment_dict, 'model': model})
    cache_path = cache_path_for_fingerprint(workflow.id, expected_fingerprint)
    is_cached = (
        reuse_cache
        and segment.audio_status == 'ready'
        and segment.audio_fingerprint == expected_fingerprint
        and cache_path.exists()
    )

    if is_cached:
        audio_bytes = cache_path.read_bytes()
        info = read_wav_info(audio_bytes)
        duration = info['frames'] / info['framerate']
        return {
            'audio_base64': base64.b64encode(audio_bytes).decode('ascii'),
            'audio_bytes': audio_bytes,
            'wav_info': info,
            'duration': duration,
            'fingerprint': expected_fingerprint,
            'cached': True,
            'segment_dict': segment_dict,
        }

    result = synthesize_emotion_segment(
        api_key,
        segment_dict,
        voice_profile=profile,
        fallback_voice_description=data.get('voice_description', ''),
        style_tags=(profile or {}).get('style_tags'),
        model=model,
        voice=profile_audio_voice(profile),
    )
    audio_bytes = result['audio_bytes']
    info = result['wav_info']
    duration = result['duration']

    if persist_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(audio_bytes)
        segment.audio_path = str(cache_path)
        segment.audio_fingerprint = expected_fingerprint
        segment.audio_status = 'ready'

    return {
        'audio_base64': result['audio_base64'],
        'audio_bytes': audio_bytes,
        'wav_info': info,
        'duration': duration,
        'fingerprint': expected_fingerprint,
        'cached': False,
        'segment_dict': segment_dict,
    }


def cache_status_for_segment(workflow, segment):
    profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
    profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
    model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    segment_dict = segment.to_dict()
    expected_fingerprint = build_audio_fingerprint({**segment_dict, 'model': model})
    cache_path = cache_path_for_fingerprint(workflow.id, expected_fingerprint)
    ready = (
        segment.audio_status == 'ready'
        and segment.audio_fingerprint == expected_fingerprint
        and cache_path.exists()
    )
    return {
        'segment_id': segment.id,
        'order_index': segment.order_index,
        'text': segment.text,
        'status': 'ready' if ready else (segment.audio_status or 'missing'),
        'ready': ready,
        'expected_fingerprint': expected_fingerprint,
        'cached_path': str(cache_path) if ready else None,
    }


def build_voice_track_from_workflow(workflow_id: int, request_data: dict) -> dict:
    data = request_data or {}
    workflow = db.session.get(VoiceWorkflow, workflow_id)
    if not workflow:
        raise ValueError('配音工程不存在')

    api_key = data.get('api_key')
    if not api_key:
        raise ValueError('请填写 API Key')

    try:
        segments = ordered_segments(workflow)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if not segments:
        raise ValueError('当前配音工程没有可导出的语句')

    audio_items = []
    durations = []
    voice_chunks = []
    for segment in segments:
        try:
            result = synthesize_or_cache_segment(workflow, segment, api_key, data)
        except Exception as exc:
            segment.audio_status = 'failed'
            segment.audio_fingerprint = None
            segment.audio_path = None
            raise ValueError(f"第 {segment.order_index} 句语音生成失败: {exc}") from exc

        audio_items.append({'wav_info': result['wav_info'], 'segment': result['segment_dict']})
        durations.append(result['duration'])
        voice_chunks.append({
            **result['segment_dict'],
            'duration': round(result['duration'], 3),
            'cached': result['cached'],
            'fingerprint': result['fingerprint'],
        })

    db.session.commit()

    try:
        voice_audio = concat_emotional_wavs(audio_items)
        subtitle_max_chars = subtitle_max_chars_for_workflow(workflow, data)
        subtitle_timeline = build_emotional_subtitle_timeline(
            [segment.to_dict() for segment in segments],
            durations,
            subtitle_max_chars=subtitle_max_chars,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    if not subtitle_timeline:
        raise ValueError('未生成字幕时间轴')

    manifest = build_workflow_manifest(workflow, voice_chunks, subtitle_timeline)
    full_info = read_wav_info(voice_audio)
    return {
        'source': 'voice_workflow',
        'workflow_id': workflow.id,
        'voice_audio': voice_audio,
        'subtitle_timeline': subtitle_timeline,
        'manifest': manifest,
        'voice_chunks': voice_chunks,
        'duration': full_info['frames'] / full_info['framerate'],
    }
