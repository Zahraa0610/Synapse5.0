import os
import secrets
import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine

from flask import Flask
from flask_cors import CORS

from .extensions import db
from .routes_auth import auth_bp
from .routes_care import care_bp
from .routes_oversight import oversight_bp
from .routes_passport import passport_bp
from .routes_people import people_bp
from .routes_shelter import shelter_bp
from .seed import seed


@event.listens_for(Engine, "connect")
def enable_foreign_keys(connection, record):
    if isinstance(connection, sqlite3.Connection):
        connection.execute("PRAGMA foreign_keys=ON")


def create_app(config=None):
    app = Flask(__name__)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app.config["SECRET_KEY"] = os.environ.get("MAAK_SECRET") or secrets.token_hex(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("MAAK_DATABASE_URL", "sqlite:///" + os.path.join(base, "maak-dev.db"))
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(base, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
    app.config["SESSION_HOURS"] = 8
    app.config["AUTO_MIGRATE"] = False
    app.config["SEED_DEMO"] = False
    app.config["CREDENTIAL_FOLDER"] = os.environ.get("MAAK_CREDENTIAL_FOLDER", os.path.join(base, "private_credentials"))
    if config:
        app.config.update(config)
    if os.environ.get("MAAK_ENV") == "production" and (not os.environ.get("MAAK_SECRET") or len(app.config["SECRET_KEY"]) < 32):
        raise RuntimeError("Production requires a MAAK_SECRET of at least 32 characters")
    CORS(app, resources={r"/api/*": {"origins": os.environ.get("MAAK_CORS_ORIGINS", "http://localhost:5173").split(",")}})
    db.init_app(app)
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(passport_bp, url_prefix="/api")
    app.register_blueprint(care_bp, url_prefix="/api")
    app.register_blueprint(people_bp, url_prefix="/api")
    app.register_blueprint(shelter_bp, url_prefix="/api")
    app.register_blueprint(oversight_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"ok": True, "name": "Ma'ak"}

    @app.errorhandler(400)
    def bad_input(exc):
        return {"error": "Invalid request"}, 400

    @app.errorhandler(413)
    def too_large(exc):
        return {"error": "File exceeds the upload size limit"}, 413

    @app.errorhandler(ValueError)
    @app.errorhandler(TypeError)
    def invalid_values(exc):
        db.session.rollback()
        return {"error": "Invalid request values"}, 400

    @app.cli.command("db-upgrade")
    def db_upgrade():
        from .migrations import upgrade
        upgrade()

    @app.cli.command("seed-demo")
    def seed_demo():
        if os.environ.get("MAAK_ENV") == "production":
            raise RuntimeError("Demo seeding is disabled in production")
        seed()

    with app.app_context():
        if app.config["AUTO_MIGRATE"]:
            from .migrations import upgrade
            upgrade()
        if app.config["SEED_DEMO"]:
            seed()
    return app
