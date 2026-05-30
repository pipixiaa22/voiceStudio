from server.services.emotion_planner import build_segment_delivery_instruction


def test_intensity_high_in_output():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 1.8, 'rate': 1.0, 'pitch': 0,
        'volume_db': 0, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '极致' in instruction or '爆发边缘' in instruction


def test_intensity_low_in_output():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.2, 'rate': 1.0, 'pitch': 0,
        'volume_db': 0, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '克制' in instruction or '内敛' in instruction


def test_pitch_low_in_output():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.5, 'rate': 1.0, 'pitch': -5,
        'volume_db': 0, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '压低' in instruction or '胸声' in instruction


def test_pitch_high_in_output():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.5, 'rate': 1.0, 'pitch': 5,
        'volume_db': 0, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '抬高' in instruction or '明亮' in instruction


def test_transition_suppressed_burst():
    instruction = build_segment_delivery_instruction({
        'emotion': 'angry_burst', 'intensity': 1.6, 'rate': 1.15, 'pitch': 2,
        'volume_db': 3, 'transition': 'suppressed_burst', 'delivery_instruction': '',
    })
    assert '压抑' in instruction and '爆发' in instruction


def test_transition_cold_shift():
    instruction = build_segment_delivery_instruction({
        'emotion': 'cold', 'intensity': 0.7, 'rate': 0.8, 'pitch': -2,
        'volume_db': -2, 'transition': 'cold_shift', 'delivery_instruction': '',
    })
    assert '冷' in instruction


def test_transition_soften():
    instruction = build_segment_delivery_instruction({
        'emotion': 'calm', 'intensity': 0.3, 'rate': 0.95, 'pitch': -1,
        'volume_db': -1, 'transition': 'soften', 'delivery_instruction': '',
    })
    assert '软化' in instruction or '温柔' in instruction


def test_transition_whisper_in():
    instruction = build_segment_delivery_instruction({
        'emotion': 'whisper', 'intensity': 0.4, 'rate': 0.85, 'pitch': -2,
        'volume_db': -4, 'transition': 'whisper_in', 'delivery_instruction': '',
    })
    assert '耳语' in instruction or '轻' in instruction


def test_rate_very_fast():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.5, 'rate': 1.3, 'pitch': 0,
        'volume_db': 0, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '很快' in instruction or '急切' in instruction


def test_rate_very_slow():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.5, 'rate': 0.7, 'pitch': 0,
        'volume_db': 0, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '明显放慢' in instruction or '停顿感' in instruction


def test_custom_delivery_instruction_included():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.5, 'rate': 1.0, 'pitch': 0,
        'volume_db': 0, 'transition': 'normal',
        'delivery_instruction': '像在对晚辈说话，温和但有威严',
    })
    assert '对晚辈说话' in instruction


def test_volume_very_low():
    instruction = build_segment_delivery_instruction({
        'emotion': 'neutral', 'intensity': 0.5, 'rate': 1.0, 'pitch': 0,
        'volume_db': -6, 'transition': 'normal', 'delivery_instruction': '',
    })
    assert '耳语' in instruction or '自言自语' in instruction
