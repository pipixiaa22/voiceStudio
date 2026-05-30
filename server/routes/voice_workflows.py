import base64
import io
import os
from urllib.parse import quote

from flask import Blueprint, jsonify, request, send_file

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment
from server.services import voice_profile_repository as repo
from server.services.audio_package import build_srt, build_zip_package, read_wav_info
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline
from server.services.emotional_tts import synthesize_emotion_segment
from server.services.emotion_planner import plan_workflow_segments
from server.services.voice_workflow_service import build_audio_fingerprint, build_workflow_manifest, ordered_segments, save_workflow_snapshot

CACHE_DIR = 'outputs/voice_workflow_cache'

voice_workflows_bp = Blueprint('voice_workflows', __name__)


def _create_edges_for_segments(workflow_id, segments):
    edges = []
    for index in range(len(segments) - 1):
        edge = VoiceWorkflowEdge(
            workflow_id=workflow_id,
            source_segment_id=segments[index].id,
            target_segment_id=segments[index + 1].id,
            order_index=index + 1,
        )
        db.session.add(edge)
        edges.append(edge)
    return edges


@voice_workflows_bp.route('/api/voice-workflows', methods=['GET'])
def list_voice_workflows():
    workflows = VoiceWorkflow.query.order_by(VoiceWorkflow.updated_at.desc()).all()
    return jsonify([workflow.to_dict(include_children=False) for workflow in workflows])


@voice_workflows_bp.route('/api/voice-workflows', methods=['POST'])
def create_voice_workflow():
    data = request.get_json() or {}
    workflow = VoiceWorkflow(
        title=data.get('title') or '未命名配音工程',
        source_text_id=data.get('source_text_id'),
        source_content=data.get('source_content') or '',
        default_voice_profile_id=data.get('default_voice_profile_id'),
    )
    workflow.settings = data.get('settings') or {'subtitle_max_chars': 20, 'segment_max_chars': 80}
    db.session.add(workflow)
    db.session.flush()

    created_segments = []
    for segment_data in plan_workflow_segments(workflow.source_content, max_chars=workflow.settings.get('segment_max_chars', 80)):
        segment = VoiceWorkflowSegment(workflow_id=workflow.id, **segment_data)
        db.session.add(segment)
        created_segments.append(segment)
    db.session.flush()
    _create_edges_for_segments(workflow.id, created_segments)
    db.session.commit()
    return jsonify(workflow.to_dict(include_children=True)), 201


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>', methods=['GET'])
def get_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    return jsonify(workflow.to_dict(include_children=True))


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>', methods=['PUT'])
def update_voice_workflow(workflow_id):
    data = request.get_json() or {}
    try:
        result = save_workflow_snapshot(workflow_id, data)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400
    return jsonify(result)


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>', methods=['DELETE'])
def delete_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    db.session.delete(workflow)
    db.session.commit()
    return '', 204


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/plan', methods=['POST'])
def plan_voice_workflow_segments_endpoint(workflow_id):
    VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    content = data.get('content') or ''
    max_chars = int(data.get('max_chars', 80))
    return jsonify({'segments': plan_workflow_segments(content, max_chars=max_chars)})


def _profile_audio_voice(profile):
    if not profile:
        return None
    if profile.get('source_type') == 'voice_clone':
        return profile.get('voice_sample_data_uri')
    return profile.get('builtin_voice')


