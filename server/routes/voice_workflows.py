from flask import Blueprint, jsonify, request

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment
from server.services.emotion_planner import plan_workflow_segments
from server.services.voice_workflow_service import save_workflow_snapshot

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
