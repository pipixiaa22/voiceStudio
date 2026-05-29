from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment


def test_voice_workflow_to_dict_includes_segments_and_edges(app):
    workflow = VoiceWorkflow(title='试音工程', source_content='我知道了。')
    db.session.add(workflow)
    db.session.flush()
    first = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=1,
        text='我知道了。',
        node_x=80,
        node_y=120,
        emotion='calm',
        intensity=0.3,
        rate=0.95,
        pitch=-1,
        volume_db=0,
        pause_before_ms=0,
        pause_after_ms=250,
        transition='normal',
        audio_status='missing',
    )
    second = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=2,
        text='可是你为什么现在才告诉我！',
        node_x=320,
        node_y=180,
        emotion='angry_burst',
        intensity=1.6,
        rate=1.15,
        pitch=2,
        volume_db=3,
        pause_before_ms=80,
        pause_after_ms=180,
        transition='burst',
        audio_status='missing',
    )
    db.session.add_all([first, second])
    db.session.flush()
    db.session.add(VoiceWorkflowEdge(
        workflow_id=workflow.id,
        source_segment_id=first.id,
        target_segment_id=second.id,
        order_index=1,
    ))
    db.session.commit()

    data = workflow.to_dict(include_children=True)

    assert data['title'] == '试音工程'
    assert data['source_content'] == '我知道了。'
    assert [item['text'] for item in data['segments']] == [
        '我知道了。',
        '可是你为什么现在才告诉我！',
    ]
    assert data['segments'][1]['emotion'] == 'angry_burst'
    assert data['edges'][0]['source_segment_id'] == first.id
    assert data['edges'][0]['target_segment_id'] == second.id


import pytest

from server.models.voice_workflow import VoiceWorkflow
from server.services.voice_workflow_service import (
    build_audio_fingerprint,
    save_workflow_snapshot,
    validate_linear_edges,
)


def test_validate_linear_edges_rejects_branching():
    segments = [{'id': 1}, {'id': 2}, {'id': 3}]
    edges = [
        {'source_segment_id': 1, 'target_segment_id': 2},
        {'source_segment_id': 1, 'target_segment_id': 3},
    ]

    with pytest.raises(ValueError, match='最多只能连接一个后继'):
        validate_linear_edges(segments, edges)


def test_save_workflow_snapshot_replaces_segments_and_edges(app):
    workflow = VoiceWorkflow(title='旧工程', source_content='旧内容')
    db.session.add(workflow)
    db.session.commit()

    data = save_workflow_snapshot(workflow.id, {
        'workflow': {
            'title': '新工程',
            'source_content': '我知道了。可是你为什么现在才告诉我！',
            'settings': {'subtitle_max_chars': 20},
        },
        'segments': [
            {'order_index': 1, 'text': '我知道了。', 'emotion': 'calm', 'node_x': 80, 'node_y': 120},
            {'order_index': 2, 'text': '可是你为什么现在才告诉我！', 'emotion': 'angry_burst', 'node_x': 320, 'node_y': 180},
        ],
        'edges': [
            {'source_client_id': 0, 'target_client_id': 1, 'order_index': 1},
        ],
    })

    assert data['title'] == '新工程'
    assert len(data['segments']) == 2
    assert len(data['edges']) == 1
    assert data['segments'][1]['audio_status'] == 'missing'


def test_audio_fingerprint_changes_when_parameters_change():
    first = build_audio_fingerprint({
        'text': '我知道了。',
        'emotion': 'calm',
        'intensity': 0.3,
        'rate': 0.95,
        'volume_db': 0,
        'voice_profile_id': 9,
        'model': 'mimo-v2.5-tts-voicedesign',
    })
    second = build_audio_fingerprint({
        'text': '我知道了。',
        'emotion': 'angry_burst',
        'intensity': 1.6,
        'rate': 1.15,
        'volume_db': 3,
        'voice_profile_id': 9,
        'model': 'mimo-v2.5-tts-voicedesign',
    })

    assert first.startswith('sha256:')
    assert first != second
