import os

from flask import g, jsonify, send_from_directory
from flask import Blueprint

from .domain import (
    CLINICAL,
    age_years,
    can_view_passport,
    can_write_passport,
    profile_id_from_passport_id,
    criticality_for,
    iso,
    profile_public,
    user_public,
)
from .extensions import db
from .http import error, login_required, parse_date, payload, save_upload
from .models import (
    Announcement,
    Appointment,
    Attachment,
    DialysisSession,
    MedicalEntry,
    Pregnancy,
    Profile,
    Shelter,
    User,
)

passport_bp = Blueprint("passport", __name__)

ENTRY_TYPES = ["condition", "allergy", "medication", "operation", "lab", "report", "vaccine", "note"]


def _entry_json(entry):
    author = db.session.get(User, entry.author_user_id) if entry.author_user_id else None
    files = Attachment.query.filter_by(entry_id=entry.id).all()
    return {
        "id": entry.id,
        "profile_id": entry.profile_id,
        "entry_type": entry.entry_type,
        "title": entry.title,
        "details": entry.details,
        "occurred_on": iso(entry.occurred_on),
        "author_type": entry.author_type,
        "author_name": author.full_name if author else None,
        "facility_name": entry.facility_name,
        "doctor_name": entry.doctor_name,
        "result_text": entry.result_text,
        "vaccine_status": entry.vaccine_status,
        "created_at": iso(entry.created_at),
        "attachments": [
            {"id": item.id, "filename": item.filename, "mime_type": item.mime_type} for item in files
        ],
    }


def _owned(profile):
    return profile.owner_user_id == g.user.id


@passport_bp.get("/home")
@login_required()
def home():
    profiles = Profile.query.filter_by(owner_user_id=g.user.id).order_by(Profile.id.asc()).all()
    announcements = Announcement.query.order_by(Announcement.starts_at.asc()).limit(6).all()
    upcoming = []
    for profile in profiles:
        for session in DialysisSession.query.filter_by(profile_id=profile.id, status="scheduled").all():
            upcoming.append(
                {
                    "kind": "dialysis",
                    "profile_id": profile.id,
                    "who": profile.full_name,
                    "when": iso(session.scheduled_at),
                    "where": session.facility_name,
                }
            )
        pregnancy = Pregnancy.query.filter_by(profile_id=profile.id).first()
        if pregnancy and pregnancy.next_appointment:
            upcoming.append(
                {
                    "kind": "prenatal",
                    "profile_id": profile.id,
                    "who": profile.full_name,
                    "when": iso(pregnancy.next_appointment),
                    "where": "Prenatal appointment",
                }
            )
        for appointment in Appointment.query.filter_by(profile_id=profile.id).all():
            upcoming.append(
                {
                    "kind": appointment.kind,
                    "profile_id": profile.id,
                    "who": profile.full_name,
                    "when": iso(appointment.scheduled_at),
                    "where": appointment.facility,
                    "appointment_id": appointment.id,
                }
            )
    return jsonify(
        {
            "profiles": [profile_public(profile) for profile in profiles],
            "announcements": [_announcement(item) for item in announcements],
            "upcoming": upcoming,
        }
    )


def _announcement(item):
    shelter = db.session.get(Shelter, item.shelter_id) if item.shelter_id else None
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "location": item.location,
        "starts_at": iso(item.starts_at),
        "details": item.details,
        "shelter_name": shelter.name if shelter else None,
    }


@passport_bp.post("/profiles")
@login_required({"caregiver"})
def create_profile():
    data = payload()
    name = (data.get("full_name") or "").strip()
    if not name:
        return error("Enter a name", 400)
    shelter_id = data.get("shelter_id") or g.user.shelter_id
    if shelter_id and not db.session.get(Shelter, int(shelter_id)):
        return error("That shelter is not registered", 400)
    import secrets

    profile = Profile(
        owner_user_id=g.user.id,
        full_name=name,
        relationship=(data.get("relationship") or "other").strip(),
        date_of_birth=parse_date(data.get("date_of_birth")),
        sex=(data.get("sex") or "").strip() or None,
        blood_type=(data.get("blood_type") or "").strip() or None,
        shelter_id=int(shelter_id) if shelter_id else None,
        disability=str(data.get("disability", "")).lower() in {"1", "true", "yes", "on"},
        disability_notes=(data.get("disability_notes") or "").strip() or None,
        emergency_contact_name=(data.get("emergency_contact_name") or "").strip() or None,
        emergency_contact_phone=(data.get("emergency_contact_phone") or "").strip() or None,
        emergency_token=secrets.token_urlsafe(8),
    )
    db.session.add(profile)
    db.session.commit()
    return jsonify({"profile": profile_public(profile)}), 201


