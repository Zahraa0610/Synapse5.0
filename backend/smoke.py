from app import create_app

import tempfile
from pathlib import Path

temporary = tempfile.TemporaryDirectory()
app = create_app({"AUTO_MIGRATE": True, "SEED_DEMO": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(Path(temporary.name) / "smoke.db"), "UPLOAD_FOLDER": str(Path(temporary.name) / "uploads")})
from app.extensions import db
from app.models import User
with app.app_context():
    # Explicit synthetic fixture authorization; production users are never auto-approved.
    User.query.filter_by(email="jad@maak.test").first().verification_status = "approved"
    db.session.commit()
client = app.test_client()


def login(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "maak1234"})
    assert response.status_code == 200, response.json
    return {"Authorization": f"Bearer {response.json['token']}"}


def main():
    assert client.get("/api/health").json["ok"]
    rania = login("rania@maak.test")
    doctor = login("nadine@maak.test")
    ministry = login("ministry@maak.test")
    donor = login("lina@maak.test")
    coordinator = login("jad@maak.test")
    volunteer = login("rana@maak.test")
    ngo = login("ngo@maak.test")
    phone = client.post("/api/auth/login", json={"phone": "+96170111001", "code": "000000"})
    assert phone.status_code == 503

    home = client.get("/api/home", headers=rania).json
    assert any(profile["full_name"] == "Salma Khoury" for profile in home["profiles"])
    salma = next(profile for profile in home["profiles"] if profile["full_name"] == "Salma Khoury")
    assert salma["criticality"]["level"] == "critical"
    assert salma["criticality"]["confirmed"] is True

    passport = client.get(f"/api/profiles/{salma['id']}/passport", headers=rania)
    assert passport.status_code == 200
    authors = {entry["author_type"] for entry in passport.json["entries"]}
    assert "patient" in authors and "clinician" in authors
    blocked = client.get(f"/api/profiles/{salma['id']}/passport", headers=ministry)
    assert blocked.status_code == 403

    created = client.post(
        f"/api/profiles/{salma['id']}/entries",
        headers=doctor,
        json={"entry_type": "lab", "title": "Creatinine", "facility_name": "RHUH", "result_text": "1.8", "doctor_name": "Nadine Saab"},
    )
    assert created.status_code == 201, created.json
    assert created.json["entry"]["author_type"] == "clinician"

    emergency = client.get(f"/api/emergency/{salma['emergency_token']}")
    assert emergency.status_code == 200
    assert "Penicillin" in emergency.json["summary"]["allergies"]
    assert "entries" not in emergency.json["summary"]

    care = client.get(f"/api/profiles/{salma['id']}/care", headers=rania).json
    assert care["backup_shelters"]
    assert any(seat["seats_available"] >= 0 for seat in care["seats"])

    board = client.get("/api/shelter/board", headers=coordinator).json
    assert board["stats"]["shortages"] == 9
    assert board["stats"]["critical_residents"] == 7

    donor_board = client.get("/api/donor/board", headers=donor).json
    assert donor_board["recommendation"]
    gift = client.post(
        "/api/donations",
        headers=donor,
        json={
            "kind": "physical",
            "item_description": "Oxygen cylinders",
            "target_type": "shelter",
            "target_shelter_id": donor_board["recommendation"]["target_shelter_id"],
            "cause_label": "Chosen by donor",
            "from_recommendation": True,
        },
    )
    assert gift.status_code == 201, gift.json
    missing = client.post("/api/donations", headers=donor, json={"kind": "money", "amount": 10, "target_type": "cause"})
    assert missing.status_code == 400

    tasks = client.get("/api/volunteer/board", headers=volunteer).json["tasks"]
    open_task = next(task for task in tasks if task["status"] == "open")
    accepted = client.post(f"/api/tasks/{open_task['id']}/respond", headers=volunteer, json={"action": "accept"})
    assert accepted.status_code == 200

    overview = client.get("/api/ministry/overview", headers=ministry).json
    assert overview["ranked"][0]["priority"]["score"] >= overview["ranked"][-1]["priority"]["score"]
    assert "person decides" in overview["forecast"][0]["note"].lower() or "person decides" in overview["note"].lower()
    complaints = client.get("/api/ministry/complaints", headers=ministry).json
    assert any(pattern["reopened"] for pattern in complaints["patterns"])
    assert complaints["regions"]
    reports = client.get("/api/ministry/reports", headers=ministry).json
    assert reports["high_risk"]["note"]
    assert "full_name" not in str(reports["high_risk"]["regions"])

    ngo_board = client.get("/api/ngo/board", headers=ngo)
    assert ngo_board.status_code == 200
    print("smoke ok")


if __name__ == "__main__":
    try:
        main()
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        temporary.cleanup()
