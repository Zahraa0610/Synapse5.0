import os
import uuid
import re
from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

from .domain import CLINICAL, ROLES, user_public
from .extensions import db
from .http import error, login_required, parse_date, payload, token_for
from .models import Shelter, User, Credential

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    data = payload()
    if any(data.get(field) is not None and not isinstance(data[field], str) for field in ("role", "full_name", "email", "phone", "password", "specialty", "license_number", "license_body", "helper_type")):
        return error("Account fields must be text", 400)
    role = (data.get("role") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""
    if role not in ROLES:
        return error("Choose a role", 400)
    if not full_name or len(full_name) > 160 or phone and len(phone) > 40:
        return error("Enter your name", 400)
    if not email or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 160:
        return error("Enter an email address; phone sign-in is unavailable", 400)
    if len(password) < 10 or len(password) > 256:
        return error("Use a password between 10 and 256 characters", 400)
    if email and User.query.filter_by(email=email).first():
        return error("An account with this email already exists", 409)
    if phone and User.query.filter_by(phone=phone).first():
        return error("An account with this phone number already exists", 409)

    privileged = role in CLINICAL or role in {"ministry", "ngo", "shelter_coordinator"}
    status = "pending" if privileged else "not_required"

    shelter_id = data.get("shelter_id") or None
    if shelter_id:
        shelter = db.session.get(Shelter, int(shelter_id))
        if not shelter:
            return error("That shelter is not registered", 400)
        shelter_id = shelter.id

    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=generate_password_hash(password),
        role="caregiver" if privileged else role,
        requested_role=role if privileged else None,
        specialty=(data.get("specialty") or "").strip() or None,
        license_number=(data.get("license_number") or "").strip() or None,
        license_body=(data.get("license_body") or "").strip() or None,
        license_expires=parse_date(data.get("license_expires")),
        verification_status=status,
        helper_type=(data.get("helper_type") or "").strip() or None,
        shelter_id=None,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("An account with these contact details already exists", 409)
    return jsonify({"token": token_for(user), "user": user_public(user)}), 201


@auth_bp.post("/auth/login")
def login():
    data = payload()
    if any(data.get(field) is not None and not isinstance(data[field], str) for field in ("email", "phone", "password")):
        return error("Login fields must be text", 400)
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    user = None
    if email:
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return error("Email or password is incorrect", 401)
    elif phone:
        return error("Phone verification is unavailable. Sign in with email and password.", 503)
    else:
        return error("Enter your email or phone number", 400)
    return jsonify({"token": token_for(user), "user": user_public(user)})


@auth_bp.get("/auth/me")
@login_required()
def me():
    return jsonify({"user": user_public(g.user)})


@auth_bp.post("/auth/logout")
@login_required()
def logout():
    g.auth_session.revoked = True
    db.session.commit()
    return jsonify({"ok": True})


@auth_bp.post("/auth/phone-code")
def phone_code():
    return error("No SMS or WhatsApp verification provider is configured", 503)


@auth_bp.post("/me/verification-file")
@login_required()
def upload_license():
    upload = request.files.get("file")
    kind = request.form.get("document_kind", "identity")
    if kind not in {"identity", "professional", "practice"}:
        return error("Choose an identity, professional or practice document", 400)
    try:
        saved = _save_credential(upload)
    except ValueError as exc:
        return error(str(exc), 400)
    if not saved:
        return error("Choose a file", 400)
    g.user.license_file = saved["stored_name"]
    db.session.add(Credential(user_id=g.user.id, document_kind=kind, **saved))
    g.user.verification_status = "pending"
    db.session.commit()
    return jsonify({"user": user_public(g.user)})


def _save_credential(upload):
    if not upload or not upload.filename:
        return None
    ext = os.path.splitext(upload.filename)[1].lower()
    signatures = {".pdf": (b"%PDF-",), ".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".webp": (b"RIFF",)}
    if ext not in signatures:
        raise ValueError("Upload a PDF, PNG, JPEG, or WebP document")
    content = upload.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024 or not content.startswith(signatures[ext]):
        raise ValueError("Invalid document format or file exceeds 5 MB")
    if ext == ".webp" and content[8:12] != b"WEBP":
        raise ValueError("Invalid WebP document")
    folder = current_app.config["CREDENTIAL_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    stored = uuid.uuid4().hex + ext
    with open(os.path.join(folder, stored), "xb") as target:
        target.write(content)
    return {"filename": secure_filename(upload.filename) or stored, "stored_name": stored, "mime_type": {".pdf":"application/pdf", ".png":"image/png", ".jpg":"image/jpeg", ".jpeg":"image/jpeg", ".webp":"image/webp"}[ext]}


@auth_bp.get("/me/credentials")
@login_required()
def credentials():
    return jsonify({"credentials": [{"id": row.id, "filename": row.filename, "document_kind": row.document_kind, "status": row.status, "review_note": row.review_note} for row in Credential.query.filter_by(user_id=g.user.id).all()]})


@auth_bp.get("/credentials/<int:credential_id>/file")
@login_required()
def credential_file(credential_id):
    row = db.session.get(Credential, credential_id)
    if not row:
        return error("Document not found", 404)
    if row.user_id != g.user.id and not (g.user.role == "ministry" and g.user.verification_status == "approved"):
        return error("You do not have access to this document", 403)
    response = send_from_directory(current_app.config["CREDENTIAL_FOLDER"], row.stored_name, download_name=row.filename, as_attachment=True)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@auth_bp.get("/clinicians")
@login_required()
def clinicians():
    rows = (
        User.query.filter(User.role.in_(list(CLINICAL)), User.verification_status == "approved")
        .order_by(User.full_name.asc())
        .all()
    )
    return jsonify(
        {
            "clinicians": [
                {
                    "id": row.id,
                    "full_name": row.full_name,
                    "role": row.role,
                    "specialty": row.specialty,
                }
                for row in rows
            ]
        }
    )


@auth_bp.get("/shelters")
@login_required()
def list_shelters():
    from .domain import priority_for, shelter_public
    from .models import InventoryItem

    rows = []
    for shelter in Shelter.query.order_by(Shelter.name.asc()).all():
        item = shelter_public(shelter)
        item["priority"] = priority_for(shelter) if g.user.role in {"ministry", "shelter_coordinator"} else None
        shortages = InventoryItem.query.filter_by(shelter_id=shelter.id, status="shortage").all()
        item["shortage_names"] = [row.item_name for row in shortages]
        item["equipment"] = [
            {"name": row.item_name, "status": row.status, "quantity": row.quantity}
            for row in InventoryItem.query.filter_by(shelter_id=shelter.id, is_equipment=True).all()
        ]
        rows.append(item)
    return jsonify({"shelters": rows})


@auth_bp.patch("/users/<int:user_id>/verification")
@login_required({"ministry"}, approved=True)
def review_verification(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return error("Account not found", 404)
    if user.id == g.user.id:
        return error("You cannot review your own credentials", 403)
    data = payload()
    status = (data.get("status") or "").strip()
    if status not in {"pending", "approved", "rejected"}:
        return error("Choose a review status", 400)
    documents = Credential.query.filter_by(user_id=user.id).all()
    if status == "approved" and not documents:
        return error("A privately submitted identity or professional document is required", 400)
    requested = user.requested_role or user.role
    if status == "approved":
        kinds = {document.document_kind for document in documents}
        required = {"identity", "professional"} if requested in CLINICAL else {"identity"}
        if not required.issubset(kinds):
            return error("Submit identity and required professional documents before approval", 400)
    if requested == "ministry" and status == "approved":
        return error("Ministry authorization requires an operator, not peer approval", 403)
    if requested == "shelter_coordinator" and status == "approved":
        shelter = db.session.get(Shelter, int(data.get("shelter_id") or 0))
        if not shelter:
            return error("Assign a registered shelter before approval", 400)
        user.shelter_id = shelter.id
    if status == "approved":
        user.role = requested
        user.requested_role = None
    elif user.role in CLINICAL or user.role in {"ngo", "shelter_coordinator"}:
        user.requested_role = user.role
        user.role = "caregiver"
        user.shelter_id = None
    for document in documents:
        document.status = status
        document.reviewer_id = g.user.id
        document.review_note = str(data.get("note") or "Manual review")[:2000]
    user.verification_status = status
    db.session.commit()
    return jsonify({"user": user_public(user)})


@auth_bp.patch("/users/<int:user_id>/shelter")
@login_required()
def assign_shelter(user_id):
    if g.user.role != "ministry":
        return error("You do not have access to this", 403)
    if g.user.role == "ministry" and g.user.verification_status != "approved":
        return error("This account is still under review", 403)
    user = db.session.get(User, user_id)
    if not user:
        return error("Account not found", 404)
    if user.role != "shelter_coordinator" or user.verification_status != "approved":
        return error("Only approved coordinators can be assigned a shelter", 400)
    shelter = db.session.get(Shelter, int(payload().get("shelter_id") or 0))
    if not shelter:
        return error("That shelter is not registered", 400)
    user.shelter_id = shelter.id
    db.session.commit()
    return jsonify({"user": user_public(user)})


@auth_bp.get("/verification-queue")
@login_required({"ministry"}, approved=True)
def verification_queue():
    rows = User.query.filter(User.verification_status.in_(["pending", "rejected", "documents_received", "checking"])).all()
    return jsonify({"users": [{**user_public(row), "credentials": [{"id": document.id, "filename": document.filename, "document_kind": document.document_kind, "status": document.status} for document in Credential.query.filter_by(user_id=row.id).all()]} for row in rows]})
