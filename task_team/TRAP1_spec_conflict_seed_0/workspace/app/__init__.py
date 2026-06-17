"""
marketplace_api — Flask application factory.
"""
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["TESTING"] = False

    from app.routes import register_routes
    register_routes(app)

    return app
