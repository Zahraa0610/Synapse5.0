import os

from flask import Flask

from .extensions import db
from .routes_auth import auth_bp
from .routes_care import care_bp
from .routes_oversight import oversight_bp
from .routes_passport import passport_bp
from .routes_people import people_bp
from .routes_shelter import shelter_bp

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_env_file(path=os.path.join(BASE_DIR, ".env")):
    """Read KEY=value lines from backend/.env into the environment (if the file exists).
    Values already set in the environment win."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_app(config=None):
    load_env_file()
    app = Flask(__name__)
    secret = os.environ.get("MAAK_SECRET")
    if not secret:
        secret = "local-development-only-key-change-me-in-backend-env"
        print(" * MAAK_SECRET is not set: using a development key. Set it in backend/.env before deploying.")
    app.config.update(
        SECRET_KEY=secret,
        # Database: Google Cloud Firestore (see app/store.py)
        STORE=os.environ.get("MAAK_STORE", "firestore"),
        FIREBASE_CREDENTIALS=os.environ.get("FIREBASE_CREDENTIALS"),
        FIREBASE_PROJECT_ID=os.environ.get("FIREBASE_PROJECT_ID"),
        # WhatsApp verification codes (see app/whatsapp.py)
        TWILIO_ACCOUNT_SID=os.environ.get("TWILIO_ACCOUNT_SID"),
        TWILIO_AUTH_TOKEN=os.environ.get("TWILIO_AUTH_TOKEN"),
        TWILIO_WHATSAPP_FROM=os.environ.get("TWILIO_WHATSAPP_FROM"),
        TWILIO_CONTENT_SID=os.environ.get("TWILIO_CONTENT_SID"),
        UPLOAD_FOLDER=os.path.join(BASE_DIR, "uploads"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
    )
    if config:
        app.config.update(config)

    try:
        from flask_cors import CORS

        CORS(app, resources={r"/api/*": {"origins": "*"}})
    except ImportError:  # the Vite dev server proxies /api, so CORS is optional locally
        pass

    db.init_app(app)
    for blueprint in (auth_bp, passport_bp, care_bp, people_bp, shelter_bp, oversight_bp):
        app.register_blueprint(blueprint, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"ok": True, "name": "Ma'ak"}

    return app
