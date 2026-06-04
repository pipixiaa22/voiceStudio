import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from server.models import db

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Always load the project .env explicitly. `override=True` makes settings saved
# from the UI take effect after restart even if the shell had stale variables.
load_dotenv(ENV_PATH, override=True)


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static', static_url_path='')

    # Support DATABASE_URL environment variable for MySQL, fallback to SQLite
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        from server.services.video_template import seed_builtin_templates
        seed_builtin_templates()
        from server.services.discovery_seed import seed_discovery_sources
        seed_discovery_sources()
        from server.routes.texts import texts_bp
        from server.routes.folders import folders_bp
        from server.routes.tags import tags_bp
        from server.routes.tts import tts_bp
        from server.routes.video import video_bp
        from server.routes.voice_profiles import voice_profiles_bp
        from server.routes.models import models_bp
        app.register_blueprint(texts_bp)
        app.register_blueprint(folders_bp)
        app.register_blueprint(tags_bp)
        app.register_blueprint(tts_bp)
        app.register_blueprint(video_bp)
        app.register_blueprint(voice_profiles_bp)
        app.register_blueprint(models_bp)
        from server.routes.discovery import discovery_bp
        app.register_blueprint(discovery_bp)
        from server.routes.voice_workflows import voice_workflows_bp
        app.register_blueprint(voice_workflows_bp)
        from server.routes.system import system_bp
        app.register_blueprint(system_bp)
        from server.routes.novels import novels_bp
        app.register_blueprint(novels_bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app


def main():
    app = create_app()
    debug = os.environ.get('FLASK_DEBUG') == '1'
    app.run(debug=debug, port=5002, use_reloader=False)


if __name__ == '__main__':
    main()
