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
