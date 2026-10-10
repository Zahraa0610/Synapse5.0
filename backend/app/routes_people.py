from flask import Blueprint, g, jsonify, request

from .domain import distribution, iso, opportunities, shelter_public
from .extensions import db
from .http import error, login_required, parse_dt, payload, save_upload
from .models import (
    Announcement,
    Appointment,
    Complaint,
    Donation,
    Profile,
    ResourceExchange,
    Shelter,
    SupportFlag,
    Task,
    TransportRequest,
    User,
)

people_bp = Blueprint("people", __name__)


def _profile_name(profile_id):
    profile = db.session.get(Profile, profile_id) if profile_id else None
    return profile.full_name if profile else None


@people_bp.get("/requests/mine")
@login_required()
def my_requests():
    profiles = _visible_profiles()
    ids = [profile.id for profile in profiles]
    transports = []
    appointments = []
    if ids:
        transports = TransportRequest.query.filter(TransportRequest.profile_id.in_(ids)).all()
        appointments = Appointment.query.filter(Appointment.profile_id.in_(ids)).all()
    if g.user.role in {"ngo", "volunteer"}:
        transports = TransportRequest.query.order_by(TransportRequest.created_at.desc()).all()
    flags = _visible_flags()
    complaints = _visible_complaints()
    linked = {item.appointment_id for item in transports if item.appointment_id and item.status in {"requested", "accepted", "completed"}}
    at_risk = []
    for appointment in appointments:
        if appointment.scheduled_at and appointment.id not in linked:
            at_risk.append(appointment.id)
    return jsonify(
        {
            "profiles": [{"id": profile.id, "full_name": profile.full_name} for profile in profiles],
            "transports": [_transport(item) for item in transports],
            "appointments": [_appointment(item) for item in appointments],
            "at_risk_appointment_ids": at_risk,
            "flags": [_flag(item) for item in flags],
            "complaints": [_complaint(item) for item in complaints],
        }
    )


def _visible_profiles():
    if g.user.role == "caregiver":
        return Profile.query.filter_by(owner_user_id=g.user.id).all()
    if g.user.role == "shelter_coordinator" and g.user.shelter_id:
        return Profile.query.filter_by(shelter_id=g.user.shelter_id).all()
    return []


def _visible_flags():
    if g.user.role == "caregiver":
        ids = [profile.id for profile in Profile.query.filter_by(owner_user_id=g.user.id).all()]
        if not ids:
            return []
        return SupportFlag.query.filter(SupportFlag.profile_id.in_(ids)).all()
    if g.user.role == "volunteer":
        return SupportFlag.query.filter_by(flagged_by=g.user.id).all()
    if g.user.role == "shelter_coordinator" and g.user.shelter_id:
        ids = [profile.id for profile in Profile.query.filter_by(shelter_id=g.user.shelter_id).all()]
        return SupportFlag.query.filter(
            (SupportFlag.shelter_id == g.user.shelter_id) | (SupportFlag.profile_id.in_(ids or [0]))
        ).all()
    return []


def _visible_complaints():
    if g.user.role == "ministry":
        return Complaint.query.order_by(Complaint.created_at.desc()).all()
    if g.user.role == "shelter_coordinator" and g.user.shelter_id:
        return Complaint.query.filter_by(shelter_id=g.user.shelter_id).order_by(Complaint.created_at.desc()).all()
    return Complaint.query.filter_by(submitted_by=g.user.id).order_by(Complaint.created_at.desc()).all()


def _transport(item):
    provider = db.session.get(User, item.provider_user_id) if item.provider_user_id else None
    return {
        "id": item.id,
        "profile_id": item.profile_id,
        "who": _profile_name(item.profile_id),
        "destination": item.destination,
        "destination_type": item.destination_type,
        "wheelchair_required": item.wheelchair_required,
        "appointment_id": item.appointment_id,
        "status": item.status,
        "provider_name": provider.full_name if provider else None,
        "notes": item.notes,
        "created_at": iso(item.created_at),
    }


def _appointment(item):
    return {
        "id": item.id,
        "profile_id": item.profile_id,
        "who": _profile_name(item.profile_id),
        "facility": item.facility,
        "scheduled_at": iso(item.scheduled_at),
        "kind": item.kind,
        "notes": item.notes,
    }