def _cache_path_for_fingerprint(workflow_id, fingerprint):
    """Use fingerprint-based path so cache survives segment ID changes."""
    safe_name = fingerprint.replace('sha256:', '')[:16]
    return os.path.join(CACHE_DIR, str(workflow_id), f'{safe_name}.wav')


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/<int:segment_id>/audition', methods=['POST'])
def audition_voice_workflow_segment(workflow_id, segment_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    segment = VoiceWorkflowSegment.query.filter_by(id=segment_id, workflow_id=workflow.id).first_or_404()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
    profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
    model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    result = synthesize_emotion_segment(
        api_key,
        segment.to_dict(),
        voice_profile=profile,
        fallback_voice_description=data.get('voice_description', ''),
        style_tags=(profile or {}).get('style_tags'),
        model=model,
        voice=_profile_audio_voice(profile),
    )
    # Write to cache and update segment
    cache_path = _cache_path_for_fingerprint(workflow_id, result['fingerprint'])
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'wb') as f:
        f.write(result['audio_bytes'])
    segment.audio_path = cache_path
    segment.audio_fingerprint = result['fingerprint']
    segment.audio_status = 'ready'
    db.session.commit()
    return jsonify({
        'audio_base64': result['audio_base64'],
        'duration': round(result['duration'], 3),
        'fingerprint': result['fingerprint'],
    })


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/audition-path', methods=['POST'])
def audition_voice_workflow_path(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    audio_items = []
    durations = []
    for segment in ordered_segments(workflow):
        profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
        profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
        model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
        result = synthesize_emotion_segment(
            api_key,
            segment.to_dict(),
            voice_profile=profile,
            fallback_voice_description=data.get('voice_description', ''),
            style_tags=(profile or {}).get('style_tags'),
            model=model,
            voice=_profile_audio_voice(profile),
        )
        audio_items.append({'wav_info': result['wav_info'], 'segment': segment.to_dict()})
        durations.append(result['duration'])

    full_audio = concat_emotional_wavs(audio_items)
    audio_base64 = base64.b64encode(full_audio).decode('ascii')
    subtitle_max_chars = (workflow.settings or {}).get('subtitle_max_chars', 20)
    timeline = build_emotional_subtitle_timeline(
        [segment.to_dict() for segment in ordered_segments(workflow)], durations,
        subtitle_max_chars=subtitle_max_chars,
    )
    return jsonify({
        'audio_base64': audio_base64,
        'total_duration': round(sum(durations), 3),
        'segment_count': len(durations),
        'timeline': timeline,
    })


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/export', methods=['POST'])
def export_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    chunk_files = []
    audio_items = []
    manifest_segments = []
    durations = []

    for index, segment in enumerate(ordered_segments(workflow), 1):
        profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
        profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
        model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
        segment_dict = segment.to_dict()
        expected_fingerprint = build_audio_fingerprint({**segment_dict, 'model': model})

        cache_path = _cache_path_for_fingerprint(workflow_id, expected_fingerprint)
        is_cached = (
            segment.audio_status == 'ready'
            and segment.audio_fingerprint == expected_fingerprint
            and os.path.exists(cache_path)
        )

        if is_cached:
            audio_bytes = open(cache_path, 'rb').read()
            info = read_wav_info(audio_bytes)
            duration = info['frames'] / info['framerate']
        else:
            result = synthesize_emotion_segment(
                api_key,
                segment_dict,
                voice_profile=profile,
                fallback_voice_description=data.get('voice_description', ''),
                style_tags=(profile or {}).get('style_tags'),
                model=model,
                voice=_profile_audio_voice(profile),
            )
            audio_bytes = result['audio_bytes']
            info = result['wav_info']
            duration = result['duration']
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'wb') as f:
                f.write(audio_bytes)
            segment.audio_path = cache_path
            segment.audio_fingerprint = expected_fingerprint
            segment.audio_status = 'ready'

        filename = f'segments/{index:03d}.wav'
        chunk_files.append((filename, audio_bytes))
        audio_items.append({'wav_info': info, 'segment': segment_dict})
        durations.append(duration)
        manifest_segments.append({**segment_dict, 'filename': filename, 'duration': round(duration, 3)})

    db.session.commit()

    full_audio = concat_emotional_wavs(audio_items)
    subtitle_max_chars = (workflow.settings or {}).get('subtitle_max_chars', 20)
    timeline = build_emotional_subtitle_timeline(
        [segment.to_dict() for segment in ordered_segments(workflow)], durations,
        subtitle_max_chars=subtitle_max_chars,
    )
    srt_content = build_srt(timeline)
    manifest = build_workflow_manifest(workflow, manifest_segments, timeline)
    zip_bytes = build_zip_package(workflow.title, full_audio, srt_content, manifest, chunk_files)
    download_name = f'{workflow.title}_配音工作流.zip'
    response = send_file(
        io.BytesIO(zip_bytes),
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name,
    )
    response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(download_name)}"
    return response


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/cache', methods=['DELETE'])
def clear_voice_workflow_cache(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    import shutil
    cache_dir = os.path.join(CACHE_DIR, str(workflow_id))
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    for segment in workflow.segments:
        segment.audio_status = 'missing'
        segment.audio_fingerprint = None
        segment.audio_path = None
    db.session.commit()
    return '', 204
