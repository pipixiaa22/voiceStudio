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