@passport_bp.patch("/profiles/<int:profile_id>")
@login_required()
def update_profile(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile or not _owned(profile):
        return error("You do not have access to this profile", 403)
    data = payload()
    for field in (
        "full_name",
        "relationship",
        "sex",
        "blood_type",
        "disability_notes",
        "emergency_contact_name",
        "emergency_contact_phone",
    ):
        if field in data and data[field] is not None:
            setattr(profile, field, str(data[field]).strip())
    if "date_of_birth" in data:
        profile.date_of_birth = parse_date(data.get("date_of_birth"))
    if "disability" in data:
        profile.disability = str(data.get("disability")).lower() in {"1", "true", "yes", "on"}
    if "shelter_id" in data:
        shelter_id = data.get("shelter_id") or None
        if shelter_id and not db.session.get(Shelter, int(shelter_id)):
            return error("That shelter is not registered", 400)
        profile.shelter_id = int(shelter_id) if shelter_id else None
    db.session.commit()
    return jsonify({"profile": profile_public(profile)})


@passport_bp.delete("/profiles/<int:profile_id>")
@login_required({"caregiver"})
def delete_profile(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile or not _owned(profile):
        return error("You do not have access to this profile", 403)
    if profile.relationship == "self":
        return error("The main profile stays with the account", 400)
    db.session.delete(profile)
    db.session.commit()
    return jsonify({"ok": True})


def _passport_payload(profile):
    entries = MedicalEntry.query.filter_by(profile_id=profile.id).order_by(MedicalEntry.occurred_on.desc()).all()
    return {
        "profile": profile_public(profile),
        "entries": [_entry_json(entry) for entry in entries],
        "can_edit": can_write_passport(g.user, profile),
    }


@passport_bp.get("/profiles/<int:profile_id>/passport")
@login_required()
def passport(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile:
        return error("Health passport not found", 404)
    return jsonify(_passport_payload(profile))


@passport_bp.get("/passport/lookup/<passport_id>")
@login_required()
def passport_lookup(passport_id):
    """Open any health passport with its ID, e.g. MAK-0012-6059."""
    pid = profile_id_from_passport_id(passport_id)
    profile = db.session.get(Profile, pid) if pid else None
    if not profile:
        return error("No health passport has this ID. Check the ID and try again.", 404)
    return jsonify(_passport_payload(profile))


@passport_bp.post("/profiles/<int:profile_id>/entries")
@login_required()
def add_entry(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile:
        return error("Profile not found", 404)
    data = payload()
    entry_type = (data.get("entry_type") or "").strip()
    title = (data.get("title") or "").strip()
    if entry_type not in ENTRY_TYPES or not title:
        return error("Choose a record type and a title", 400)
    if _owned(profile):
        author_type = "patient"
    elif can_write_passport(g.user, profile):
        author_type = "clinician"
    else:
        return error("You cannot add to this health passport", 403)
    if entry_type == "vaccine" and data.get("vaccine_status") not in {"administered", "missing", "overdue"}:
        return error("Mark the vaccine as administered, missing, or overdue", 400)
    entry = MedicalEntry(
        profile_id=profile.id,
        entry_type=entry_type,
        title=title,
        details=(data.get("details") or "").strip() or None,
        occurred_on=parse_date(data.get("occurred_on")),
        author_type=author_type,
        author_user_id=g.user.id,
        facility_name=(data.get("facility_name") or "").strip() or None,
        doctor_name=(data.get("doctor_name") or "").strip() or (g.user.full_name if author_type == "clinician" else None),
        result_text=(data.get("result_text") or "").strip() or None,
        vaccine_status=(data.get("vaccine_status") or "").strip() or None,
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"entry": _entry_json(entry)}), 201


@passport_bp.patch("/entries/<int:entry_id>")
@login_required()
def update_entry(entry_id):
    entry = db.session.get(MedicalEntry, entry_id)
    if not entry:
        return error("Record not found", 404)
    profile = db.session.get(Profile, entry.profile_id)
    if entry.author_user_id != g.user.id:
        return error("You can edit records you wrote", 403)
    data = payload()
    for field in ("title", "details", "facility_name", "doctor_name", "result_text"):
        if field in data:
            setattr(entry, field, (data.get(field) or "").strip() or None)
    if "occurred_on" in data:
        entry.occurred_on = parse_date(data.get("occurred_on"))
    if entry.entry_type == "vaccine" and data.get("vaccine_status") in {"administered", "missing", "overdue"}:
        entry.vaccine_status = data.get("vaccine_status")
    if entry.title is None or entry.title == "":
        return error("A record needs a title", 400)
    db.session.commit()
    return jsonify({"entry": _entry_json(entry)})


@passport_bp.delete("/entries/<int:entry_id>")
@login_required()
def delete_entry(entry_id):
    entry = db.session.get(MedicalEntry, entry_id)
    if not entry:
        return error("Record not found", 404)
    if entry.author_user_id != g.user.id:
        return error("You can remove records you wrote", 403)
    Attachment.query.filter_by(entry_id=entry.id).delete()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"ok": True})


@passport_bp.post("/entries/<int:entry_id>/attachments")
@login_required()
def add_attachment(entry_id):
    entry = db.session.get(MedicalEntry, entry_id)
    if not entry:
        return error("Record not found", 404)
    profile = db.session.get(Profile, entry.profile_id)
    if not _owned(profile) and entry.author_user_id != g.user.id:
        return error("Attach files to a record you can edit", 403)
    try:
        saved = save_upload(request_file())
    except ValueError as exc:
        return error(str(exc), 400)
    if not saved:
        return error("Choose a file", 400)
    attachment = Attachment(entry_id=entry.id, **saved)
    db.session.add(attachment)
    db.session.commit()
    return jsonify({"attachment": {"id": attachment.id, "filename": attachment.filename, "mime_type": attachment.mime_type}}), 201


def request_file():
    from flask import request

    return request.files.get("file")


@passport_bp.get("/attachments/<int:attachment_id>")
@login_required()
def download_attachment(attachment_id):
    attachment = db.session.get(Attachment, attachment_id)
    if not attachment:
        return error("File not found", 404)
    entry = db.session.get(MedicalEntry, attachment.entry_id)
    profile = db.session.get(Profile, entry.profile_id)
    if not can_view_passport(g.user, profile):
        return error("You do not have access to this file", 403)
    folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
    return send_from_directory(folder, attachment.stored_name, download_name=attachment.filename)


def _emergency_body(profile):
    entries = MedicalEntry.query.filter_by(profile_id=profile.id).all()
    from .models import Dependency

    deps = Dependency.query.filter_by(profile_id=profile.id).all()
    return {
        "profile_id": profile.id,
        "full_name": profile.full_name,
        "age": age_years(profile.date_of_birth),
        "blood_type": profile.blood_type,
        "allergies": [entry.title for entry in entries if entry.entry_type == "allergy"],
        "conditions": [entry.title for entry in entries if entry.entry_type == "condition"],
        "medications": [entry.title for entry in entries if entry.entry_type == "medication"],
        "overdue_vaccines": [
            entry.title for entry in entries if entry.entry_type == "vaccine" and entry.vaccine_status in {"missing", "overdue"}
        ],
        "dependencies": [
            {
                "kind": dep.kind,
                "device_name": dep.device_name,
                "supply_level_percent": dep.supply_level_percent,
                "hours_remaining": dep.hours_remaining,
            }
            for dep in deps
        ],
        "emergency_contact_name": profile.emergency_contact_name,
        "emergency_contact_phone": profile.emergency_contact_phone,
        "criticality": criticality_for(profile)["level"],
        "token": profile.emergency_token,
        "note": "Emergency summary only. The full passport stays private.",
    }


@passport_bp.get("/profiles/<int:profile_id>/emergency-summary")
@login_required()
def emergency_summary(profile_id):
    profile = db.session.get(Profile, profile_id)
    if not profile or not _owned(profile):
        return error("You do not have access to this profile", 403)
    return jsonify({"summary": _emergency_body(profile)})


@passport_bp.get("/emergency/<token>")
def public_emergency(token):
    profile = Profile.query.filter_by(emergency_token=token).first()
    if not profile:
        return error("This emergency card was not found", 404)
    return jsonify({"summary": _emergency_body(profile)})
