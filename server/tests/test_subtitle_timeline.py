from server.services.subtitle_timeline import build_subtitle_timeline
from server.services.tts_planner import SpeechChunk


def test_single_subtitle_per_chunk():
    chunks = [SpeechChunk(index=1, text='你好世界', subtitle_indices=[0])]
    durations = [2.0]
    timeline = build_subtitle_timeline(chunks, durations, gap=0.0)
    assert len(timeline) == 1
    assert timeline[0]['start'] == 0.0
    assert timeline[0]['end'] == 2.0
    assert timeline[0]['text'] == '你好世界'


def test_multiple_subtitles_per_chunk():
    chunks = [SpeechChunk(index=1, text='你好世界', subtitle_indices=[0, 1])]
    subtitle_segments = ['你好', '世界']
    durations = [2.0]
    timeline = build_subtitle_timeline(chunks, durations, gap=0.0, subtitle_segments=subtitle_segments)
    assert len(timeline) == 2
    assert timeline[0]['text'] == '你好'
    assert timeline[1]['text'] == '世界'
    assert timeline[0]['start'] == 0.0
    assert timeline[1]['end'] == 2.0


def test_gap_between_chunks():
    chunks = [
        SpeechChunk(index=1, text='第一段', subtitle_indices=[0]),
        SpeechChunk(index=2, text='第二段', subtitle_indices=[1]),
    ]
    durations = [2.0, 3.0]
    timeline = build_subtitle_timeline(chunks, durations, gap=0.5)
    assert timeline[0]['start'] == 0.0
    assert timeline[0]['end'] == 2.0
    assert timeline[1]['start'] == 2.5
    assert timeline[1]['end'] == 5.5
