import pytest
from server.app import create_app
from server.models import db as _db


@pytest.fixture
def app():
    app = create_app(test_config={
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True,
    })
    with app.app_context():
        _db.create_all()
        from server.services.video_template import seed_builtin_templates
        seed_builtin_templates()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db
