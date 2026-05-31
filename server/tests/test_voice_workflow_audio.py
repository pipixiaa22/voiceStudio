import io
import wave

import pytest

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment


def _wav_bytes(duration_seconds=0.1, framerate=8000):
    output = io.BytesIO()
    frames = b'\x00\x00' * int(duration_seconds * framerate)
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(frames)
    return output.getvalue()


def _workflow_with_segments():
    workflow = VoiceWorkflow(title='配音工程', source_content='第一句。第二句。')
    workflow.settings = {'subtitle_max_chars': 20}
    db.session.add(workflow)
    db.session.flush()
    first = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=1,
        text='第一句。',
        emotion='calm',
        pause_before_ms=0,
        pause_after_ms=100,
    )
    second = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=2,
        text='第二句。',
        emotion='tense',
        pause_before_ms=50,
        pause_after_ms=0,
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
    return workflow


def test_synthesize_or_cache_segment_reuses_ready_cache(app, tmp_path, monkeypatch):
    from server.services import voice_workflow_audio
    from server.services.voice_workflow_service import build_audio_fingerprint

    monkeypatch.setattr(voice_workflow_audio, 'CACHE_DIR', str(tmp_path))
    workflow = _workflow_with_segments()
    segment = workflow.segments[0]
    expected = build_audio_fingerprint({**segment.to_dict(), 'model': 'mimo-v2.5-tts-voicedesign'})
    cache_path = voice_workflow_audio.cache_path_for_fingerprint(workflow.id, expected)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    audio = _wav_bytes()
    cache_path.write_bytes(audio)
    segment.audio_status = 'ready'
    segment.audio_fingerprint = expected
    db.session.commit()

    def fail_synthesize(*args, **kwargs):
        raise AssertionError('cache hit should not synthesize')

    monkeypatch.setattr(voice_workflow_audio, 'synthesize_emotion_segment', fail_synthesize)

    result = voice_workflow_audio.synthesize_or_cache_segment(workflow, segment, 'key', {}, reuse_cache=True)

    assert result['cached'] is True
    assert result['audio_bytes'] == audio
    assert result['duration'] > 0


def test_build_voice_track_from_workflow_returns_manifest_and_timeline(app, tmp_path, monkeypatch):
    from server.services import voice_workflow_audio

    monkeypatch.setattr(voice_workflow_audio, 'CACHE_DIR', str(tmp_path))
    workflow = _workflow_with_segments()
    audio = _wav_bytes()

    def fake_synthesize(workflow, segment, api_key, data, reuse_cache=True, persist_cache=True):
        return {
            'audio_base64': '',
            'audio_bytes': audio,
            'wav_info': voice_workflow_audio.read_wav_info(audio),
            'duration': 0.1,
            'fingerprint': f'f-{segment.id}',
            'cached': False,
            'segment_dict': segment.to_dict(),
        }

    monkeypatch.setattr(voice_workflow_audio, 'synthesize_or_cache_segment', fake_synthesize)

    result = voice_workflow_audio.build_voice_track_from_workflow(
        workflow.id,
        {'api_key': 'key', 'subtitle_options': {'max_chars': 20}},
    )

    assert result['source'] == 'voice_workflow'
    assert result['workflow_id'] == workflow.id
    assert result['voice_audio']
    assert result['subtitle_timeline'][0]['text'] == '第一句'
    assert result['manifest']['source'] == 'voice_workflow'
    assert result['manifest']['workflow_id'] == workflow.id
    assert [item['text'] for item in result['voice_chunks']] == ['第一句。', '第二句。']


def test_build_voice_track_from_workflow_rolls_back_partial_state_on_failure(app, tmp_path, monkeypatch):
    from server.services import voice_workflow_audio

    monkeypatch.setattr(voice_workflow_audio, 'CACHE_DIR', str(tmp_path))
    workflow = _workflow_with_segments()
    first_id = workflow.segments[0].id
    second_id = workflow.segments[1].id
    audio = _wav_bytes()

    def fake_synthesize(workflow, segment, api_key, data, reuse_cache=True, persist_cache=True):
        if segment.order_index == 2:
            raise RuntimeError('provider timeout')
        segment.audio_status = 'ready'
        segment.audio_fingerprint = 'partial-fingerprint'
        segment.audio_path = 'partial.wav'
        return {
            'audio_base64': '',
            'audio_bytes': audio,
            'wav_info': voice_workflow_audio.read_wav_info(audio),
            'duration': 0.1,
            'fingerprint': 'partial-fingerprint',
            'cached': False,
            'segment_dict': segment.to_dict(),
        }

    monkeypatch.setattr(voice_workflow_audio, 'synthesize_or_cache_segment', fake_synthesize)

    with pytest.raises(ValueError, match='第 2 句语音生成失败'):
        voice_workflow_audio.build_voice_track_from_workflow(workflow.id, {'api_key': 'key'})

    first = db.session.get(VoiceWorkflowSegment, first_id)
    second = db.session.get(VoiceWorkflowSegment, second_id)
    assert first.audio_status == 'missing'
    assert first.audio_fingerprint is None
    assert first.audio_path is None
    assert second.audio_status == 'missing'
    assert second.audio_fingerprint is None
    assert second.audio_path is None
