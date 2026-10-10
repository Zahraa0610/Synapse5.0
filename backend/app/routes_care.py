from flask import Blueprint, g, jsonify

from .domain import criticality_for, iso, profile_public, shelter_public
from .extensions import db
from .http import error, login_required, parse_dt, payload
from .models import (
    CriticalityReview,
    Dependency,
    DialysisSeat,
    DialysisSession,
    PersonalSupply,
    Pregnancy,
    Profile,
    Relocation,
    Shelter,
)

care_bp = Blueprint("care", __name__)

DEPENDENCY_KINDS = ["oxygen", "electricity", "ventilator", "concentrator", "suction", "feeding", "other"]
SUPPLY_CATEGORIES = ["food", "formula", "sanitary", "specialized_nutrition", "other"]


def _own(profile):
    return profile and profile.owner_user_id == g.user.id


@care_bp.get("/profiles/<int:profile_id>/care")
@login_required()
def care(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not _own(profile) and g.user.role not in {"shelter_coordinator", "doctor", "nurse"}:
        return error("You do not have access to this care record", 403)
    if g.user.role == "shelter_coordinator" and profile.shelter_id != g.user.shelter_id:
        return error("You do not have access to this care record", 403)
    from .domain import can_view_passport

    if g.user.role in {"doctor", "nurse"} and not can_view_passport(g.user, profile):
        return error("This patient has not granted you access", 403)
    return jsonify(_care_payload(profile))


def _care_payload(profile):
    pregnancy = Pregnancy.query.filter_by(profile_id=profile.id).first()
    shelters = Shelter.query.filter_by(has_backup_power=True).order_by(Shelter.electricity_hours.desc()).all()
    return {
        "profile": profile_public(profile),
        "criticality": criticality_for(profile),
        "dependencies": [_dependency(item) for item in Dependency.query.filter_by(profile_id=profile.id).all()],
        "supplies": [_supply(item) for item in PersonalSupply.query.filter_by(profile_id=profile.id).all()],
        "dialysis": [_dialysis(item) for item in DialysisSession.query.filter_by(profile_id=profile.id).all()],
        "seats": [_seat(item) for item in DialysisSeat.query.order_by(DialysisSeat.seats_available.desc()).all()],
        "pregnancy": _pregnancy(pregnancy),
        "backup_shelters": [shelter_public(item) for item in shelters],
        "relocations": [
            {"id": item.id, "destination_shelter_id": item.destination_shelter_id, "status": item.status}
            for item in Relocation.query.filter_by(profile_id=profile.id).all()
        ],
    }


def _dependency(item):
    return {
        "id": item.id,
        "kind": item.kind,
        "device_name": item.device_name,
        "supply_description": item.supply_description,
        "supply_level_percent": item.supply_level_percent,
        "hours_remaining": item.hours_remaining,
        "notes": item.notes,
    }


def _supply(item):
    return {
        "id": item.id,
        "item_name": item.item_name,
        "category": item.category,
        "quantity_note": item.quantity_note,
        "status": item.status,
    }


def _dialysis(item):
    return {
        "id": item.id,
        "facility_name": item.facility_name,
        "scheduled_at": iso(item.scheduled_at),
        "status": item.status,
        "seat_note": item.seat_note,
    }


def _seat(item):
    return {
        "id": item.id,
        "facility_name": item.facility_name,
        "region": item.region,
        "seats_available": item.seats_available,
        "next_opening": iso(item.next_opening),
        "notes": item.notes,
    }


def _pregnancy(item):
    if not item:
        return None
    return {
        "id": item.id,
        "weeks": item.weeks,
        "due_date": iso(item.due_date),
        "risk_level": item.risk_level,
        "risk_notes": item.risk_notes,
        "next_appointment": iso(item.next_appointment),
    }


@care_bp.post("/profiles/<int:profile_id>/dependencies")
@login_required({"caregiver"})
def add_dependency(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not _own(profile):
        return error("You do not have access to this profile", 403)
    data = payload()
    kind = (data.get("kind") or "").strip()
    if kind not in DEPENDENCY_KINDS:
        return error("Choose the kind of medical dependency", 400)
    if kind == "other" and not (data.get("device_name") or "").strip():
        return error("Write the name of the device", 400)
    item = Dependency(
        profile_id=profile.id,
        kind=kind,
        device_name=(data.get("device_name") or "").strip() or None,
        supply_description=(data.get("supply_description") or "").strip() or None,
        supply_level_percent=_optional_int(data.get("supply_level_percent")),
        hours_remaining=_optional_int(data.get("hours_remaining")),
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"dependency": _dependency(item), "criticality": criticality_for(profile)}), 201


@care_bp.delete("/dependencies/<int:item_id>")
@login_required({"caregiver"})
def delete_dependency(item_id):
    item = db.session.get(Dependency, item_id)
    profile = db.session.get(Profile, item.profile_id) if item else None
    if not item or not _own(profile):
        return error("You do not have access to this record", 403)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True, "criticality": criticality_for(profile)})


@care_bp.post("/profiles/<int:profile_id>/supplies")
@login_required({"caregiver"})
def add_supply(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not _own(profile):
        return error("You do not have access to this profile", 403)
    data = payload()
    name = (data.get("item_name") or "").strip()
    category = (data.get("category") or "food").strip()
    status = (data.get("status") or "ok").strip()
    if not name or category not in SUPPLY_CATEGORIES or status not in {"ok", "low", "shortage"}:
        return error("Enter the supply, its category, and whether you still have it", 400)
    item = PersonalSupply(
        profile_id=profile.id,
        item_name=name,
        category=category,
        quantity_note=(data.get("quantity_note") or "").strip() or None,
        status=status,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"supply": _supply(item)}), 201


