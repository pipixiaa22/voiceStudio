from server.services.emotion_planner import (
    build_segment_delivery_instruction,
    plan_workflow_segments,
)


def test_plan_workflow_segments_detects_burst_from_punctuation():
    segments = plan_workflow_segments('我知道了。可是你为什么现在才告诉我！', max_chars=80)

    assert [segment['text'] for segment in segments] == [
        '我知道了。',
        '可是你为什么现在才告诉我！',
    ]
    assert segments[0]['emotion'] == 'calm'
    assert segments[1]['emotion'] == 'angry_burst'
    assert segments[1]['pause_before_ms'] == 80


def test_delivery_instruction_mentions_same_speaker_and_emotion():
    instruction = build_segment_delivery_instruction({
        'emotion': 'angry_burst',
        'intensity': 1.6,
        'rate': 1.15,
        'pitch': 2,
        'volume_db': 3,
        'transition': 'burst',
        'delivery_instruction': '',
    })

    assert '同一个说话人音色' in instruction
    assert '突然爆发' in instruction
    assert '语速加快' in instruction
    assert '不要像换了一个人' in instruction
