"""End-to-end API tests. They run the real Flask app on the in-memory store,
so no Firebase project or Twilio account is needed.

    cd backend
    python -m unittest discover tests
"""

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app, whatsapp  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402

SENT_CODES = {}


def fake_send_code(phone, code):
    SENT_CODES[phone] = code
    return "whatsapp"


class MaakApiTest(unittest.TestCase):
    """One story through every role, in order."""

    @classmethod
    def setUpClass(cls):
        whatsapp.send_code = fake_send_code
        cls.app = create_app({"STORE": "memory", "SECRET_KEY": "test-secret-key-that-is-long-enough-123", "TESTING": True})
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.session.add(
                User(full_name="Ministry Admin", email="admin@moph.gov.lb", password_hash=generate_password_hash("admin-pass-1"),
                     role="ministry", verification_status="approved")
            )
            db.session.commit()
        cls.tokens = {}
        cls.ids = {}

    # -- helpers ------------------------------------------------------------
    def call(self, method, path, who=None, expect=(200, 201), **kwargs):
        headers = {"Authorization": f"Bearer {self.tokens[who]}"} if who else {}
        response = getattr(self.client, method)(f"/api{path}", headers=headers, **kwargs)
        codes = expect if isinstance(expect, tuple) else (expect,)
        self.assertIn(response.status_code, codes, f"{method.upper()} {path} -> {response.status_code}: {response.get_json()}")
        return response.get_json()

    def sign_in(self, who, email, password):
        self.tokens[who] = self.call("post", "/auth/login", json={"email": email, "password": password})["token"]

    def register(self, who, **body):
        body.setdefault("password", "password-123")
        result = self.call("post", "/auth/register", json=body, expect=201)
        self.tokens[who] = result["token"]
        return result["user"]

    # -- the story ----------------------------------------------------------
    def test_full_story(self):
        # Ministry registers shelters
        self.sign_in("ministry", "admin@moph.gov.lb", "admin-pass-1")
        alay = self.call("post", "/shelters", "ministry", json={"name": "Alay Public School", "region": "Mount Lebanon", "capacity": 300, "occupancy": 280, "has_backup_power": True, "electricity_hours": 18, "accessible": True})["shelter"]
        saida = self.call("post", "/shelters", "ministry", json={"name": "Saida Institute", "region": "South", "capacity": 100, "occupancy": 40})["shelter"]
        self.call("post", "/shelters", "ministry", json={"name": "alay public school", "region": "South"}, expect=409)

        # Sign-up: a phone number must be confirmed with a WhatsApp code
        phone = "+96170111222"
        self.call("post", "/auth/register", json={"role": "caregiver", "full_name": "Rania", "phone": phone, "password": "password-123"}, expect=400)
        self.call("post", "/auth/send-code", json={"phone": "+961 70 111 222", "purpose": "signup"})
        self.call("post", "/auth/verify-code", json={"phone": phone, "code": "000000"}, expect=400)
        self.call("post", "/auth/verify-code", json={"phone": phone, "code": SENT_CODES[phone]})
        family = self.register("family", role="caregiver", full_name="Rania Haddad", phone=phone, shelter_id=alay["id"])
        self.assertTrue(family["phone_verified"])

        # Login with a WhatsApp code, single use
        self.call("post", "/auth/send-code", json={"phone": phone, "purpose": "login"})
        code = SENT_CODES[phone]
        self.call("post", "/auth/login", json={"phone": phone, "code": code})
        self.call("post", "/auth/login", json={"phone": phone, "code": code}, expect=401)
        self.call("post", "/auth/login", json={"email": "nobody@x.com", "password": "x"}, expect=401)

        # Passwords are stored hashed
        with self.app.app_context():
            stored = User.query.filter_by(phone=phone).first()
            self.assertNotIn("password-123", stored.password_hash)

        # Other roles
        self.register("coordinator", role="shelter_coordinator", full_name="Jad", email="jad@x.com", shelter_id=alay["id"])
        self.call("post", "/auth/register", json={"role": "volunteer", "full_name": "Rana", "email": "rana@x.com", "password": "password-123"}, expect=400)
        self.register("volunteer", role="volunteer", full_name="Rana", email="rana@x.com", id_document_type="lebanese_id", id_document_number="LB1", offers_driving=True, car_model="Kia", car_plate="B 1")
        doctor = self.register("doctor", role="doctor", full_name="Dr Nadine", email="nadine@x.com", license_number="123")
        self.register("donor", role="donor", full_name="Lina", email="lina@x.com")
        ngo = self.register("ngo", role="ngo", full_name="Amel", email="amel@x.com")
        self.register("renting", role="caregiver", full_name="Hussein", email="h@x.com")

        # Ministry approves the doctor and the NGO
        queue = self.call("get", "/verification-queue", "ministry")["users"]
        self.assertEqual({u["id"] for u in queue}, {doctor["id"], ngo["id"]})
        for person in (doctor, ngo):
            self.call("patch", f"/users/{person['id']}/verification", "ministry", json={"status": "approved"})

        # Family: home, own passport, family member, records
        home = self.call("get", "/home", "family")
        self.assertEqual(home["profiles"][0]["relationship"], "self")
        salma = self.call("post", "/profiles", "family", json={"full_name": "Salma Khoury", "relationship": "parent", "date_of_birth": "1948-03-02", "disability": True})["profile"]
        self.assertEqual(salma["shelter_id"], alay["id"])
        entry = self.call("post", f"/profiles/{salma['id']}/entries", "family", json={"entry_type": "condition", "title": "COPD", "occurred_on": "2020-01-01"})["entry"]
        self.call("post", f"/entries/{entry['id']}/attachments", "family", data={"file": (io.BytesIO(b"%PDF-1.4"), "report.pdf")}, content_type="multipart/form-data")
        passport = self.call("get", f"/profiles/{salma['id']}/passport", "family")
        self.assertEqual(passport["entries"][0]["author_type"], "patient")

        # Care needs and a move request
        self.call("post", f"/profiles/{salma['id']}/dependencies", "family", json={"kind": "other", "device_name": "CPAP", "supply_level_percent": 10, "hours_remaining": 5})
        self.call("post", f"/profiles/{salma['id']}/dependencies", "family", json={"kind": "other"}, expect=400)
        self.call("post", f"/profiles/{salma['id']}/supplies", "family", json={"item_name": "Tube formula", "category": "specialized_nutrition", "status": "shortage"})
        self.call("post", f"/profiles/{salma['id']}/dialysis", "family", json={"facility_name": "Aley unit", "scheduled_at": "2030-01-01T08:00"})
        self.call("put", f"/profiles/{salma['id']}/pregnancy", "family", json={"weeks": 20, "risk_level": "high"})
        care = self.call("get", f"/profiles/{salma['id']}/care", "family")
        self.assertEqual(care["criticality"]["level"], "critical")
        self.call("post", "/relocations", "family", json={"profile_id": salma["id"], "destination_shelter_id": saida["id"], "reason": "Needs power"})
        again = self.call("post", "/relocations", "family", json={"profile_id": salma["id"], "destination_shelter_id": saida["id"], "reason": "Needs power"})
        self.assertEqual(again["relocation"]["status"], "requested")

        # Requests page: appointment, transport, support, complaint
        appointment = self.call("post", "/appointments", "family", json={"profile_id": salma["id"], "facility": "AUBMC", "scheduled_at": "2030-02-01T10:00"})["appointment"]
        self.call("post", "/transport", "family", json={"profile_id": salma["id"], "destination": "AUBMC", "destination_type": "hospital", "appointment_id": appointment["id"], "wheelchair_required": True})
        self.call("post", "/complaints", "family", json={"category": "Food", "description": "No meals", "source": "direct"})
        mine = self.call("get", "/requests/mine", "family")
        self.assertEqual(len(mine["transports"]), 1)

        # Passport lookup by ID (any signed-in user), wrong ID rejected
        self.call("get", f"/passport/lookup/{salma['passport_id']}", "donor")
        self.call("get", "/passport/lookup/MAK-0002-0000", "donor", expect=404)
        self.call("get", f"/emergency/{salma['emergency_token']}")

        # Family outside shelters asks for donations
        request_row = self.call("post", "/donation-requests", "renting", json={"living_situation": "renting", "region": "South", "category": "food", "description": "Food for 6", "people_count": 6})["request"]

        # Coordinator manages the shelter
        board = self.call("get", "/shelter/board", "coordinator")
        self.assertEqual(board["shelter"]["name"], "Alay Public School")
        self.call("patch", f"/shelters/{alay['id']}", "coordinator", json={"occupancy": 295, "accessible": True})
        item = self.call("post", f"/shelters/{alay['id']}/inventory", "coordinator", json={"item_name": "Insulin", "category": "medication", "quantity": 0, "status": "shortage"})["item"]
        self.call("patch", f"/inventory/{item['id']}", "coordinator", json={"quantity": 2, "status": "low"})
        self.call("patch", f"/inventory/{item['id']}", "coordinator", json={"status": "shortage"})
        extra = self.call("post", f"/shelters/{alay['id']}/inventory", "coordinator", json={"item_name": "Old item", "status": "available"})["item"]
        self.call("delete", f"/inventory/{extra['id']}", "coordinator")
        exchange = self.call("post", "/exchanges", "coordinator", json={"to_shelter_id": saida["id"], "item_name": "Formula", "quantity": 3, "needs_volunteer": True})["exchange"]
        self.call("patch", f"/exchanges/{exchange['id']}", "coordinator", json={"status": "accepted"})
        self.call("post", "/outbreaks", "coordinator", json={"suspected_illness": "Diarrhea", "case_count": 4})
        relocation = self.call("get", "/shelter/board", "coordinator")["relocations"][0]
        self.call("patch", f"/relocations/{relocation['id']}", "coordinator", json={"status": "escalated"})
        self.call("post", f"/profiles/{salma['id']}/criticality-review", "coordinator", json={"classification": "critical"})
        self.call("post", "/tasks", "coordinator", json={"kind": "companion", "title": "Hospital companion", "scheduled_at": "2030-01-02T09:00"})
        self.call("post", "/announcements", "coordinator", json={"kind": "doctor_visit", "title": "Dr visit", "starts_at": "2030-01-03T10:00"})
        complaint = self.call("get", "/shelter/board", "coordinator")["complaints"][0]
        self.call("patch", f"/complaints/{complaint['id']}", "coordinator", json={"status": "being_addressed"})
        report = self.call("get", "/shelter/board", "coordinator")["history"]
        self.assertEqual(report["history"][-1]["shortages"], 1)  # this month, from live data

        # Volunteer: tasks, support case (free text), complaint
        tasks = self.call("get", "/volunteer/board", "volunteer")["tasks"]
        self.assertGreaterEqual(len(tasks), 2)  # delivery from the exchange + companion task
        task = tasks[0]
        self.call("post", f"/tasks/{task['id']}/respond", "volunteer", json={"action": "accept"})
        self.call("post", f"/tasks/{task['id']}/respond", "volunteer", json={"action": "complete"})
        self.call("post", "/support-flags", "volunteer", json={"person_description": "Boy, about 9", "shelter_id": alay["id"], "signs": ["Bullying"], "reason": "Bullied at school"})
        self.call("post", "/support-flags", "volunteer", json={"reason": "No person"}, expect=400)
        self.call("post", "/complaints", "volunteer", json={"category": "Hygiene", "description": "Dirty toilets", "source": "phone", "shelter_id": alay["id"]})
        rides = self.call("get", "/requests/mine", "volunteer")["transports"]
        self.call("patch", f"/transport/{rides[0]['id']}", "volunteer", json={"status": "accepted"})

        # Donor: needs include the shelter shortage and the family's request
        donor_board = self.call("get", "/donor/board", "donor")
        kinds = {item["kind"] for item in donor_board["opportunities"]}
        self.assertTrue({"shelter", "request"} <= kinds)
        gift = self.call("post", "/donations", "donor", json={"kind": "physical", "item_description": "Insulin", "target_type": "shelter", "target_shelter_id": alay["id"]})["donation"]
        family_gift = self.call("post", "/donations", "donor", json={"kind": "money", "amount": 50, "target_type": "request", "donation_request_id": request_row["id"]})["donation"]
        self.call("post", f"/donations/{family_gift['id']}/received", "renting")
        self.call("post", f"/donations/{family_gift['id']}/received", "family", expect=403)

        # Ministry: insulin is promised, not received -> still a gap
        donations = self.call("get", "/ministry/donations", "ministry")
        alay_row = next(row for row in donations["distribution"] if row["shelter_id"] == alay["id"])
        self.assertIn("Insulin", alay_row["pledged_only"])
        self.call("patch", f"/donations/{gift['id']}", "coordinator", json={"status": "received"})
        donations = self.call("get", "/ministry/donations", "ministry")
        alay_row = next(row for row in donations["distribution"] if row["shelter_id"] == alay["id"])
        self.assertEqual(alay_row["gaps"] + alay_row["pledged_only"], [])

        # Doctor: find by passport ID, add a clinician record, change status
        found = self.call("get", f"/doctor/patients?q={salma['passport_id']}", "doctor")["patients"]
        self.assertEqual(found[0]["id"], salma["id"])
        clinician_entry = self.call("post", f"/profiles/{salma['id']}/entries", "doctor", json={"entry_type": "note", "title": "Review"})["entry"]
        self.assertEqual(clinician_entry["author_type"], "clinician")
        self.call("post", f"/profiles/{salma['id']}/criticality-review", "doctor", json={"classification": "non_critical"})
        self.assertEqual(self.call("get", "/doctor/patients", "doctor")["patients"][0]["criticality"]["level"], "non_critical")

        # NGO offer: Ministry can connect or reject it
        offer = self.call("post", "/ngo/requests", "ngo", json={"description": "Mobile clinic"})["request"]
        self.call("patch", f"/ngo/requests/{offer['id']}", "ministry", json={"status": "rejected"})
        self.call("patch", f"/ngo/requests/{offer['id']}", "ngo", json={"status": "accepted"}, expect=400)
        self.call("get", "/ngo/board", "ngo")

        # Ministry dashboards
        overview = self.call("get", "/ministry/overview", "ministry")
        self.assertEqual(overview["shelter_count"], 2)
        self.call("get", "/ministry/shelters", "ministry")
        complaints = self.call("get", "/ministry/complaints", "ministry")
        self.assertGreaterEqual(len(complaints["complaints"]), 2)
        reports = self.call("get", "/ministry/reports", "ministry")
        self.assertGreaterEqual(reports["high_risk"]["regions"][-1]["elderly"], 1)
        self.call("get", "/ministry/ngos", "ministry")
        self.call("get", "/distribution", "ministry")

        # Role checks
        self.call("get", "/ministry/overview", "family", expect=403)
        self.call("get", "/shelter/board", "donor", expect=403)
        self.call("get", "/home", expect=401)


if __name__ == "__main__":
    unittest.main()
