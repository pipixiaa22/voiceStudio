from server.models import Text, Folder, Tag


def test_create_text(app, db):
    with app.app_context():
        text = Text(title='测试标题', content='测试内容')
        db.session.add(text)
        db.session.commit()
        assert text.id is not None
        assert text.title == '测试标题'


def test_create_folder(app, db):
    with app.app_context():
        folder = Folder(name='测试文件夹')
        db.session.add(folder)
        db.session.commit()
        assert folder.id is not None


def test_create_tag(app, db):
    with app.app_context():
        tag = Tag(name='测试标签')
        db.session.add(tag)
        db.session.commit()
        assert tag.id is not None


def test_text_with_folder(app, db):
    with app.app_context():
        folder = Folder(name='文件夹')
        db.session.add(folder)
        db.session.flush()
        text = Text(title='标题', content='内容', folder_id=folder.id)
        db.session.add(text)
        db.session.commit()
        assert text.folder_id == folder.id


def test_text_with_tags(app, db):
    with app.app_context():
        tag1 = Tag(name='标签1')
        tag2 = Tag(name='标签2')
        db.session.add_all([tag1, tag2])
        db.session.flush()
        text = Text(title='标题', content='内容', tags=[tag1, tag2])
        db.session.add(text)
        db.session.commit()
        assert len(text.tags) == 2


def test_video_template_create(app, db):
    from server.models import VideoTemplate
    template = VideoTemplate(
        template_key='test_template',
        name='Test Template',
        config_json='{"fps": 24}',
        is_builtin=True,
    )
    db.session.add(template)
    db.session.commit()
    assert template.id is not None
    assert template.template_key == 'test_template'


def test_video_template_to_dict(app, db):
    from server.models import VideoTemplate
    template = VideoTemplate(
        template_key='test_template',
        name='Test Template',
        config_json='{"fps": 24}',
    )
    db.session.add(template)
    db.session.commit()
    d = template.to_dict()
    assert d['template_key'] == 'test_template'
    assert d['name'] == 'Test Template'
    assert d['config'] == {'fps': 24}


def test_video_job_create(app, db):
    from server.models import VideoJob
    job = VideoJob(
        job_id='test-job-uuid',
        title='Test Video',
        status='queued',
        request_json='{}',
    )
    db.session.add(job)
    db.session.commit()
    assert job.id is not None
    assert job.status == 'queued'


def test_video_job_to_dict(app, db):
    from server.models import VideoJob
    job = VideoJob(
        job_id='test-job-uuid',
        title='Test Video',
        status='rendering',
        progress=0.5,
        stage='mixing_audio',
        message='Mixing audio',
    )
    db.session.add(job)
    db.session.commit()
    d = job.to_dict()
    assert d['job_id'] == 'test-job-uuid'
    assert d['status'] == 'rendering'
    assert d['progress'] == 0.5
