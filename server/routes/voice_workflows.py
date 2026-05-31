import base64
import io
import os
from urllib.parse import quote

from flask import Blueprint, jsonify, request, send_file

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment
from server.services import voice_workflow_audio
from server.services.audio_package import build_srt, build_zip_package, read_wav_info
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline
from server.services.emotion_planner import plan_workflow_segments
from server.services.jianying_draft import inject_subtitles_into_draft
from server.services.voice_workflow_service import build_workflow_manifest, ordered_segments, save_workflow_snapshot

CACHE_DIR = voice_workflow_audio.CACHE_DIR
repo = voice_workflow_audio.repo

voice_workflows_bp = Blueprint('voice_workflows', __name__)


def _sync_audio_cache_dir():
    voice_workflow_audio.CACHE_DIR = CACHE_DIR


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


def _subtitle_max_chars(workflow, data):
    return voice_workflow_audio.subtitle_max_chars_for_workflow(workflow, data)


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


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/duplicate', methods=['POST'])
def duplicate_voice_workflow(workflow_id):
    source = VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    duplicate = VoiceWorkflow(
        title=data.get('title') or f'{source.title} 副本',
        source_text_id=source.source_text_id,
        source_content=source.source_content,
        default_voice_profile_id=source.default_voice_profile_id,
    )
    duplicate.settings = source.settings
    db.session.add(duplicate)
    db.session.flush()

    segment_id_map = {}
    for source_segment in source.segments:
        copied = VoiceWorkflowSegment(
            workflow_id=duplicate.id,
            order_index=source_segment.order_index,
            text=source_segment.text,
            node_x=source_segment.node_x,
            node_y=source_segment.node_y,
            emotion=source_segment.emotion,
            intensity=source_segment.intensity,
            rate=source_segment.rate,
            pitch=source_segment.pitch,
            volume_db=source_segment.volume_db,
            pause_before_ms=source_segment.pause_before_ms,
            pause_after_ms=source_segment.pause_after_ms,
            transition=source_segment.transition,
            delivery_instruction=source_segment.delivery_instruction,
            voice_profile_id=source_segment.voice_profile_id,
            audio_status='missing',
            audio_path=None,
            audio_fingerprint=None,
        )
        db.session.add(copied)
        db.session.flush()
        segment_id_map[source_segment.id] = copied.id

    for source_edge in source.edges:
        source_id = segment_id_map.get(source_edge.source_segment_id)
        target_id = segment_id_map.get(source_edge.target_segment_id)
        if source_id and target_id:
            db.session.add(VoiceWorkflowEdge(
                workflow_id=duplicate.id,
                source_segment_id=source_id,
                target_segment_id=target_id,
                order_index=source_edge.order_index,
            ))

    db.session.commit()
    return jsonify(duplicate.to_dict(include_children=True)), 201


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/plan', methods=['POST'])
def plan_voice_workflow_segments_endpoint(workflow_id):
    VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    content = data.get('content') or ''
    max_chars = _parse_int_option(data.get('max_chars', 80), 1, 500, 80)
    if max_chars is None:
        return jsonify({'error': 'max_chars 必须是 1 到 500 之间的整数'}), 400
    return jsonify({'segments': plan_workflow_segments(content, max_chars=max_chars)})


def _segment_failure_response(segment, exc):
    return jsonify({
        'error': f"第 {segment.order_index} 句语音生成失败: {exc}",
        'segment_id': segment.id,
        'order_index': segment.order_index,
        'message': str(exc),
    }), 502


