from flask import Flask, jsonify

from config import Config
from routes import files, health, upload


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(health.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(files.bp)

    @app.get("/")
    def index():
        return "Hello World"

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": f"Fichier trop volumineux (maximum {Config.MAX_UPLOAD_MB} Mo)"}), 413

    return app


app = create_app()