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
    outgoing_count = {}
    incoming_count = {}
    next_by_source = {}
    if not edges:
        return [item['id'] for item in sorted(segments, key=lambda item: item.get('order_index', 0))]
    for edge in edges:
        source = edge.get('source_segment_id')
        target = edge.get('target_segment_id')
        if source not in ids or target not in ids:
            raise ValueError('连线引用了不存在的语句节点')
        if source == target:
            raise ValueError('语句节点不能连接到自身')
        outgoing_count[source] = outgoing_count.get(source, 0) + 1
        incoming_count[target] = incoming_count.get(target, 0) + 1
        next_by_source[source] = target
        if outgoing_count[source] > 1:
            raise ValueError('每个语句节点最多只能连接一个后继')
        if incoming_count[target] > 1:
            raise ValueError('每个语句节点最多只能连接一个前驱')

    heads = [item_id for item_id in ids if incoming_count.get(item_id, 0) == 0]
    if not heads:
        raise ValueError('语句连线不能形成环路')
    if len(edges) != max(0, len(ids) - 1):
        raise ValueError('语句节点必须连接成一条完整链路')
    if len(heads) != 1:
        raise ValueError('语句节点必须连接成一条完整链路')

    path = []
    current = heads[0]
    visited = set()
    while current is not None:
        if current in visited:
            raise ValueError('语句连线不能形成环路')
        visited.add(current)
        path.append(current)
        current = next_by_source.get(current)

    if visited != ids:
        raise ValueError('语句节点必须连接成一条完整链路')
    return path


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


def _update_segment_from_payload(segment: VoiceWorkflowSegment, payload: dict, index: int):
    """Update an existing segment's fields from payload (preserves ID)."""
    segment.order_index = _clamp_int(payload.get('order_index'), 1, 100000, index + 1)
    segment.text = (payload.get('text') or '').strip()
    segment.node_x = _clamp_float(payload.get('node_x'), -100000, 100000, 80 + index * 240)
    segment.node_y = _clamp_float(payload.get('node_y'), -100000, 100000, 120)
    segment.emotion = payload.get('emotion') or 'neutral'
    segment.intensity = _clamp_float(payload.get('intensity'), 0.0, 2.0, 0.5)
    segment.rate = _clamp_float(payload.get('rate'), 0.5, 2.0, 1.0)
    segment.pitch = _clamp_float(payload.get('pitch'), -12.0, 12.0, 0.0)
    segment.volume_db = _clamp_float(payload.get('volume_db'), -12.0, 12.0, 0.0)
    segment.pause_before_ms = _clamp_int(payload.get('pause_before_ms'), 0, 10000, 0)
    segment.pause_after_ms = _clamp_int(payload.get('pause_after_ms'), 0, 10000, 250)
    segment.transition = payload.get('transition') or 'normal'
    segment.delivery_instruction = payload.get('delivery_instruction') or ''
    segment.voice_profile_id = payload.get('voice_profile_id')
    # Preserve audio_status and fingerprint if client sends them
    if payload.get('audio_status'):
        segment.audio_status = payload['audio_status']
    if payload.get('audio_fingerprint'):
        segment.audio_fingerprint = payload['audio_fingerprint']