def _build_preflight(workflow):
    _sync_audio_cache_dir()
    try:
        segments = ordered_segments(workflow)
    except ValueError as exc:
        return {
            'ok': False,
            'segment_count': len(workflow.segments),
            'ready_count': 0,
            'missing_count': len(workflow.segments),
            'issues': [{'code': 'invalid_path', 'message': str(exc)}],
            'warnings': [],
            'segments': [],
        }

    issues = []
    warnings = []
    segment_statuses = []
    for segment in segments:
        status = voice_workflow_audio.cache_status_for_segment(workflow, segment)
        segment_statuses.append(status)
        if not segment.text.strip():
            issues.append({
                'code': 'empty_text',
                'message': f'第 {segment.order_index} 句文本为空',
                'segment_id': segment.id,
                'order_index': segment.order_index,
            })
        if not status['ready']:
            issues.append({
                'code': 'missing_audio',
                'message': f'第 {segment.order_index} 句音频未生成或缓存已失效',
                'segment_id': segment.id,
                'order_index': segment.order_index,
            })

    if not segments:
        issues.append({'code': 'empty_workflow', 'message': '当前配音工程没有可导出的语句'})
    if not workflow.default_voice_profile_id:
        warnings.append({'code': 'missing_default_voice', 'message': '工程未设置默认音色，将使用兜底声音描述'})

    ready_count = sum(1 for item in segment_statuses if item['ready'])
    return {
        'ok': not issues,
        'segment_count': len(segments),
        'ready_count': ready_count,
        'missing_count': len(segments) - ready_count,
        'issues': issues,
        'warnings': warnings,
        'segments': segment_statuses,
    }


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/preflight', methods=['GET'])
def preflight_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    return jsonify(_build_preflight(workflow))


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/regenerate-missing', methods=['POST'])
def regenerate_missing_voice_workflow_segments(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    _sync_audio_cache_dir()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    try:
        segments = ordered_segments(workflow)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    generated = []
    failures = []
    for segment in segments:
        status = voice_workflow_audio.cache_status_for_segment(workflow, segment)
        if status['ready']:
            continue
        try:
            result = voice_workflow_audio.synthesize_or_cache_segment(workflow, segment, api_key, data, reuse_cache=False)
            generated.append({
                'segment_id': segment.id,
                'order_index': segment.order_index,
                'fingerprint': result['fingerprint'],
                'duration': round(result['duration'], 3),
            })
        except Exception as exc:
            segment.audio_status = 'failed'
            segment.audio_fingerprint = None
            segment.audio_path = None
            failures.append({
                'segment_id': segment.id,
                'order_index': segment.order_index,
                'message': str(exc),
            })

    db.session.commit()
    payload = {
        'generated_count': len(generated),
        'failed_count': len(failures),
        'generated': generated,
        'failures': failures,
        'segments': [segment.to_dict() for segment in ordered_segments(workflow)],
        'preflight': _build_preflight(workflow),
    }
    return jsonify(payload), 207 if failures else 200


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/<int:segment_id>/audition', methods=['POST'])
def audition_voice_workflow_segment(workflow_id, segment_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    _sync_audio_cache_dir()
    segment = VoiceWorkflowSegment.query.filter_by(id=segment_id, workflow_id=workflow.id).first_or_404()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    try:
        result = voice_workflow_audio.synthesize_or_cache_segment(workflow, segment, api_key, data, reuse_cache=False)
    except Exception as exc:
        db.session.rollback()
        return _segment_failure_response(segment, exc)
    db.session.commit()
    return jsonify({
        'audio_base64': result['audio_base64'],
        'duration': round(result['duration'], 3),
        'fingerprint': result['fingerprint'],
    })


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/audition-path', methods=['POST'])
def audition_voice_workflow_path(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    _sync_audio_cache_dir()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    try:
        segments = ordered_segments(workflow)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    audio_items = []
    durations = []
    for segment in segments:
        try:
            result = voice_workflow_audio.synthesize_or_cache_segment(workflow, segment, api_key, data)
        except Exception as exc:
            db.session.rollback()
            return _segment_failure_response(segment, exc)
        audio_items.append({'wav_info': result['wav_info'], 'segment': segment.to_dict()})
        durations.append(result['duration'])

    db.session.commit()
    try:
        full_audio = concat_emotional_wavs(audio_items)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    audio_base64 = base64.b64encode(full_audio).decode('ascii')
    try:
        subtitle_max_chars = _subtitle_max_chars(workflow, data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    timeline = build_emotional_subtitle_timeline(
        [segment.to_dict() for segment in segments], durations,
        subtitle_max_chars=subtitle_max_chars,
    )
    full_info = read_wav_info(full_audio)
    return jsonify({
        'audio_base64': audio_base64,
        'total_duration': round(full_info['frames'] / full_info['framerate'], 3),
        'segment_count': len(durations),
        'timeline': timeline,
    })


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/export', methods=['POST'])
def export_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    _sync_audio_cache_dir()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    chunk_files = []
    audio_items = []
    manifest_segments = []
    durations = []
    export_options = data.get('export_options') or {}
    include_segment_wavs = export_options.get('include_segment_wavs', True) is not False
    reuse_cache = export_options.get('reuse_cache', True) is not False

    try:
        segments = ordered_segments(workflow)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    for index, segment in enumerate(segments, 1):
        try:
            result = voice_workflow_audio.synthesize_or_cache_segment(
                workflow,
                segment,
                api_key,
                data,
                reuse_cache=reuse_cache,
            )
        except Exception as exc:
            db.session.rollback()
            return _segment_failure_response(segment, exc)

        filename = f'segments/{index:03d}.wav'
        if include_segment_wavs:
            chunk_files.append((filename, result['audio_bytes']))
        audio_items.append({'wav_info': result['wav_info'], 'segment': result['segment_dict']})
        durations.append(result['duration'])
        manifest_segments.append({
            **result['segment_dict'],
            'filename': filename if include_segment_wavs else None,
            'duration': round(result['duration'], 3),
            'cached': result['cached'],
        })

    db.session.commit()

    try:
        full_audio = concat_emotional_wavs(audio_items)
        subtitle_max_chars = _subtitle_max_chars(workflow, data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    timeline = build_emotional_subtitle_timeline(
        [segment.to_dict() for segment in segments], durations,
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


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/export-to-jianying', methods=['POST'])
def export_voice_workflow_to_jianying(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    _sync_audio_cache_dir()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    draft_dir = data.get('draft_dir')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    if not draft_dir:
        return jsonify({'error': '请填写剪映工程目录'}), 400

    try:
        segments = ordered_segments(workflow)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if not segments:
        return jsonify({'error': '当前配音工程没有可导出的语句'}), 400

    durations = []
    for segment in segments:
        try:
            result = voice_workflow_audio.synthesize_or_cache_segment(workflow, segment, api_key, data)
        except Exception as exc:
            db.session.rollback()
            return _segment_failure_response(segment, exc)
        durations.append(result['duration'])

    db.session.commit()

    subtitle_max_chars = (workflow.settings or {}).get('subtitle_max_chars', 20)
    timeline = build_emotional_subtitle_timeline(
        [segment.to_dict() for segment in segments],
        durations,
        subtitle_max_chars=subtitle_max_chars,
    )
    try:
        result = inject_subtitles_into_draft(
            draft_dir,
            timeline,
            track_name=f'墨影字幕-{workflow.id}',
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(result)


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