def _flag(item):
    shelter = db.session.get(Shelter, item.shelter_id) if item.shelter_id else None
    return {
        "id": item.id,
        "profile_id": item.profile_id,
        "who": item.person_description or _profile_name(item.profile_id),
        "registered_name": _profile_name(item.profile_id),
        "signs": item.signs.split(" · ") if item.signs else [],
        "shelter_name": shelter.name if shelter else None,
        "reason": item.reason,
        "includes_bullying": item.includes_bullying,
        "status": item.status,
        "created_at": iso(item.created_at),
    }


def _complaint(item):
    shelter = db.session.get(Shelter, item.shelter_id) if item.shelter_id else None
    return {
        "id": item.id,
        "shelter_id": item.shelter_id,
        "shelter_name": shelter.name if shelter else None,
        "region": item.region,
        "category": item.category,
        "description": item.description,
        "source": item.source,
        "status": item.status,
        "has_photo": bool(item.photo_stored_name),
        "created_at": iso(item.created_at),
        "resolved_at": iso(item.resolved_at),
    }


@people_bp.post("/appointments")
@login_required({"caregiver"})
def add_appointment():
    data = payload()
    profile = db.session.get(Profile, int(data.get("profile_id") or 0))
    if not profile or profile.owner_user_id != g.user.id:
        return error("Choose one of your profiles", 400)
    facility = (data.get("facility") or "").strip()
    when = parse_dt(data.get("scheduled_at"))
    if not facility or not when:
        return error("Enter the facility and the appointment time", 400)
    item = Appointment(
        profile_id=profile.id,
        facility=facility,
        scheduled_at=when,
        kind=(data.get("kind") or "clinic").strip(),
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"appointment": _appointment(item)}), 201


@people_bp.post("/transport")
@login_required({"caregiver", "shelter_coordinator"})
def add_transport():
    data = payload()
    profile = db.session.get(Profile, int(data.get("profile_id") or 0))
    if not profile:
        return error("Choose a person", 400)
    if g.user.role == "caregiver" and profile.owner_user_id != g.user.id:
        return error("You do not have access to this profile", 403)
    if g.user.role == "shelter_coordinator" and profile.shelter_id != g.user.shelter_id:
        return error("This resident is not at your shelter", 403)
    destination = (data.get("destination") or "").strip()
    destination_type = (data.get("destination_type") or "hospital").strip()
    if not destination or destination_type not in {"hospital", "dialysis", "clinic", "other"}:
        return error("Enter where the person needs to go", 400)
    appointment_id = data.get("appointment_id") or None
    if appointment_id:
        appointment = db.session.get(Appointment, int(appointment_id))
        if not appointment or appointment.profile_id != profile.id:
            return error("That appointment does not match this person", 400)
        appointment_id = appointment.id
    item = TransportRequest(
        profile_id=profile.id,
        requester_id=g.user.id,
        destination=destination,
        destination_type=destination_type,
        wheelchair_required=str(data.get("wheelchair_required", "")).lower() in {"1", "true", "yes", "on"},
        appointment_id=appointment_id,
        notes=(data.get("notes") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"transport": _transport(item)}), 201


@people_bp.patch("/transport/<int:item_id>")
@login_required()
def update_transport(item_id):
    item = db.session.get(TransportRequest, item_id)
    if not item:
        return error("Request not found", 404)
    status = (payload().get("status") or "").strip()
    if status not in {"accepted", "completed", "cancelled"}:
        return error("Choose a status", 400)
    # Volunteers who said at sign-up that they can drive can take ride requests.
    provider = g.user.role == "ngo" or (g.user.role == "volunteer" and g.user.offers_driving)
    owner = _owns_transport(item)
    if status in {"accepted", "completed"} and not provider and g.user.role != "shelter_coordinator":
        return error("A transport provider accepts this request", 403)
    if status == "cancelled" and not owner and not provider:
        return error("You do not have access to this request", 403)
    if status == "accepted":
        item.provider_user_id = g.user.id
    item.status = status
    db.session.commit()
    return jsonify({"transport": _transport(item)})


