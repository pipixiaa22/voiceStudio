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
