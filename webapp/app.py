from flask import Flask, jsonify

import history
from config import Config
from routes import files, health, search, searches, upload


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(health.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(files.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(searches.bp)

    try:
        history.ensure_indexes()
    except Exception:
        pass  # MongoDB peut démarrer après la webapp

    @app.get("/")
    def index():
        return "Hello World"

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": f"Fichier trop volumineux (maximum {Config.MAX_UPLOAD_MB} Mo)"}), 413

    return app


app = create_app()