@care_bp.patch("/supplies/<int:item_id>")
@login_required({"caregiver"})
def update_supply(item_id):
    item = db.session.get(PersonalSupply, item_id)
    profile = db.session.get(Profile, item.profile_id) if item else None
    if not item or not _own(profile):
        return error("You do not have access to this record", 403)
    data = payload()
    if data.get("status") in {"ok", "low", "shortage"}:
        item.status = data.get("status")
    if "quantity_note" in data:
        item.quantity_note = (data.get("quantity_note") or "").strip() or None
    db.session.commit()
    return jsonify({"supply": _supply(item), "criticality": criticality_for(profile)})


@care_bp.delete("/supplies/<int:item_id>")
@login_required({"caregiver"})
def delete_supply(item_id):
    item = db.session.get(PersonalSupply, item_id)
    profile = db.session.get(Profile, item.profile_id) if item else None
    if not item or not _own(profile):
        return error("You do not have access to this record", 403)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


@care_bp.post("/profiles/<int:profile_id>/dialysis")
@login_required({"caregiver"})
def add_dialysis(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not _own(profile):
        return error("You do not have access to this profile", 403)
    data = payload()
    facility = (data.get("facility_name") or "").strip()
    when = parse_dt(data.get("scheduled_at"))
    status = (data.get("status") or "scheduled").strip()
    if not facility or not when or status not in {"scheduled", "completed", "missed"}:
        return error("Enter the dialysis center, date, and status", 400)
    item = DialysisSession(
        profile_id=profile.id,
        facility_name=facility,
        scheduled_at=when,
        status=status,
        seat_note=(data.get("seat_note") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"session": _dialysis(item), "criticality": criticality_for(profile)}), 201


@care_bp.patch("/dialysis/<int:item_id>")
@login_required({"caregiver"})
def update_dialysis(item_id):
    item = db.session.get(DialysisSession, item_id)
    profile = db.session.get(Profile, item.profile_id) if item else None
    if not item or not _own(profile):
        return error("You do not have access to this record", 403)
    status = (payload().get("status") or "").strip()
    if status not in {"scheduled", "completed", "missed"}:
        return error("Choose scheduled, completed, or missed", 400)
    item.status = status
    db.session.commit()
    return jsonify({"session": _dialysis(item), "criticality": criticality_for(profile)})


@care_bp.put("/profiles/<int:profile_id>/pregnancy")
@login_required({"caregiver"})
def save_pregnancy(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not _own(profile):
        return error("You do not have access to this profile", 403)
    data = payload()
    try:
        weeks = int(data.get("weeks"))
    except (TypeError, ValueError):
        return error("Enter the pregnancy stage in weeks", 400)
    risk = (data.get("risk_level") or "routine").strip()
    if risk not in {"routine", "high"}:
        return error("Mark the pregnancy routine or high-risk", 400)
    item = Pregnancy.query.filter_by(profile_id=profile.id).first()
    if not item:
        item = Pregnancy(profile_id=profile.id, weeks=weeks, risk_level=risk)
        db.session.add(item)
    item.weeks = weeks
    item.risk_level = risk
    item.risk_notes = (data.get("risk_notes") or "").strip() or None
    from .http import parse_date

    item.due_date = parse_date(data.get("due_date"))
    item.next_appointment = parse_dt(data.get("next_appointment"))
    db.session.commit()
    return jsonify({"pregnancy": _pregnancy(item)})


@care_bp.delete("/profiles/<int:profile_id>/pregnancy")
@login_required({"caregiver"})
def delete_pregnancy(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not _own(profile):
        return error("You do not have access to this profile", 403)
    item = Pregnancy.query.filter_by(profile_id=profile.id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return jsonify({"ok": True})


@care_bp.post("/profiles/<int:profile_id>/criticality-review")
@login_required({"shelter_coordinator", "doctor", "nurse"})
def review_criticality(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile:
        return error("Profile not found", 404)
    if g.user.role == "shelter_coordinator" and profile.shelter_id != g.user.shelter_id:
        return error("This resident is not at your shelter", 403)
    if g.user.role in {"doctor", "nurse"}:
        from .domain import can_view_passport

        if not can_view_passport(g.user, profile):
            return error("This patient has not granted you access", 403)
        if g.user.verification_status != "approved":
            return error("Your credentials are still under review", 403)
    data = payload()
    level = (data.get("classification") or "").strip()
    if level not in {"critical", "non_critical"}:
        return error("Classify the case as critical or non-critical", 400)
    review = CriticalityReview(
        profile_id=profile.id,
        reviewer_id=g.user.id,
        classification=level,
        note=(data.get("note") or "").strip() or None,
    )
    db.session.add(review)
    db.session.commit()
    return jsonify({"criticality": criticality_for(profile)})


@care_bp.post("/dialysis-seats")
@login_required({"shelter_coordinator", "ministry"})
def add_seat():
    data = payload()
    name = (data.get("facility_name") or "").strip()
    region = (data.get("region") or "").strip()
    if not name or not region:
        return error("Enter the dialysis center and region", 400)
    item = DialysisSeat(
        facility_name=name,
        region=region,
        seats_available=int(data.get("seats_available") or 0),
        next_opening=parse_dt(data.get("next_opening")),
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"seat": _seat(item)}), 201


def _optional_int(value):
    if value is None or value == "":
        return None
    return int(value)