def _owns_transport(item):
    profile = db.session.get(Profile, item.profile_id)
    return profile and profile.owner_user_id == g.user.id


@people_bp.get("/roster")
@login_required({"volunteer", "shelter_coordinator", "caregiver"})
def roster():
    query = Profile.query
    if g.user.role == "shelter_coordinator":
        query = query.filter_by(shelter_id=g.user.shelter_id)
    elif g.user.role == "caregiver":
        query = query.filter_by(owner_user_id=g.user.id)
    q = (request.args.get("q") or "").strip()
    if q:
        query = query.filter(Profile.full_name.ilike(f"%{q}%"))
    rows = []
    for profile in query.order_by(Profile.full_name.asc()).limit(30).all():
        shelter = db.session.get(Shelter, profile.shelter_id) if profile.shelter_id else None
        rows.append(
            {
                "id": profile.id,
                "full_name": profile.full_name,
                "shelter_name": shelter.name if shelter else None,
                "shelter_id": profile.shelter_id,
            }
        )
    return jsonify({"people": rows})


@people_bp.post("/support-flags")
@login_required({"caregiver", "volunteer", "shelter_coordinator"})
def add_flag():
    """Report a case that needs mental health support.
    The person is described in words; linking a registered profile is optional."""
    data = payload()
    profile = None
    if data.get("profile_id"):
        profile = db.session.get(Profile, int(data.get("profile_id")))
        if not profile:
            return error("That person is not registered", 400)
        if g.user.role == "caregiver" and profile.owner_user_id != g.user.id:
            return error("You can flag people on your own profiles", 403)
        if g.user.role == "shelter_coordinator" and profile.shelter_id != g.user.shelter_id:
            return error("This resident is not at your shelter", 403)
    person = (data.get("person_description") or "").strip()
    if not profile and not person:
        return error("Say who needs support", 400)
    reason = (data.get("reason") or "").strip()
    if not reason:
        return error("Write a short description of the case", 400)
    signs = data.get("signs") or []
    if isinstance(signs, str):
        signs = [part.strip() for part in signs.split("·") if part.strip()]
    shelter_id = data.get("shelter_id") or (profile.shelter_id if profile else None) or g.user.shelter_id
    item = SupportFlag(
        profile_id=profile.id if profile else None,
        person_description=person or None,
        shelter_id=int(shelter_id) if shelter_id else None,
        signs=" · ".join(signs) or None,
        flagged_by=g.user.id,
        reason=reason,
        includes_bullying=str(data.get("includes_bullying", "")).lower() in {"1", "true", "yes", "on"}
        or any("ullying" in sign for sign in signs),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"flag": _flag(item)}), 201


@people_bp.patch("/support-flags/<int:item_id>")
@login_required({"shelter_coordinator", "caregiver"})
def update_flag(item_id):
    item = db.session.get(SupportFlag, item_id)
    if not item:
        return error("Flag not found", 404)
    status = (payload().get("status") or "").strip()
    if status not in {"open", "acknowledged", "closed"}:
        return error("Choose a status", 400)
    item.status = status
    db.session.commit()
    return jsonify({"flag": _flag(item)})


@people_bp.post("/complaints")
@login_required({"caregiver", "volunteer", "shelter_coordinator"})
def add_complaint():
    data = payload()
    category = (data.get("category") or "").strip()
    description = (data.get("description") or "").strip()
    source = (data.get("source") or "direct").strip()
    sources = {"direct", "email", "phone", "message", "photo", "note", "in_person"}
    if not category or not description or source not in sources:
        return error("Enter the issue, how it reached you, and what happened", 400)
    shelter_id = data.get("shelter_id") or g.user.shelter_id
    shelter = db.session.get(Shelter, int(shelter_id)) if shelter_id else None
    if g.user.role == "shelter_coordinator":
        shelter = db.session.get(Shelter, g.user.shelter_id) if g.user.shelter_id else None
    item = Complaint(
        shelter_id=shelter.id if shelter else None,
        region=shelter.region if shelter else (data.get("region") or "").strip() or None,
        category=category,
        description=description,
        source=source,
        submitted_by=g.user.id,
    )
    photo = request.files.get("photo") if request.files else None
    if photo:
        try:
            saved = save_upload(photo)
        except ValueError as exc:
            return error(str(exc), 400)
        if saved:
            item.photo_stored_name = saved["stored_name"]
    db.session.add(item)
    db.session.commit()
    return jsonify({"complaint": _complaint(item)}), 201


