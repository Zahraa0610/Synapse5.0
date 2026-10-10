import os
import uuid
from datetime import date, datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from .extensions import db
from .models import User, AuthSession

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".dcm", ".dicom"}


def error(message, code):
    return jsonify({"error": message}), code


def token_for(user):
    expires = datetime.now(timezone.utc) + timedelta(hours=current_app.config["SESSION_HOURS"])
    session = AuthSession(id=uuid.uuid4().hex, user_id=user.id, expires_at=expires, revoked=False)
    db.session.add(session)
    db.session.commit()
    payload = {"uid": user.id, "sid": session.id, "exp": expires}
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode()
    return token


def current_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"], options={"require": ["uid", "sid", "exp"]})
    except jwt.PyJWTError:
        return None
    session = db.session.get(AuthSession, payload.get("sid"))
    if not session or session.revoked or session.user_id != payload.get("uid") or session.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        return None
    g.auth_session = session
    return db.session.get(User, session.user_id)


def login_required(roles=None, approved=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return error("Sign in required", 401)
            if roles and user.role not in roles:
                return error("You do not have access to this", 403)
            privileged = {"doctor", "nurse", "psychologist", "ministry", "ngo", "shelter_coordinator"}
            account_endpoints = {"auth.me", "auth.upload_license", "auth.logout", "auth.credential_file", "auth.credentials"}
            if user.role in privileged and user.verification_status != "approved" and request.endpoint not in account_endpoints:
                return error("This account is still under review", 403)
            if user.role == "shelter_coordinator" and not user.shelter_id and request.endpoint not in account_endpoints:
                return error("An authorized reviewer must assign your shelter", 403)
            if approved and user.verification_status != "approved":
                return error("This account is still under review", 403)
            g.user = user
            try:
                return fn(*args, **kwargs)
            except (ValueError, TypeError):
                db.session.rollback()
                return error("Invalid request values", 400)

        return wrapper

    return decorator


def payload():
    if request.content_type and "multipart/form-data" in request.content_type:
        return request.form
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        from werkzeug.exceptions import BadRequest
        raise BadRequest()
    return data


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def parse_date(value):
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def parse_dt(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    if len(text) == 10:
        text += "T09:00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def save_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Upload a PDF, image, or DICOM file")
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    file_storage.save(os.path.join(folder, stored))
    return {
        "stored_name": stored,
        "filename": secure_filename(file_storage.filename) or stored,
        "mime_type": file_storage.mimetype or "application/octet-stream",
    }
