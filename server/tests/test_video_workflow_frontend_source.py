from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_video_generate_modal_sends_voice_workflow_payload():
    source = (ROOT / 'web/src/components/video/VideoGenerateModal.vue').read_text()

    assert 'voice_source:' in source
    assert 'voice_workflow_id:' in source
    assert "audioOptions.value.voice_source" in source
    assert "audioOptions.value.voice_workflow_id" in source


def test_audio_mix_step_source_has_wav_upload_and_choice_guards():
    source = (ROOT / 'web/src/components/video/AudioMixStep.vue').read_text()

    assert 'videoApi.uploadAudio' in source
    assert 'accept=".wav"' in source
    assert '请选择配音工程' in source
    assert '请先上传 BGM 文件' in source
    assert 'bgm_path' in source


def test_video_preview_step_source_displays_audio_source_states():
    source = (ROOT / 'web/src/components/video/VideoPreviewStep.vue').read_text()

    assert '音频来源' in source
    assert '配音工程' in source
    assert '配音工程未选择' in source
    assert 'voice_source' in source