@people_bp.patch("/complaints/<int:item_id>")
@login_required({"shelter_coordinator", "ministry"})
def update_complaint(item_id):
    if g.user.role == "ministry" and g.user.verification_status != "approved":
        return error("This account is still under review", 403)
    item = db.session.get(Complaint, item_id)
    if not item:
        return error("Complaint not found", 404)
    if g.user.role == "shelter_coordinator" and item.shelter_id != g.user.shelter_id:
        return error("This complaint is for another shelter", 403)
    status = (payload().get("status") or "").strip()
    if status not in {"received", "under_review", "being_addressed", "resolved"}:
        return error("Choose a complaint status", 400)
    item.status = status
    if status == "resolved":
        from datetime import datetime, timezone

        item.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"complaint": _complaint(item)})


@people_bp.get("/volunteer/board")
@login_required({"volunteer"})
def volunteer_board():
    tasks = Task.query.order_by(Task.scheduled_at.asc()).all()
    return jsonify({"tasks": [_task(item) for item in tasks], "announcements": [_announcement(item) for item in notices_for(g.user)]})


def _task(item):
    assignee = db.session.get(User, item.assignee_user_id) if item.assignee_user_id else None
    shelter = db.session.get(Shelter, item.shelter_id) if item.shelter_id else None
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "details": item.details,
        "location": item.location,
        "scheduled_at": iso(item.scheduled_at),
        "shelter_name": shelter.name if shelter else None,
        "status": item.status,
        "assignee_name": assignee.full_name if assignee else None,
        "assignee_user_id": item.assignee_user_id,
        "exchange_id": item.exchange_id,
        "mine": item.assignee_user_id == g.user.id,
    }


NOTICE_KINDS = {"doctor_visit", "free_healthcare_day", "screening", "vaccination", "other"}
POSTER_LABELS = {"ministry": "Ministry of Public Health", "doctor": "Doctor", "nurse": "Nurse", "shelter_coordinator": "Shelter coordinator"}


def _announcement(item):
    shelter = db.session.get(Shelter, item.shelter_id) if item.shelter_id else None
    author = db.session.get(User, item.created_by) if item.created_by else None
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "location": item.location,
        "starts_at": iso(item.starts_at),
        "ends_at": iso(item.ends_at),
        "details": item.details,
        "shelter_id": item.shelter_id,
        "shelter_name": shelter.name if shelter else None,
        "region": item.region or (shelter.region if shelter else None),
        "posted_by": author.full_name if author else None,
        "posted_by_role": POSTER_LABELS.get(author.role) if author else None,
        "mine": bool(author and author.id == g.user.id),
    }


def notices_for(user, limit=None):
    """Upcoming notices this person should see: everything national, plus their
    region and their shelter. People without a shelter see every notice."""
    from datetime import datetime, timedelta, timezone

    from .domain import aware

    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
    shelter = db.session.get(Shelter, user.shelter_id) if user.shelter_id else None
    rows = []
    for item in Announcement.query.order_by(Announcement.starts_at.asc()).all():
        last = item.ends_at or item.starts_at
        if last and aware(last) < cutoff:
            continue  # already over
        if user.role == "caregiver" and shelter:
            item_region = item.region or (db.session.get(Shelter, item.shelter_id).region if item.shelter_id else None)
            if item.shelter_id and item.shelter_id != shelter.id:
                continue
            if not item.shelter_id and item_region and item_region != shelter.region:
                continue
        rows.append(item)
    return rows[:limit] if limit else rows


