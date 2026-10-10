from flask import Blueprint, g, jsonify

from .domain import history_for_shelter, iso, priority_for, profile_public, roster_row, shelter_public
from .extensions import db
from .http import error, login_required, payload
from .models import (
    Complaint,
    Donation,
    InventoryItem,
    Outbreak,
    Profile,
    Relocation,
    ResourceExchange,
    Shelter,
    Task,
    User,
)

shelter_bp = Blueprint("shelter", __name__)


def _require_own_shelter():
    if not g.user.shelter_id:
        return None, error("Choose the shelter you coordinate", 400)
    shelter = db.session.get(Shelter, g.user.shelter_id)
    if not shelter:
        return None, error("That shelter is not registered", 404)
    return shelter, None


@shelter_bp.get("/shelter/board")
@login_required({"shelter_coordinator"})
def board():
    shelter, failure = _require_own_shelter()
    if failure:
        return failure
    residents = Profile.query.filter_by(shelter_id=shelter.id).order_by(Profile.full_name.asc()).all()
    inventory = InventoryItem.query.filter_by(shelter_id=shelter.id).order_by(InventoryItem.item_name.asc()).all()
    complaints = Complaint.query.filter_by(shelter_id=shelter.id).order_by(Complaint.created_at.desc()).all()
    exchanges = ResourceExchange.query.filter(
        (ResourceExchange.from_shelter_id == shelter.id) | (ResourceExchange.to_shelter_id == shelter.id)
    ).all()
    donations = Donation.query.filter_by(target_shelter_id=shelter.id).all()
    tasks = Task.query.filter_by(shelter_id=shelter.id).all()
    outbreaks = Outbreak.query.filter_by(shelter_id=shelter.id).all()
    relocations = Relocation.query.filter_by(shelter_id=shelter.id).all()
    stats = priority_for(shelter)
    public = shelter_public(shelter)
    return jsonify(
        {
            "shelter": public,
            "stats": {**stats, "percent": public["percent"], "backup_hours": shelter.electricity_hours},
            "residents": [roster_row(person) for person in residents],
            "inventory": [_inventory(item) for item in inventory],
            "complaints": [_complaint_brief(item) for item in complaints],
            "exchanges": [_exchange(item) for item in exchanges],
            "donations": [_donation_brief(item) for item in donations],
            "tasks": [_task_brief(item) for item in tasks],
            "outbreaks": [_outbreak(item) for item in outbreaks],
            "relocations": [_relocation(item) for item in relocations],
            "history": history_for_shelter(shelter.id),
        }
    )


def _inventory(item):
    return {
        "id": item.id,
        "item_name": item.item_name,
        "category": item.category,
        "quantity": item.quantity,
        "unit": item.unit,
        "status": item.status,
        "is_equipment": item.is_equipment,
        "is_specialized": item.is_specialized,
    }


def _complaint_brief(item):
    return {
        "id": item.id,
        "category": item.category,
        "description": item.description,
        "source": item.source,
        "status": item.status,
        "region": item.region,
        "created_at": iso(item.created_at),
    }


def _exchange(item):
    source = db.session.get(Shelter, item.from_shelter_id)
    dest = db.session.get(Shelter, item.to_shelter_id)
    return {
        "id": item.id,
        "from_shelter_id": item.from_shelter_id,
        "from_shelter_name": source.name if source else None,
        "to_shelter_id": item.to_shelter_id,
        "to_shelter_name": dest.name if dest else None,
        "item_name": item.item_name,
        "quantity": item.quantity,
        "status": item.status,
        "needs_volunteer": item.needs_volunteer,
    }


def _donation_brief(item):
    donor = db.session.get(User, item.donor_id)
    return {
        "id": item.id,
        "donor_name": donor.full_name if donor else None,
        "kind": item.kind,
        "amount": item.amount,
        "currency": item.currency,
        "item_description": item.item_description,
        "status": item.status,
        "cause_label": item.cause_label,
    }


def _task_brief(item):
    assignee = db.session.get(User, item.assignee_user_id) if item.assignee_user_id else None
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "status": item.status,
        "location": item.location,
        "scheduled_at": iso(item.scheduled_at),
        "assignee_name": assignee.full_name if assignee else None,
    }


