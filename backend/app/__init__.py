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


def _check_schema():
    """Stop with a clear message when maak.db was made by an older version of the app."""
    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    missing = []
    for table in db.metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        missing += [f"{table.name}.{column.name}" for column in table.columns if column.name not in existing]
    if missing:
        raise SystemExit(
            "\n\nYour database (backend/maak.db) is from an older version of Ma'ak.\n"
            "Run `python manage.py reset` (or delete backend/maak.db) and start again.\n"
            f"Missing columns: {', '.join(missing[:6])}{' ...' if len(missing) > 6 else ''}\n"
        )


def create_app(check_schema=True):
    app = Flask(__name__)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Demo mode: loads fictional demo data into an empty database and shows
    # quick-login buttons. Turn it on with `python run.py --demo` or MAAK_DEMO=1.
    app.config["DEMO"] = os.environ.get("MAAK_DEMO", "").lower() in {"1", "true", "yes"}
    secret = os.environ.get("MAAK_SECRET")
    if not secret:
        secret = "local-development-only"
        print(" * MAAK_SECRET is not set: using a development key. Set it before deploying.")
    app.config["SECRET_KEY"] = secret
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
        return {"ok": True, "name": "Ma'ak", "demo": app.config["DEMO"]}

    @app.get("/api/demo/accounts")
    def demo_accounts():
        if not app.config["DEMO"]:
            return {"error": "Not found"}, 404
        from .demo_data import DEMO_ACCOUNTS, DEMO_PASSWORD

        return {"accounts": [{"label": label, "email": email} for label, email in DEMO_ACCOUNTS], "password": DEMO_PASSWORD}

    with app.app_context():
        if not check_schema:
            return app  # manage.py: reset/demo rebuild the tables themselves
        db.create_all()
        _check_schema()
        if app.config["DEMO"]:
            from .demo_data import load_demo_data

            if load_demo_data():
                print(" * Demo mode: demo data loaded.")
            else:
                print(" * Demo mode: database already has data, nothing loaded. Run `python manage.py demo` for a fresh demo.")
    return app
