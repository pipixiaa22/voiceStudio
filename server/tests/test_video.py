import io
import json

import pytest
from server.routes.video import generate_ass_subtitle, get_resolution


def test_get_resolution_9_16():
    width, height = get_resolution('9:16')
    assert width == 1080
    assert height == 1920


def test_get_resolution_16_9():
    width, height = get_resolution('16:9')
    assert width == 1920
    assert height == 1080


def test_get_resolution_1_1():
    width, height = get_resolution('1:1')
    assert width == 1080
    assert height == 1080


def test_get_resolution_invalid():
    with pytest.raises(ValueError):
        get_resolution('invalid')


def test_generate_ass_subtitle():
    timeline = [
        {'start': 0.0, 'end': 3.0, 'text': '这是第一段字幕'},
        {'start': 3.0, 'end': 6.0, 'text': '这是第二段字幕'},
    ]
    ass_content = generate_ass_subtitle(timeline, 1920, 1080)

    assert '[Script Info]' in ass_content
    assert '[V4+ Styles]' in ass_content
    assert '[Events]' in ass_content
    assert '0:00:00.00' in ass_content
    assert '0:00:03.00' in ass_content
    assert '这是第一段字幕' in ass_content
    assert '这是第二段字幕' in ass_content


def test_generate_ass_subtitle_empty():
    ass_content = generate_ass_subtitle([], 1920, 1080)
    assert '[Script Info]' in ass_content
    assert 'Dialogue' not in ass_content


def test_generate_video_invalid_ratio():
    """测试无效宽高比"""
    with pytest.raises(ValueError):
        get_resolution('4:3')


def test_format_ass_timestamp():
    """测试 ASS 时间戳格式化"""
    from server.routes.video import _format_ass_timestamp
    assert _format_ass_timestamp(0) == '0:00:00.00'
    assert _format_ass_timestamp(61.5) == '0:01:01.50'
    assert _format_ass_timestamp(3661.123) == '1:01:01.12'


def test_video_generate_missing_params(client):
    """测试缺少参数"""
    response = client.post('/api/video/generate')
    assert response.status_code == 400


def test_video_generate_invalid_ratio(client):
    """测试无效宽高比"""
    response = client.post('/api/video/generate', data={
        'aspect_ratio': '4:3',
    })
    assert response.status_code == 400


def test_get_templates(client):
    response = client.get('/api/video/templates')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 5
    assert data[0]['template_key'] == 'xianxia_narration'


def test_get_template_by_key(client):
    response = client.get('/api/video/templates/xianxia_narration')
    assert response.status_code == 200
    data = response.get_json()
    assert data['template_key'] == 'xianxia_narration'


def test_get_template_not_found(client):
    response = client.get('/api/video/templates/nonexistent')
    assert response.status_code == 404


def test_create_video_job_missing_params(client):
    response = client.post('/api/video/jobs', json={})
    assert response.status_code == 400


def test_create_video_job_rejects_missing_workflow_id(client):
    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'voice_source': 'workflow',
    })

    assert response.status_code == 400
    assert response.get_json()['error'] == '请选择配音工程'


def test_create_video_job_rejects_nested_missing_workflow_id(client):
    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'voice_source': 'generate',
        'audio_options': {
            'voice_source': 'workflow',
        },
    })

    assert response.status_code == 400
    assert response.get_json()['error'] == '请选择配音工程'


def test_create_video_job_rejects_nonexistent_workflow_id(client):
    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'voice_source': 'workflow',
        'voice_workflow_id': 999,
    })

    assert response.status_code == 404
    assert response.get_json()['error'] == '配音工程不存在'


def test_create_video_job_normalizes_nested_workflow_request(client, db, monkeypatch):
    from server.models.video import VideoJob
    from server.models.voice_workflow import VoiceWorkflow
    from server.routes import video as video_routes

    workflow = VoiceWorkflow(title='Test Workflow', source_content='测试内容')
    db.session.add(workflow)
    db.session.commit()
    monkeypatch.setattr(video_routes, 'start_job_processing', lambda *args, **kwargs: None)

    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'voice_source': 'generate',
        'audio_options': {
            'voice_source': 'workflow',
            'voice_workflow_id': workflow.id,
        },
    })

    assert response.status_code == 202
    job = VideoJob.query.filter_by(job_id=response.get_json()['job_id']).first()
    request_data = json.loads(job.request_json)
    assert request_data['voice_source'] == 'workflow'
    assert request_data['voice_workflow_id'] == workflow.id


def test_create_video_job(client):
    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'text_id': 1,
        'images': ['scene1.png'],
    })
    assert response.status_code == 202
    data = response.get_json()
    assert 'job_id' in data
    assert data['status'] == 'queued'


def test_get_video_job_status(client):
    create_resp = client.post('/api/video/jobs', json={
        'title': 'Test',
        'template_key': 'xianxia_narration',
        'text_id': 1,
        'images': ['scene1.png'],
    })
    job_id = create_resp.get_json()['job_id']
    response = client.get(f'/api/video/jobs/{job_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['job_id'] == job_id


def test_get_video_job_not_found(client):
    response = client.get('/api/video/jobs/nonexistent')
    assert response.status_code == 404


def test_upload_audio_accepts_wav(client):
    data = {
        'audio': (io.BytesIO(b'RIFF....WAVEfmt '), 'bgm.wav'),
    }

    response = client.post('/api/video/upload-audio', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['filename'].endswith('.wav')
    assert payload['path'].endswith('.wav')


def test_upload_audio_rejects_missing_file(client):
    response = client.post('/api/video/upload-audio', data={}, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json()['error'] == '没有上传音频'


def test_upload_audio_rejects_empty_filename(client):
    data = {
        'audio': (io.BytesIO(b'RIFF....WAVEfmt '), ''),
    }

    response = client.post('/api/video/upload-audio', data=data, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json()['error'] == '没有选择文件'


def test_upload_audio_rejects_non_wav(client):
    data = {
        'audio': (io.BytesIO(b'not-wav'), 'bgm.mp3'),
    }

    response = client.post('/api/video/upload-audio', data=data, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json()['error'] == '第一阶段只支持 WAV 格式 BGM'


def test_upload_audio_rejects_empty_wav(client):
    data = {
        'audio': (io.BytesIO(b''), 'bgm.wav'),
    }

    response = client.post('/api/video/upload-audio', data=data, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json()['error'] == '音频文件为空'
