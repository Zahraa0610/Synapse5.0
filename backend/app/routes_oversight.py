from flask import Blueprint, g, jsonify, request

from .domain import (
    complaint_patterns,
    distribution,
    forecast,
    high_risk,
    history_for_shelter,
    iso,
    priority_for,
    profile_public,
    regional_trends,
    shelter_public,
    support_counts,
    user_public,
)
from .domain import can_view_passport
from .extensions import db
from .http import error, login_required, payload
from .models import (
    Complaint,
    Donation,
    InventoryItem,
    NgoRequest,
    Outbreak,
    Profile,
    Shelter,
    User,
)

oversight_bp = Blueprint("oversight", __name__)


@oversight_bp.get("/doctor/patients")
@login_required({"doctor", "nurse", "psychologist"})
def doctor_patients():
    from .models import AccessGrant

    if g.user.verification_status != "approved":
        return jsonify({"patients": [], "verification_status": g.user.verification_status, "user": user_public(g.user)})
    q = (request.args.get("q") or "").strip()
    grants = AccessGrant.query.filter_by(grantee_user_id=g.user.id, status="active").all()
    patients = []
    for grant in grants:
        profile = db.session.get(Profile, grant.profile_id)
        if not profile:
            continue
        if q and q.lower() not in profile.full_name.lower():
            continue
        patients.append(profile_public(profile))
    return jsonify({"patients": patients, "verification_status": g.user.verification_status, "user": user_public(g.user)})


@oversight_bp.get("/doctor/profiles/<int:profile_id>")
@login_required({"doctor", "nurse", "psychologist"})
def doctor_profile(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile or not can_view_passport(g.user, profile):
        return error("This patient has not granted you access", 403)
    from .routes_passport import _entry_json
    from .models import MedicalEntry

    entries = MedicalEntry.query.filter_by(profile_id=profile.id).all()
    return jsonify({"profile": profile_public(profile), "entries": [_entry_json(entry) for entry in entries]})


@oversight_bp.get("/ministry/overview")
@login_required({"ministry"}, approved=True)
def overview():
    shelters = Shelter.query.order_by(Shelter.name.asc()).all()
    ranked = []
    occupancy = 0
    critical = 0
    shortages = 0
    for shelter in shelters:
        score = priority_for(shelter)
        occupancy += shelter.occupancy or 0
        critical += score["critical_residents"]
        shortages += score["shortages"]
        ranked.append({**shelter_public(shelter), "priority": score})
    ranked.sort(key=lambda row: -row["priority"]["score"])
    return jsonify(
        {
            "shelter_count": len(shelters),
            "occupancy": occupancy,
            "critical_residents": critical,
            "open_shortages": shortages,
            "open_complaints": Complaint.query.filter(Complaint.status != "resolved").count(),
            "donation_count": Donation.query.count(),
            "outbreak_count": Outbreak.query.filter(Outbreak.status != "investigating").count(),
            "ranked": ranked,
            "forecast": forecast(),
            "note": "Figures are aggregated from shelter reports. They support a decision; they do not make one.",
        }
    )


@oversight_bp.get("/ministry/shelters")
@login_required({"ministry"}, approved=True)
def ministry_shelters():
    rows = []
    for shelter in Shelter.query.order_by(Shelter.name.asc()).all():
        inventory = InventoryItem.query.filter_by(shelter_id=shelter.id).all()
        rows.append(
            {
                **shelter_public(shelter),
                "priority": priority_for(shelter),
                "history": history_for_shelter(shelter.id),
                "inventory": [
                    {
                        "item_name": item.item_name,
                        "status": item.status,
                        "quantity": item.quantity,
                        "is_equipment": item.is_equipment,
                        "is_specialized": item.is_specialized,
                    }
                    for item in inventory
                ],
            }
        )
    rows.sort(key=lambda row: -row["priority"]["score"])
    return jsonify({"shelters": rows})


@oversight_bp.get("/ministry/complaints")
@login_required({"ministry"}, approved=True)
def ministry_complaints():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return jsonify(
        {
            "complaints": [
                {
                    "id": item.id,
                    "shelter_id": item.shelter_id,
                    "region": item.region,
                    "category": item.category,
                    "description": item.description,
                    "source": item.source,
                    "status": item.status,
                    "created_at": iso(item.created_at),
                }
                for item in complaints
            ],
            "patterns": complaint_patterns(),
            "regions": regional_trends(),
            "support_counts": support_counts(),
        }
    )


@oversight_bp.get("/ministry/ngos")
@login_required({"ministry"}, approved=True)
def ministry_ngos():
    return jsonify({"requests": [_ngo(item) for item in NgoRequest.query.order_by(NgoRequest.created_at.desc()).all()]})


@oversight_bp.get("/ministry/donations")
@login_required({"ministry"}, approved=True)
def ministry_donations():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    rows = []
    for item in donations:
        shelter = db.session.get(Shelter, item.target_shelter_id) if item.target_shelter_id else None
        donor = db.session.get(User, item.donor_id)
        rows.append(
            {
                "id": item.id,
                "donor_name": donor.full_name if donor else None,
                "kind": item.kind,
                "amount": item.amount,
                "currency": item.currency,
                "item_description": item.item_description,
                "shelter_name": shelter.name if shelter else None,
                "region": shelter.region if shelter else None,
                "cause_label": item.cause_label,
                "status": item.status,
                "target_type": item.target_type,
            }
        )
    return jsonify({"donations": rows, "distribution": distribution()})


@oversight_bp.get("/ministry/reports")
@login_required({"ministry"}, approved=True)
def ministry_reports():
    outbreaks = Outbreak.query.order_by(Outbreak.created_at.desc()).all()
    from .routes_shelter import _outbreak

    return jsonify(
        {
            "high_risk": high_risk(),
            "forecast": forecast(),
            "history": [
                {"shelter": shelter_public(shelter), **history_for_shelter(shelter.id)}
                for shelter in Shelter.query.order_by(Shelter.name.asc()).all()
            ],
            "outbreaks": [_outbreak(item) for item in outbreaks],
            "support_counts": support_counts(),
        }
    )


def _ngo(item):
    shelter = db.session.get(Shelter, item.shelter_id) if item.shelter_id else None
    user = db.session.get(User, item.ngo_user_id)
    return {
        "id": item.id,
        "organization": item.organization or (user.full_name if user else "NGO"),
        "description": item.description,
        "shelter_id": item.shelter_id,
        "shelter_name": shelter.name if shelter else None,
        "status": item.status,
        "created_at": iso(item.created_at),
    }


@oversight_bp.get("/ngo/board")
@login_required({"ngo"}, approved=True)
def ngo_board():
    from .models import TransportRequest

    mine = NgoRequest.query.filter_by(ngo_user_id=g.user.id).order_by(NgoRequest.created_at.desc()).all()
    rides = TransportRequest.query.filter(TransportRequest.status.in_(["requested", "accepted"])).all()
    from .routes_people import _transport

    return jsonify({"requests": [_ngo(item) for item in mine], "transports": [_transport(item) for item in rides]})


@oversight_bp.post("/ngo/requests")
@login_required({"ngo"}, approved=True)
def create_ngo_request():
    data = payload()
    description = (data.get("description") or "").strip()
    if not description:
        return error("Describe the assistance you can offer", 400)
    item = NgoRequest(
        ngo_user_id=g.user.id,
        organization=(data.get("organization") or g.user.full_name).strip(),
        description=description,
        status="submitted",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"request": _ngo(item)}), 201