def save_workflow_snapshot(workflow_id: int, payload: dict) -> dict:
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    workflow_data = payload.get('workflow') or {}
    workflow.title = workflow_data.get('title') or workflow.title
    workflow.source_content = workflow_data.get('source_content', workflow.source_content)
    workflow.source_text_id = workflow_data.get('source_text_id', workflow.source_text_id)
    workflow.default_voice_profile_id = workflow_data.get('default_voice_profile_id', workflow.default_voice_profile_id)
    workflow.settings = workflow_data.get('settings', workflow.settings)

    # Upsert segments: update existing by ID, create new for tmp-* IDs
    existing_by_id = {s.id: s for s in workflow.segments}
    payload_segments = payload.get('segments') or []
    seen_ids = set()
    created_segments = []

    for index, segment_payload in enumerate(payload_segments):
        raw_id = segment_payload.get('id')
        # Check if this is an existing DB segment (integer ID that exists)
        if isinstance(raw_id, int) and raw_id in existing_by_id:
            segment = existing_by_id[raw_id]
            _update_segment_from_payload(segment, segment_payload, index)
            seen_ids.add(raw_id)
        else:
            # New segment (tmp-* string ID or missing ID)
            segment = _segment_from_payload(workflow.id, segment_payload, index)
            if not segment.text:
                raise ValueError('语句文本不能为空')
            db.session.add(segment)
        created_segments.append(segment)

    # Delete segments not in payload (edges first for FK)
    segments_to_delete = [s for s in workflow.segments if s.id not in seen_ids]
    if segments_to_delete:
        # Delete edges referencing segments being deleted
        delete_seg_ids = {s.id for s in segments_to_delete}
        for edge in list(workflow.edges):
            if edge.source_segment_id in delete_seg_ids or edge.target_segment_id in delete_seg_ids:
                db.session.delete(edge)
        for segment in segments_to_delete:
            db.session.delete(segment)

    db.session.flush()

    # Rebuild all edges
    for edge in list(workflow.edges):
        db.session.delete(edge)
    db.session.flush()

    edge_payloads = []
    for edge_payload in payload.get('edges') or []:
        source_client_id = edge_payload.get('source_client_id')
        target_client_id = edge_payload.get('target_client_id')
        source = (
            created_segments[source_client_id]
            if isinstance(source_client_id, int) and 0 <= source_client_id < len(created_segments)
            else None
        )
        target = (
            created_segments[target_client_id]
            if isinstance(target_client_id, int) and 0 <= target_client_id < len(created_segments)
            else None
        )
        if not source or not target:
            raise ValueError('连线引用了不存在的语句节点')
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


def resolve_linear_path(workflow: VoiceWorkflow) -> list[VoiceWorkflowSegment]:
    """Traverse edges to get the true playback order. Falls back to order_index if no edges."""
    segments = VoiceWorkflowSegment.query.filter_by(workflow_id=workflow.id).order_by(
        VoiceWorkflowSegment.order_index,
    ).all()
    if not segments:
        return []
    edges = VoiceWorkflowEdge.query.filter_by(workflow_id=workflow.id).order_by(
        VoiceWorkflowEdge.order_index,
    ).all()
    if not edges:
        return sorted(segments, key=lambda s: s.order_index)

    seg_by_id = {s.id: s for s in segments}
    path_ids = validate_linear_edges(
        [segment.to_dict() for segment in segments],
        [edge.to_dict() for edge in edges],
    )
    return [seg_by_id[segment_id] for segment_id in path_ids]


def ordered_segments(workflow: VoiceWorkflow) -> list[VoiceWorkflowSegment]:
    return resolve_linear_path(workflow)


def _segment_manifest_entry(segment: dict) -> dict:
    return {
        **segment,
        'generation_params': {
            'emotion': segment.get('emotion'),
            'intensity': segment.get('intensity'),
            'rate': segment.get('rate'),
            'pitch': segment.get('pitch'),
            'volume_db': segment.get('volume_db'),
            'pause_before_ms': segment.get('pause_before_ms'),
            'pause_after_ms': segment.get('pause_after_ms'),
            'transition': segment.get('transition'),
            'voice_profile_id': segment.get('voice_profile_id'),
            'model': segment.get('model'),
        },
    }


def build_workflow_manifest(workflow: VoiceWorkflow, segments: list[dict], timeline: list[dict]) -> dict:
    return {
        'title': workflow.title,
        'source': 'voice_workflow',
        'workflow_id': workflow.id,
        'segments': [_segment_manifest_entry(s) for s in segments],
        'edges': [edge.to_dict() for edge in workflow.edges],
        'subtitles': timeline,
        'total_duration': round(timeline[-1]['end'], 3) if timeline else 0,
    }
