from server.services.tts_planner import plan_speech_chunks, SpeechChunk


def test_plan_single_chunk():
    segments = ['你好', '世界']
    chunks = plan_speech_chunks(segments, max_chars=200)
    assert len(chunks) == 1
    assert chunks[0].text == '你好世界'
    assert chunks[0].subtitle_indices == [0, 1]


def test_plan_multiple_chunks():
    segments = ['A' * 100, 'B' * 100, 'C' * 100]
    chunks = plan_speech_chunks(segments, max_chars=150)
    assert len(chunks) == 2
    assert chunks[0].subtitle_indices == [0]
    assert chunks[1].subtitle_indices == [1, 2]


def test_plan_empty_segments():
    chunks = plan_speech_chunks([], max_chars=200)
    assert chunks == []


def test_plan_preserves_order():
    segments = ['第一段', '第二段', '第三段']
    chunks = plan_speech_chunks(segments, max_chars=200)
    assert chunks[0].text == '第一段第二段第三段'