def _outbreak(item):
    shelter = db.session.get(Shelter, item.shelter_id)
    return {
        "id": item.id,
        "shelter_id": item.shelter_id,
        "shelter_name": shelter.name if shelter else None,
        "region": shelter.region if shelter else None,
        "suspected_illness": item.suspected_illness,
        "case_count": item.case_count,
        "notes": item.notes,
        "status": item.status,
        "created_at": iso(item.created_at),
        "disclaimer": "This flags a cluster for public health staff. It does not declare an outbreak.",
    }


def _relocation(item):
    dest = db.session.get(Shelter, item.destination_shelter_id) if item.destination_shelter_id else None
    profile = db.session.get(Profile, item.profile_id) if item.profile_id else None
    return {
        "id": item.id,
        "profile_id": item.profile_id,
        "who": profile.full_name if profile else None,
        "destination_shelter_id": item.destination_shelter_id,
        "destination_name": dest.name if dest else None,
        "reason": item.reason,
        "status": item.status,
        "created_at": iso(item.created_at),
    }


@shelter_bp.patch("/shelters/<int:shelter_id>")
@login_required({"shelter_coordinator"})
def update_shelter(shelter_id):
    if g.user.shelter_id != shelter_id:
        return error("You coordinate a different shelter", 403)
    shelter = db.session.get(Shelter, shelter_id)
    if not shelter:
        return error("Shelter not found", 404)
    data = payload()
    for field in ("capacity", "occupancy", "accessible_spaces", "electricity_hours"):
        if data.get(field) is not None and data.get(field) != "":
            setattr(shelter, field, int(data.get(field)))
    if "accessible" in data:
        shelter.accessible = str(data.get("accessible")).lower() in {"1", "true", "yes", "on"}
    if "has_backup_power" in data:
        shelter.has_backup_power = str(data.get("has_backup_power")).lower() in {"1", "true", "yes", "on"}
    if "notes" in data:
        shelter.notes = (data.get("notes") or "").strip() or None
    db.session.commit()
    return jsonify({"shelter": shelter_public(shelter)})


@shelter_bp.post("/shelters/<int:shelter_id>/inventory")
@login_required({"shelter_coordinator"})
def add_inventory(shelter_id):
    if g.user.shelter_id != shelter_id:
        return error("You coordinate a different shelter", 403)
    data = payload()
    name = (data.get("item_name") or "").strip()
    status = (data.get("status") or "available").strip()
    if not name or status not in {"available", "low", "shortage"}:
        return error("Enter the item and whether it is available, low, or short", 400)
    item = InventoryItem(
        shelter_id=shelter_id,
        item_name=name,
        category=(data.get("category") or "supplies").strip(),
        quantity=int(data.get("quantity") or 0),
        unit=(data.get("unit") or "units").strip(),
        status=status,
        is_equipment=str(data.get("is_equipment", "")).lower() in {"1", "true", "yes", "on"},
        is_specialized=str(data.get("is_specialized", "")).lower() in {"1", "true", "yes", "on"},
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"item": _inventory(item)}), 201


@shelter_bp.patch("/inventory/<int:item_id>")
@login_required({"shelter_coordinator"})
def update_inventory(item_id):
    item = db.session.get(InventoryItem, item_id)
    if not item or item.shelter_id != g.user.shelter_id:
        return error("You do not have access to this item", 403)
    data = payload()
    if data.get("status") in {"available", "low", "shortage"}:
        item.status = data.get("status")
    if data.get("quantity") is not None and data.get("quantity") != "":
        item.quantity = int(data.get("quantity"))
    db.session.commit()
    return jsonify({"item": _inventory(item)})


@shelter_bp.delete("/inventory/<int:item_id>")
@login_required({"shelter_coordinator"})
def delete_inventory(item_id):
    item = db.session.get(InventoryItem, item_id)
    if not item or item.shelter_id != g.user.shelter_id:
        return error("You do not have access to this item", 403)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


@shelter_bp.post("/exchanges")
@login_required({"shelter_coordinator"})
def create_exchange():
    shelter, failure = _require_own_shelter()
    if failure:
        return failure
    data = payload()
    dest = db.session.get(Shelter, int(data.get("to_shelter_id") or 0))
    name = (data.get("item_name") or "").strip()
    if not dest or dest.id == shelter.id or not name:
        return error("Choose another shelter and the item to move", 400)
    try:
        quantity = int(data.get("quantity") or 0)
    except ValueError:
        return error("Enter a quantity", 400)
    if quantity < 1:
        return error("Enter a quantity", 400)
    needs_volunteer = str(data.get("needs_volunteer", "")).lower() in {"1", "true", "yes", "on"}
    item = ResourceExchange(
        from_shelter_id=shelter.id,
        to_shelter_id=dest.id,
        item_name=name,
        quantity=quantity,
        needs_volunteer=needs_volunteer,
        created_by=g.user.id,
        status="proposed",
    )
    db.session.add(item)
    db.session.flush()
    if needs_volunteer:
        db.session.add(
            Task(
                kind="delivery",
                title=f"Carry {name} to {dest.name}",
                details=f"{quantity} {name} from {shelter.name}.",
                location=f"{shelter.name} to {dest.name}",
                shelter_id=dest.id,
                exchange_id=item.id,
                status="open",
            )
        )
    db.session.commit()
    return jsonify({"exchange": _exchange(item)}), 201


