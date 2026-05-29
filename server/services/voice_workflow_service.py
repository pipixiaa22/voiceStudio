import hashlib
import json

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment


def _clamp_float(value, minimum, maximum, default):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_int(value, minimum, maximum, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def validate_linear_edges(segments, edges) -> list[int]:
    ids = {item['id'] for item in segments if item.get('id') is not None}
    outgoing = {}
    incoming = {}
    for edge in edges:
        source = edge.get('source_segment_id')
        target = edge.get('target_segment_id')
        if source not in ids or target not in ids:
            raise ValueError('连线引用了不存在的语句节点')
        outgoing[source] = outgoing.get(source, 0) + 1
        incoming[target] = incoming.get(target, 0) + 1
        if outgoing[source] > 1:
            raise ValueError('每个语句节点最多只能连接一个后继')
        if incoming[target] > 1:
            raise ValueError('每个语句节点最多只能连接一个前驱')
    return [item['id'] for item in sorted(segments, key=lambda item: item.get('order_index', 0))]


def build_audio_fingerprint(segment: dict) -> str:
    payload = {
        'text': segment.get('text', ''),
        'emotion': segment.get('emotion', 'neutral'),
        'intensity': segment.get('intensity', 0.5),
        'rate': segment.get('rate', 1.0),
        'pitch': segment.get('pitch', 0),
        'volume_db': segment.get('volume_db', 0),
        'pause_before_ms': segment.get('pause_before_ms', 0),
        'pause_after_ms': segment.get('pause_after_ms', 250),
        'transition': segment.get('transition', 'normal'),
        'delivery_instruction': segment.get('delivery_instruction', ''),
        'voice_profile_id': segment.get('voice_profile_id'),
        'model': segment.get('model', 'mimo-v2.5-tts-voicedesign'),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    return f'sha256:{digest}'


def _segment_from_payload(workflow_id: int, payload: dict, index: int) -> VoiceWorkflowSegment:
    return VoiceWorkflowSegment(
        workflow_id=workflow_id,
        order_index=_clamp_int(payload.get('order_index'), 1, 100000, index + 1),
        text=(payload.get('text') or '').strip(),
        node_x=_clamp_float(payload.get('node_x'), -100000, 100000, 80 + index * 240),
        node_y=_clamp_float(payload.get('node_y'), -100000, 100000, 120),
        emotion=payload.get('emotion') or 'neutral',
        intensity=_clamp_float(payload.get('intensity'), 0.0, 2.0, 0.5),
        rate=_clamp_float(payload.get('rate'), 0.5, 2.0, 1.0),
        pitch=_clamp_float(payload.get('pitch'), -12.0, 12.0, 0.0),
        volume_db=_clamp_float(payload.get('volume_db'), -12.0, 12.0, 0.0),
        pause_before_ms=_clamp_int(payload.get('pause_before_ms'), 0, 10000, 0),
        pause_after_ms=_clamp_int(payload.get('pause_after_ms'), 0, 10000, 250),
        transition=payload.get('transition') or 'normal',
        delivery_instruction=payload.get('delivery_instruction') or '',
        voice_profile_id=payload.get('voice_profile_id'),
        audio_status=payload.get('audio_status') or 'missing',
        audio_fingerprint=payload.get('audio_fingerprint'),
    )


def save_workflow_snapshot(workflow_id: int, payload: dict) -> dict:
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    workflow_data = payload.get('workflow') or {}
    workflow.title = workflow_data.get('title') or workflow.title
    workflow.source_content = workflow_data.get('source_content', workflow.source_content)
    workflow.source_text_id = workflow_data.get('source_text_id', workflow.source_text_id)
    workflow.default_voice_profile_id = workflow_data.get('default_voice_profile_id', workflow.default_voice_profile_id)
    workflow.settings = workflow_data.get('settings', workflow.settings)

    for segment in list(workflow.segments):
        db.session.delete(segment)
    for edge in list(workflow.edges):
        db.session.delete(edge)
    db.session.flush()

    created_segments = []
    for index, segment_payload in enumerate(payload.get('segments') or []):
        segment = _segment_from_payload(workflow.id, segment_payload, index)
        if not segment.text:
            raise ValueError('语句文本不能为空')
        db.session.add(segment)
        created_segments.append(segment)
    db.session.flush()

    edge_payloads = []
    for edge_payload in payload.get('edges') or []:
        source_client_id = edge_payload.get('source_client_id')
        target_client_id = edge_payload.get('target_client_id')
        source = created_segments[source_client_id] if isinstance(source_client_id, int) else None
        target = created_segments[target_client_id] if isinstance(target_client_id, int) else None
        if not source or not target:
            continue
        edge_payloads.append({
            'source_segment_id': source.id,
            'target_segment_id': target.id,
            'order_index': edge_payload.get('order_index', len(edge_payloads) + 1),
        })

    validate_linear_edges([segment.to_dict() for segment in created_segments], edge_payloads)
    for edge_payload in edge_payloads:
        db.session.add(VoiceWorkflowEdge(workflow_id=workflow.id, **edge_payload))

    db.session.commit()
    return workflow.to_dict(include_children=True)


def ordered_segments(workflow: VoiceWorkflow) -> list[VoiceWorkflowSegment]:
    return sorted(workflow.segments, key=lambda segment: segment.order_index)


def build_workflow_manifest(workflow: VoiceWorkflow, segments: list[dict], timeline: list[dict]) -> dict:
    return {
        'title': workflow.title,
        'source': 'voice_workflow',
        'workflow_id': workflow.id,
        'segments': segments,
        'edges': [edge.to_dict() for edge in workflow.edges],
        'subtitles': timeline,
        'total_duration': round(timeline[-1]['end'], 3) if timeline else 0,
    }
