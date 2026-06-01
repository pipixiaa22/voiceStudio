import pytest


def test_create_job(app, db):
    from server.services.video_job import create_job
    job = create_job(title='Test Video', request={'template_key': 'xianxia_narration'})
    assert job.job_id is not None
    assert job.status == 'queued'
    assert job.title == 'Test Video'


def test_get_job(app, db):
    from server.services.video_job import create_job, get_job
    job = create_job(title='Test Video', request={})
    found = get_job(job.job_id)
    assert found is not None
    assert found.title == 'Test Video'


def test_get_job_not_found(app, db):
    from server.services.video_job import get_job
    found = get_job('nonexistent')
    assert found is None


def test_update_job_progress(app, db):
    from server.services.video_job import create_job, update_job_progress
    job = create_job(title='Test', request={})
    update_job_progress(job.job_id, 0.5, 'rendering', 'Rendering video')
    from server.services.video_job import get_job
    updated = get_job(job.job_id)
    assert updated.status == 'rendering'
    assert updated.progress == 0.5


def test_update_job_completed(app, db):
    from server.services.video_job import create_job, update_job_completed
    job = create_job(title='Test', request={})
    update_job_completed(job.job_id, '/tmp/output.mp4', '{}')
    from server.services.video_job import get_job
    updated = get_job(job.job_id)
    assert updated.status == 'completed'
    assert updated.progress == 1.0


def test_update_job_failed(app, db):
    from server.services.video_job import create_job, update_job_failed
    job = create_job(title='Test', request={})
    update_job_failed(job.job_id, 'Something went wrong')
    from server.services.video_job import get_job
    updated = get_job(job.job_id)
    assert updated.status == 'failed'
    assert updated.error_message == 'Something went wrong'


def test_build_voice_track_uses_workflow_when_requested(app, monkeypatch):
    from server.services import video_job

    captured = {}

    def fake_workflow_track(workflow_id, request_data):
        captured['workflow_id'] = workflow_id
        captured['request_data'] = request_data
        return {
            'source': 'voice_workflow',
            'workflow_id': workflow_id,
            'voice_audio': b'voice',
            'subtitle_timeline': [{'index': 1, 'text': '第一句。', 'start': 0, 'end': 1}],
            'manifest': {'source': 'voice_workflow', 'workflow_id': workflow_id},
            'voice_chunks': [{'text': '第一句。'}],
            'duration': 1,
        }

    monkeypatch.setattr(video_job, 'build_voice_track_from_workflow', fake_workflow_track)

    result = video_job.build_voice_track({
        'voice_source': 'workflow',
        'voice_workflow_id': 42,
        'api_key': 'key',
    })

    assert result['source'] == 'voice_workflow'
    assert captured['workflow_id'] == 42


def test_build_voice_track_falls_back_to_text_mode(app, db, monkeypatch):
    from server.models import Text
    from server.services import video_job

    text = Text(title='文本', content='你好。')
    db.session.add(text)
    db.session.commit()

    def fake_text_track(request_data):
        return {
            'source': 'text',
            'voice_audio': b'voice',
            'subtitle_timeline': [{'index': 1, 'text': '你好。', 'start': 0, 'end': 1}],
            'voice_chunks': [{'index': 1, 'text': '你好。'}],
            'duration': 1,
        }

    monkeypatch.setattr(video_job, 'build_voice_track_from_text', fake_text_track)

    result = video_job.build_voice_track({'text_id': text.id, 'api_key': 'key'})

    assert result['source'] == 'text'


def test_merge_video_manifest_marks_workflow_source():
    from server.services.video_job import merge_video_manifest

    manifest = merge_video_manifest(
        title='视频',
        template_key='xianxia_narration',
        resolution=[1080, 1920],
        scenes=[{'imagePath': '/tmp/a.png'}],
        audio_options={'bgm_enabled': False},
        voice_track={
            'source': 'voice_workflow',
            'workflow_id': 7,
            'duration': 1.2,
            'subtitle_timeline': [{'text': '第一句。', 'start': 0, 'end': 1.2}],
            'voice_chunks': [{'text': '第一句。'}],
            'manifest': {'source': 'voice_workflow', 'workflow_id': 7, 'segments': []},
        },
        warnings=['BGM 已开启但没有上传 WAV 文件'],
    )

    assert manifest['source'] == 'voice_workflow'
    assert manifest['workflow_id'] == 7
    assert manifest['video']['audio_options']['bgm_enabled'] is False
    assert manifest['video']['warnings'] == ['BGM 已开启但没有上传 WAV 文件']
