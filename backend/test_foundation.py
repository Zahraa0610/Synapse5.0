import io
import sqlite3
import tempfile
import unittest
import threading
import urllib.request
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from werkzeug.security import check_password_hash
from app import create_app
from app.extensions import db
from app.migrations import upgrade
from app.models import AuthSession, Credential, Profile, Shelter, User


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-only-signing-key-with-sufficient-length", "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(self.root / "test.db"), "CREDENTIAL_FOLDER": str(self.root / "credentials"), "UPLOAD_FOLDER": str(self.root / "uploads"), "AUTO_MIGRATE": True})
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def register(self, email="patient@example.test", role="caregiver"):
        response = self.client.post("/api/auth/register", json={"full_name": "Test User", "email": email, "password": "long-test-password", "role": role})
        self.assertEqual(response.status_code, 201, response.json)
        return response.json, {"Authorization": "Bearer " + response.json["token"]}

    def reviewer(self):
        data, headers = self.register("reviewer@example.test", "ministry")
        # Fixture represents independent operator authorization, never a public API.
        with self.app.app_context():
            user = db.session.get(User, data["user"]["id"])
            user.role = "ministry"
            user.requested_role = None
            user.verification_status = "approved"
            db.session.commit()
        return data, headers

    def test_backend_http_startup(self):
        from werkzeug.serving import make_server
        server = make_server("127.0.0.1", 0, self.app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/health", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b'"ok":true', response.read())
        finally:
            server.shutdown(); thread.join(timeout=5); server.server_close()

    def test_registration_login_refresh_logout_expiration(self):
        data, headers = self.register()
        with self.app.app_context():
            self.assertTrue(check_password_hash(db.session.get(User, data["user"]["id"]).password_hash, "long-test-password"))
        duplicate = self.client.post("/api/auth/register", json={"role":"caregiver", "full_name":"Other", "email":"PATIENT@example.test", "password":"long-test-password"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(self.client.post("/api/auth/login", json={"email":"patient@example.test", "password":"wrong"}).status_code, 401)
        signed = self.client.post("/api/auth/login", json={"email":"patient@example.test", "password":"long-test-password"})
        self.assertEqual(signed.status_code, 200)
        active = {"Authorization":"Bearer " + signed.json["token"]}
        self.assertEqual(self.client.get("/api/auth/me", headers=active).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout", headers=active).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=active).status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        with self.app.app_context():
            session = AuthSession.query.filter_by(revoked=False).first()
            session.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
            db.session.commit()
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization":"Bearer malformed"}).status_code, 401)

    def test_validation_and_no_fake_phone_provider(self):
        self.assertEqual(self.client.post("/api/auth/register", json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/register", json=[1]).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/register", json={"role":["doctor"]}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", json={"phone":"+96100000", "code":"000000"}).status_code, 503)
        self.assertEqual(self.client.post("/api/auth/phone-code").status_code, 503)

    def test_operator_ministry_authorization(self):
        data, headers = self.register("official@example.test", "ministry")
        self.assertEqual(self.client.post("/api/me/verification-file", headers=headers, data={"file":(io.BytesIO(b"%PDF-test identity"),"identity.pdf")}).status_code,200)
        _, reviewer = self.reviewer()
        self.assertEqual(self.client.patch(f"/api/users/{data['user']['id']}/verification",headers=reviewer,json={"status":"approved"}).status_code,403)
        environment={**os.environ,"MAAK_DATABASE_URL":"sqlite:///"+str(self.root/"test.db"),"MAAK_SECRET":self.app.config["SECRET_KEY"]}
        result=subprocess.run([sys.executable,str(Path(__file__).parent/"manage.py"),"authorize-ministry","--email","official@example.test"],input="AUTHORIZE\n",text=True,capture_output=True,env=environment,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.client.get("/api/auth/me",headers=headers).json["user"]["role"],"ministry")
        self.assertEqual(self.client.get("/api/ministry/overview",headers=headers).status_code,200)

    def test_privilege_requests_and_authorization_matrix(self):
        restricted = ["doctor", "nurse", "psychologist", "ministry", "ngo", "shelter_coordinator"]
        for role in restricted:
            data, headers = self.register(role + "@example.test", role)
            self.assertEqual(data["user"]["role"], "caregiver")
            self.assertEqual(data["user"]["requested_role"], role)
            for path in ["/api/doctor/patients", "/api/ministry/overview", "/api/shelter/board", "/api/ngo/board"]:
                self.assertEqual(self.client.get(path, headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/ministry/overview").status_code, 401)

    def test_private_documents_manual_review_and_shelter_scope(self):
        data, headers = self.register("doctor@example.test", "doctor")
        for name, content in [("unsafe.exe", b"MZ"), ("fake.pdf", b"not a PDF"), ("large.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024))]:
            response = self.client.post("/api/me/verification-file", headers=headers, data={"file":(io.BytesIO(content),name)})
            self.assertEqual(response.status_code, 400)
            response.close()
        uploaded = self.client.post("/api/me/verification-file", headers=headers, data={"file":(io.BytesIO(b"%PDF-1.7\nTest fixture"),"license.pdf")})
        self.assertEqual(uploaded.status_code, 200)
        uploaded = self.client.post("/api/me/verification-file", headers=headers, data={"document_kind":"professional", "file":(io.BytesIO(b"%PDF-test credential"),"professional.pdf")})
        self.assertEqual(uploaded.status_code, 200)
        document = self.client.get("/api/me/credentials", headers=headers).json["credentials"][0]
        _, other = self.register("other@example.test")
        path = f"/api/credentials/{document['id']}/file"
        self.assertEqual(self.client.get(path, headers=other).status_code, 403)
        response = self.client.get(path, headers=headers)
        self.assertEqual(response.status_code, 200)
        response.close()
        reviewer, review_headers = self.reviewer()
        incomplete, incomplete_headers = self.register("incomplete@example.test", "nurse")
        self.client.post("/api/me/verification-file", headers=incomplete_headers, data={"file":(io.BytesIO(b"%PDF-test identity"),"identity.pdf")})
        self.assertEqual(self.client.patch(f"/api/users/{incomplete['user']['id']}/verification", headers=review_headers, json={"status":"approved"}).status_code,400)
        self.assertEqual(self.client.patch(f"/api/users/{reviewer['user']['id']}/verification", headers=review_headers, json={"status":"approved"}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/users/{data['user']['id']}/verification", headers=headers, json={"status":"approved"}).status_code, 403)
        review_path = f"/api/users/{data['user']['id']}/verification"
        self.assertEqual(self.client.patch(review_path, headers=review_headers, json={"status":"rejected","note":"Needs valid evidence"}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).json["user"]["verification_status"], "rejected")
        self.assertEqual(self.client.patch(review_path, headers=review_headers, json={"status":"approved"}).status_code, 200)
        self.assertEqual(self.client.get("/api/doctor/patients", headers=headers).status_code, 200)
        coordinator, coord_headers = self.register("coord@example.test", "shelter_coordinator")
        self.client.post("/api/me/verification-file", headers=coord_headers, data={"file":(io.BytesIO(b"%PDF-test"),"identity.pdf")})
        with self.app.app_context():
            one = Shelter(name="One",region="Test",capacity=10,occupancy=0)
            two = Shelter(name="Two",region="Test",capacity=10,occupancy=0)
            db.session.add_all([one,two]); db.session.commit()
            one_id, two_id = one.id, two.id
        path = f"/api/users/{coordinator['user']['id']}/verification"
        self.assertEqual(self.client.patch(path, headers=review_headers, json={"status":"approved"}).status_code, 400)
        self.assertEqual(self.client.patch(path, headers=review_headers, json={"status":"approved","shelter_id":one_id}).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/users/{coordinator['user']['id']}/shelter", headers=coord_headers, json={"shelter_id":two_id}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/shelters/{two_id}", headers=coord_headers, json={"capacity":99}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/shelters/{one_id}", headers=coord_headers, json={"capacity":11}).status_code, 200)

    def test_patient_grants_and_medical_privacy(self):
        patient, owner = self.register()
        _, stranger = self.register("stranger@example.test")
        _, volunteer = self.register("volunteer@example.test", "volunteer")
        _, donor = self.register("donor@example.test", "donor")
        _, ministry = self.reviewer()
        doctor, clinical = self.register("doctor@example.test", "doctor")
        with self.app.app_context():
            profile = Profile(owner_user_id=patient["user"]["id"],full_name="Synthetic fixture",emergency_token="test-emergency-token")
            db.session.add(profile)
            user = db.session.get(User, doctor["user"]["id"])
            user.role="doctor"; user.requested_role=None; user.verification_status="approved"
            db.session.commit(); profile_id=profile.id
        path = f"/api/profiles/{profile_id}/passport"
        self.assertEqual(self.client.get(path,headers=owner).status_code,200)
        for unauthorized in [stranger, volunteer, donor, ministry, clinical]:
            self.assertEqual(self.client.get(path,headers=unauthorized).status_code,403)
            self.assertEqual(self.client.get(f"/api/profiles/{profile_id}/care",headers=unauthorized).status_code,403)
        grant=self.client.post(f"/api/profiles/{profile_id}/grants",headers=owner,json={"grantee_user_id":doctor['user']['id']})
        self.assertEqual(grant.status_code,200)
        self.assertEqual(self.client.get(path,headers=clinical).status_code,200)
        self.assertEqual(self.client.get(f"/api/doctor/profiles/{profile_id}",headers=clinical).status_code,200)
        with self.app.app_context():
            from app.models import AccessGrant
            grant_id=AccessGrant.query.first().id
        self.assertEqual(self.client.post(f"/api/grants/{grant_id}/revoke",headers=owner).status_code,200)
        self.assertEqual(self.client.get(path,headers=clinical).status_code,403)
        self.assertEqual(self.client.get(f"/api/doctor/profiles/{profile_id}",headers=clinical).status_code,403)
        overview=self.client.get("/api/ministry/overview",headers=ministry)
        self.assertEqual(overview.status_code,200)
        self.assertNotIn("Synthetic fixture", str(overview.json))

    def test_migrations_fresh_repeat_and_legacy_data_preservation(self):
        with self.app.app_context():
            upgrade(); upgrade()
            self.assertEqual(db.session.execute(db.text("SELECT COUNT(*) FROM schema_migrations")).scalar(),3)
            self.assertEqual(db.session.execute(db.text("PRAGMA foreign_keys")).scalar(),1)
        legacy=self.root / "legacy.db"
        conn=sqlite3.connect(legacy)
        conn.executescript((Path(__file__).parent/"migrations"/"0001_existing_schema.sql").read_text())
        conn.execute("INSERT INTO users(id,full_name,password_hash,role,verification_status,created_at) VALUES (1,'Preserved','hash','caregiver','not_required','2026-01-01')")
        conn.execute("INSERT INTO profiles(id,owner_user_id,full_name,relationship,disability,emergency_token,created_at) VALUES(1,1,'Dependent','child',0,'preserved-token','2026-01-01')")
        conn.commit()
        before={name:conn.execute('SELECT * FROM "'+name+'"').fetchall() for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        copied=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///"+str(legacy),"AUTO_MIGRATE":True})
        with copied.app_context():
            self.assertEqual(User.query.first().full_name,"Preserved")
            self.assertEqual(Profile.query.first().full_name,"Dependent")
            upgrade(); db.session.remove(); db.engine.dispose()
        conn=sqlite3.connect(legacy)
        for name, rows in before.items():
            after=conn.execute('SELECT * FROM "'+name+'"').fetchall()
            if name == "users": after=[row[:-1] for row in after]
            self.assertEqual(rows,after,name)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
