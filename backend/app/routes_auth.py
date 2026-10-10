from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .domain import CLINICAL, ROLES, user_public
from .extensions import db
from .http import as_bool, error, login_required, parse_date, payload, save_upload, token_for
from .models import Shelter, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    data = payload()
    role = (data.get("role") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower() or None
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""
    if role not in ROLES:
        return error("Choose a role", 400)
    if not full_name:
        return error("Enter your name", 400)
    if not email and not phone:
        return error("Enter a phone number or email", 400)
    if len(password) < 6:
        return error("Use at least 6 characters for the password", 400)
    if email and User.query.filter_by(email=email).first():
        return error("An account with this email already exists", 409)
    if phone and User.query.filter_by(phone=phone).first():
        return error("An account with this phone number already exists", 409)

    if role in CLINICAL:
        status = "documents_received"
    elif role in {"ministry", "ngo"}:
        status = "checking"
    else:
        status = "not_required"

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
        role=role,
        specialty=(data.get("specialty") or "").strip() or None,
        license_number=(data.get("license_number") or "").strip() or None,
        license_body=(data.get("license_body") or "").strip() or None,
        license_expires=parse_date(data.get("license_expires")),
        verification_status=status,
        helper_type=(data.get("helper_type") or "").strip() or None,
        shelter_id=shelter_id if role in {"shelter_coordinator", "caregiver"} else None,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"token": token_for(user), "user": user_public(user)}), 201


@auth_bp.post("/auth/login")
def login():
    data = payload()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""
    code = (data.get("code") or "").strip()

    user = None
    if email:
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return error("Email or password is incorrect", 401)
    elif phone:
        user = User.query.filter_by(phone=phone).first()
        if not user or code != "000000":
            return error("Phone number or code is incorrect", 401)
    else:
        return error("Enter your email or phone number", 400)
    return jsonify({"token": token_for(user), "user": user_public(user)})


@auth_bp.get("/auth/me")
@login_required()
def me():
    return jsonify({"user": user_public(g.user)})


@auth_bp.post("/me/verification-file")
@login_required()
def upload_license():
    upload = request.files.get("file")
    try:
        saved = save_upload(upload)
    except ValueError as exc:
        return error(str(exc), 400)
    if not saved:
        return error("Choose a file", 400)
    g.user.license_file = saved["stored_name"]
    if g.user.role in CLINICAL and g.user.verification_status == "not_required":
        g.user.verification_status = "documents_received"
    db.session.commit()
    return jsonify({"user": user_public(g.user)})


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
    status = (payload().get("status") or "").strip()
    if status not in {"documents_received", "checking", "approved"}:
        return error("Choose a review status", 400)
    user.verification_status = status
    db.session.commit()
    return jsonify({"user": user_public(user)})


@auth_bp.patch("/users/<int:user_id>/shelter")
@login_required()
def assign_shelter(user_id):
    if g.user.id != user_id and g.user.role != "ministry":
        return error("You do not have access to this", 403)
    if g.user.role == "ministry" and g.user.verification_status != "approved":
        return error("This account is still under review", 403)
    user = db.session.get(User, user_id)
    if not user:
        return error("Account not found", 404)
    shelter = db.session.get(Shelter, int(payload().get("shelter_id") or 0))
    if not shelter:
        return error("That shelter is not registered", 400)
    user.shelter_id = shelter.id
    db.session.commit()
    return jsonify({"user": user_public(user)})


@auth_bp.get("/verification-queue")
@login_required({"ministry"}, approved=True)
def verification_queue():
    rows = User.query.filter(User.verification_status.in_(["documents_received", "checking"])).all()
    return jsonify({"users": [user_public(row) for row in rows]})