@people_bp.post("/tasks")
@login_required({"shelter_coordinator", "ministry"})
def add_task():
    data = payload()
    title = (data.get("title") or "").strip()
    kind = (data.get("kind") or "other").strip()
    if not title or kind not in {"delivery", "companion", "other"}:
        return error("Enter the task", 400)
    item = Task(
        kind=kind,
        title=title,
        details=(data.get("details") or "").strip() or None,
        location=(data.get("location") or "").strip() or None,
        scheduled_at=parse_dt(data.get("scheduled_at")),
        shelter_id=g.user.shelter_id or data.get("shelter_id"),
        status="open",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"task": _task(item)}), 201


@people_bp.post("/tasks/<int:item_id>/respond")
@login_required({"volunteer"})
def respond_task(item_id):
    item = db.session.get(Task, item_id)
    if not item:
        return error("Task not found", 404)
    action = (payload().get("action") or "").strip()
    if action == "accept":
        if item.status == "accepted" and item.assignee_user_id != g.user.id:
            return error("Another volunteer already accepted this task", 409)
        item.status = "accepted"
        item.assignee_user_id = g.user.id
    elif action == "decline":
        if item.assignee_user_id and item.assignee_user_id != g.user.id:
            return error("This task is assigned to someone else", 403)
        item.status = "open"
        item.assignee_user_id = None
    elif action == "complete":
        if item.assignee_user_id != g.user.id:
            return error("Accept the task before completing it", 403)
        item.status = "completed"
        if item.exchange_id:
            exchange = db.session.get(ResourceExchange, item.exchange_id)
            if exchange:
                exchange.status = "completed"
    else:
        return error("Accept, decline, or complete the task", 400)
    db.session.commit()
    return jsonify({"task": _task(item)})


@people_bp.get("/announcements")
@login_required()
def list_announcements():
    """Upcoming notices for this person, plus the ones they posted themselves."""
    mine = Announcement.query.filter_by(created_by=g.user.id).order_by(Announcement.starts_at.desc()).all()
    return jsonify(
        {
            "announcements": [_announcement(item) for item in notices_for(g.user)],
            "mine": [_announcement(item) for item in mine],
        }
    )


@people_bp.post("/announcements")
@login_required({"shelter_coordinator", "doctor", "nurse", "ministry"})
def add_announcement():
    """Doctors, nurses, shelter coordinators and the Ministry post events (free check-ups,
    screening days, vaccination campaigns...). They show up for everyone concerned."""
    if g.user.role in {"doctor", "nurse", "ministry"} and g.user.verification_status != "approved":
        return error("Your account is still under review", 403)
    data = payload()
    kind = (data.get("kind") or "").strip()
    title = (data.get("title") or "").strip()
    if kind not in NOTICE_KINDS or not title:
        return error("Choose the type of event and give it a title", 400)
    starts_at = parse_dt(data.get("starts_at"))
    if not starts_at:
        return error("Choose when the event starts", 400)
    ends_at = parse_dt(data.get("ends_at"))
    if ends_at and ends_at < starts_at:
        return error("The end time is before the start time", 400)

    shelter = None
    if g.user.role == "shelter_coordinator":
        shelter = db.session.get(Shelter, g.user.shelter_id) if g.user.shelter_id else None
    elif data.get("shelter_id"):
        shelter = db.session.get(Shelter, int(data.get("shelter_id")))
        if not shelter:
            return error("That shelter is not registered", 400)
    region = (data.get("region") or "").strip() or None
    if region and region not in REGIONS:
        return error("Choose a region", 400)
    item = Announcement(
        kind=kind,
        title=title,
        location=(data.get("location") or "").strip() or None,
        starts_at=starts_at,
        ends_at=ends_at,
        details=(data.get("details") or "").strip() or None,
        shelter_id=shelter.id if shelter else None,
        region=shelter.region if shelter else region,
        created_by=g.user.id,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"announcement": _announcement(item)}), 201


@people_bp.delete("/announcements/<int:item_id>")
@login_required({"shelter_coordinator", "doctor", "nurse", "ministry"})
def delete_announcement(item_id):
    item = db.session.get(Announcement, item_id)
    if not item:
        return error("Notice not found", 404)
    if item.created_by != g.user.id and g.user.role != "ministry":
        return error("You can remove notices you posted", 403)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


