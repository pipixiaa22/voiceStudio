import os
from flask import Flask
from flask_cors import CORS
from server.models import db


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static', static_url_path='')

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        from server.routes.texts import texts_bp
        from server.routes.folders import folders_bp
        from server.routes.tags import tags_bp
        from server.routes.tts import tts_bp
        from server.routes.video import video_bp
        from server.routes.voice_profiles import voice_profiles_bp
        app.register_blueprint(texts_bp)
        app.register_blueprint(folders_bp)
        app.register_blueprint(tags_bp)
        app.register_blueprint(tts_bp)
        app.register_blueprint(video_bp)
        app.register_blueprint(voice_profiles_bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app


def main():
    app = create_app()
    app.run(debug=True, port=5002)


if __name__ == '__main__':
    main()
