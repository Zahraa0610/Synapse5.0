import os

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


def create_app():
    app = Flask(__name__)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app.config["SECRET_KEY"] = os.environ.get("MAAK_SECRET", "maak-dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(base, "maak.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(base, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": "*"}})
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

    with app.app_context():
        db.create_all()
        seed()
    return app