@people_bp.get("/donor/board")
@login_required({"donor", "ministry", "shelter_coordinator"})
def donor_board():
    items = opportunities()
    if g.user.role == "donor":
        donations = Donation.query.filter_by(donor_id=g.user.id).order_by(Donation.created_at.desc()).all()
    elif g.user.role == "shelter_coordinator":
        donations = Donation.query.filter_by(target_shelter_id=g.user.shelter_id).all()
    else:
        donations = Donation.query.order_by(Donation.created_at.desc()).all()
    return jsonify(
        {
            "opportunities": items,
            "recommendation": next((item for item in items if item["recommended"]), None),
            "donations": [_donation(item) for item in donations],
            "note": "You choose the recipient. Ma'ak does not assign a gift on its own.",
        }
    )


def _donation(item):
    shelter = db.session.get(Shelter, item.target_shelter_id) if item.target_shelter_id else None
    donor = db.session.get(User, item.donor_id)
    return {
        "id": item.id,
        "donor_name": donor.full_name if donor else None,
        "kind": item.kind,
        "amount": item.amount,
        "currency": item.currency,
        "item_description": item.item_description,
        "target_type": item.target_type,
        "target_shelter_id": item.target_shelter_id,
        "shelter_name": shelter.name if shelter else None,
        "region": shelter.region if shelter else None,
        "target_profile_id": item.target_profile_id,
        "cause_label": item.cause_label,
        "donation_request_id": item.donation_request_id,
        "status": item.status,
        "from_recommendation": item.from_recommendation,
        "created_at": iso(item.created_at),
    }


@people_bp.post("/donations")
@login_required({"donor"})
def give():
    data = payload()
    kind = (data.get("kind") or "").strip()
    target_type = (data.get("target_type") or "").strip()
    if kind not in {"money", "physical"} or target_type not in {"shelter", "case", "cause", "request"}:
        return error("Choose money or supplies, and a recipient", 400)
    shelter_id = data.get("target_shelter_id") or None
    profile_id = data.get("target_profile_id") or None
    cause = (data.get("cause_label") or "").strip() or None
    request_id = data.get("donation_request_id") or None
    if target_type == "request":
        from .models import DonationRequest

        request_row = db.session.get(DonationRequest, int(request_id or 0))
        if not request_row or request_row.status != "open":
            return error("This request is no longer open", 400)
        profile_id = request_row.profile_id
        cause = cause or f"Family in {request_row.area or request_row.region}"
    if not shelter_id and not profile_id and not cause and not request_id:
        return error("Choose a recipient before giving", 400)
    if shelter_id and not db.session.get(Shelter, int(shelter_id)):
        return error("That shelter is not registered", 400)
    amount = None
    if kind == "money":
        try:
            amount = float(data.get("amount"))
        except (TypeError, ValueError):
            return error("Enter an amount", 400)
        if amount <= 0:
            return error("Enter an amount", 400)
    description = (data.get("item_description") or "").strip() or None
    if kind == "physical" and not description:
        return error("Describe the supplies", 400)
    item = Donation(
        donor_id=g.user.id,
        kind=kind,
        amount=amount,
        currency=(data.get("currency") or "USD").strip() or "USD",
        item_description=description,
        target_type=target_type,
        target_shelter_id=int(shelter_id) if shelter_id else None,
        target_profile_id=int(profile_id) if profile_id else None,
        cause_label=cause,
        from_recommendation=str(data.get("from_recommendation", "")).lower() in {"1", "true", "yes", "on"},
        donation_request_id=int(request_id) if target_type == "request" else None,
        status="pledged",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"donation": _donation(item)}), 201


@people_bp.patch("/donations/<int:item_id>")
@login_required({"shelter_coordinator", "ministry"})
def update_donation(item_id):
    if g.user.role == "ministry" and g.user.verification_status != "approved":
        return error("This account is still under review", 403)
    item = db.session.get(Donation, item_id)
    if not item:
        return error("Donation not found", 404)
    if g.user.role == "shelter_coordinator" and item.target_shelter_id != g.user.shelter_id:
        return error("This gift is for another shelter", 403)
    status = (payload().get("status") or "").strip()
    if status not in {"pledged", "received", "allocated", "distributed"}:
        return error("Choose a distribution status", 400)
    item.status = status
    item.coordinator_id = g.user.id
    db.session.commit()
    return jsonify({"donation": _donation(item)})