@oversight_bp.patch("/ngo/requests/<int:item_id>")
@login_required({"ministry", "ngo", "shelter_coordinator"})
def update_ngo_request(item_id):
    if g.user.role in {"ministry", "ngo"} and g.user.verification_status != "approved":
        return error("This account is still under review", 403)
    item = db.session.get(NgoRequest, item_id)
    if not item:
        return error("Request not found", 404)
    data = payload()
    if g.user.role == "ministry":
        if data.get("shelter_id"):
            shelter = db.session.get(Shelter, int(data.get("shelter_id")))
            if not shelter:
                return error("That shelter is not registered", 400)
            item.shelter_id = shelter.id
            if item.status == "submitted":
                item.status = "connected"
        status = (data.get("status") or "").strip()
        if status:
            if status not in {"submitted", "connected", "accepted", "delivered", "completed"}:
                return error("Choose a status", 400)
            item.status = status
    elif g.user.role == "ngo":
        if item.ngo_user_id != g.user.id:
            return error("This request belongs to another organization", 403)
        status = (data.get("status") or "").strip()
        if status not in {"accepted", "delivered", "completed"}:
            return error("Update the request once the Ministry has connected it", 400)
        if item.status == "submitted":
            return error("Wait until the Ministry connects this request to a shelter", 400)
        item.status = status
    else:
        if item.shelter_id != g.user.shelter_id:
            return error("This request is for another shelter", 403)
        status = (data.get("status") or "").strip()
        if status not in {"accepted", "delivered", "completed"}:
            return error("Choose accepted, delivered, or completed", 400)
        item.status = status
    db.session.commit()
    return jsonify({"request": _ngo(item)})