@shelter_bp.patch("/exchanges/<int:item_id>")
@login_required({"shelter_coordinator"})
def update_exchange(item_id):
    item = db.session.get(ResourceExchange, item_id)
    if not item or g.user.shelter_id not in {item.from_shelter_id, item.to_shelter_id}:
        return error("You do not have access to this exchange", 403)
    status = (payload().get("status") or "").strip()
    if status not in {"proposed", "accepted", "in_transit", "completed"}:
        return error("Choose a status", 400)
    item.status = status
    db.session.commit()
    return jsonify({"exchange": _exchange(item)})


@shelter_bp.post("/relocations")
@login_required({"shelter_coordinator", "caregiver"})
def create_relocation():
    data = payload()
    profile = db.session.get(Profile, int(data.get("profile_id") or 0))
    if not profile:
        return error("Choose a person", 400)
    if g.user.role == "caregiver" and profile.owner_user_id != g.user.id:
        return error("You do not have access to this profile", 403)
    if g.user.role == "shelter_coordinator" and profile.shelter_id != g.user.shelter_id:
        return error("This resident is not at your shelter", 403)
    destination_id = data.get("destination_shelter_id") or None
    destination = db.session.get(Shelter, int(destination_id)) if destination_id else None
    reason = (data.get("reason") or "").strip()
    if not reason:
        return error("Describe why a move is needed", 400)
    origin_id = profile.shelter_id or g.user.shelter_id
    if not origin_id:
        return error("This profile is not linked to a shelter yet", 400)
    item = Relocation(
        shelter_id=origin_id,
        destination_shelter_id=destination.id if destination else None,
        profile_id=profile.id,
        reason=reason,
        created_by=g.user.id,
        status="requested",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"relocation": _relocation(item)}), 201


@shelter_bp.patch("/relocations/<int:item_id>")
@login_required({"shelter_coordinator", "ministry"})
def update_relocation(item_id):
    item = db.session.get(Relocation, item_id)
    if not item:
        return error("Request not found", 404)
    if g.user.role == "shelter_coordinator" and item.shelter_id != g.user.shelter_id:
        return error("This request is for another shelter", 403)
    status = (payload().get("status") or "").strip()
    if status not in {"requested", "escalated", "resolved"}:
        return error("Choose a status", 400)
    item.status = status
    db.session.commit()
    return jsonify({"relocation": _relocation(item)})


@shelter_bp.post("/outbreaks")
@login_required({"shelter_coordinator"})
def report_outbreak():
    shelter, failure = _require_own_shelter()
    if failure:
        return failure
    data = payload()
    illness = (data.get("suspected_illness") or "").strip()
    if not illness:
        return error("Name the suspected illness", 400)
    item = Outbreak(
        shelter_id=shelter.id,
        suspected_illness=illness,
        case_count=int(data.get("case_count") or 1),
        notes=(data.get("notes") or "").strip() or None,
        created_by=g.user.id,
        status="reported",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"outbreak": _outbreak(item)}), 201


@shelter_bp.patch("/outbreaks/<int:item_id>")
@login_required({"ministry"}, approved=True)
def review_outbreak(item_id):
    item = db.session.get(Outbreak, item_id)
    if not item:
        return error("Report not found", 404)
    status = (payload().get("status") or "").strip()
    if status not in {"reported", "under_review", "investigating"}:
        return error("Choose a review status", 400)
    item.status = status
    db.session.commit()
    return jsonify({"outbreak": _outbreak(item)})


@shelter_bp.get("/profiles/<int:profile_id>/roster")
@login_required({"shelter_coordinator"})
def resident(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile or profile.shelter_id != g.user.shelter_id:
        return error("This resident is not at your shelter", 404)
    return jsonify({"resident": roster_row(profile), "limited": True, "passport": None})