@people_bp.get("/distribution")
@login_required({"ministry"}, approved=True)
def distribution_view():
    return jsonify({"rows": distribution(), "note": "Compare gifts already recorded with shortages shelters still report."})


# ---------------------------------------------------------------------------
# Donation requests from displaced families outside the shelters
# ---------------------------------------------------------------------------

LIVING_SITUATIONS = {"tent", "renting", "host_family", "unfinished_building", "car", "other"}
REQUEST_CATEGORIES = {"food", "medicine", "baby", "hygiene", "blankets", "clothes", "rent", "other"}
REGIONS = {"Beirut", "Mount Lebanon", "North", "Akkar", "Bekaa", "Baalbek-Hermel", "South", "Nabatieh"}


def _donation_request(item, include_gifts=False):
    data = {
        "id": item.id,
        "profile_id": item.profile_id,
        "who": _profile_name(item.profile_id),
        "living_situation": item.living_situation,
        "region": item.region,
        "area": item.area,
        "category": item.category,
        "description": item.description,
        "people_count": item.people_count,
        "status": item.status,
        "created_at": iso(item.created_at),
    }
    if include_gifts:
        data["donations"] = [_donation(gift) for gift in Donation.query.filter_by(donation_request_id=item.id).all()]
    return data


@people_bp.post("/donation-requests")
@login_required({"caregiver"})
def add_donation_request():
    from .models import DonationRequest

    data = payload()
    situation = (data.get("living_situation") or "").strip()
    category = (data.get("category") or "").strip()
    region = (data.get("region") or "").strip()
    description = (data.get("description") or "").strip()
    if situation not in LIVING_SITUATIONS:
        return error("Choose where you are staying", 400)
    if region not in REGIONS:
        return error("Choose your region", 400)
    if category not in REQUEST_CATEGORIES or not description:
        return error("Choose what you need and describe it", 400)
    profile_id = data.get("profile_id") or None
    if profile_id:
        profile = db.session.get(Profile, int(profile_id))
        if not profile or profile.owner_user_id != g.user.id:
            return error("Choose one of your family profiles", 400)
    people = str(data.get("people_count") or "").strip()
    item = DonationRequest(
        requester_user_id=g.user.id,
        profile_id=int(profile_id) if profile_id else None,
        living_situation=situation,
        region=region,
        area=(data.get("area") or "").strip() or None,
        category=category,
        description=description,
        people_count=int(people) if people.isdigit() else None,
        status="open",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"request": _donation_request(item, include_gifts=True)}), 201


@people_bp.get("/donation-requests/mine")
@login_required({"caregiver"})
def my_donation_requests():
    from .models import DonationRequest

    rows = DonationRequest.query.filter_by(requester_user_id=g.user.id).order_by(DonationRequest.created_at.desc()).all()
    return jsonify({"requests": [_donation_request(item, include_gifts=True) for item in rows]})


@people_bp.patch("/donation-requests/<int:item_id>")
@login_required({"caregiver"})
def update_donation_request(item_id):
    from .models import DonationRequest

    item = db.session.get(DonationRequest, item_id)
    if not item or item.requester_user_id != g.user.id:
        return error("Request not found", 404)
    status = (payload().get("status") or "").strip()
    if status not in {"open", "fulfilled", "closed"}:
        return error("Choose a status", 400)
    item.status = status
    db.session.commit()
    return jsonify({"request": _donation_request(item, include_gifts=True)})


@people_bp.post("/donations/<int:item_id>/received")
@login_required({"caregiver"})
def confirm_received(item_id):
    """The family that asked for help confirms a gift arrived."""
    from .models import DonationRequest

    gift = db.session.get(Donation, item_id)
    request_row = db.session.get(DonationRequest, gift.donation_request_id) if gift and gift.donation_request_id else None
    if not request_row or request_row.requester_user_id != g.user.id:
        return error("This gift is not for your request", 403)
    gift.status = "received"
    db.session.commit()
    return jsonify({"donation": _donation(gift)})
