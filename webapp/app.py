from flask import Flask

from config import Config
from routes import health


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(health.bp)

    @app.get("/")
    def index():
        return "Hello World"

    return app


app = create_app()