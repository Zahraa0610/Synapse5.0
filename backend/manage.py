"""Explicit development database initialization and operator authorization."""
import argparse
from app import create_app
from app.extensions import db
from app.migrations import upgrade
from app.models import User

parser = argparse.ArgumentParser()
parser.add_argument("command", choices=["upgrade", "authorize-ministry"])
parser.add_argument("--email")
args = parser.parse_args()
app = create_app()
with app.app_context():
    if args.command == "upgrade":
        upgrade()
        print("Database migrations applied")
    else:
        if not args.email:
            parser.error("--email is required")
        user = User.query.filter_by(email=args.email.lower()).first()
        if not user or not (user.requested_role == "ministry" or user.role == "ministry" and user.verification_status != "approved"):
            parser.error("Account must have a pending Ministry request")
        from app.models import Credential
        if not Credential.query.filter_by(user_id=user.id).first():
            parser.error("Identity documentation must be submitted and reviewed first")
        confirmation = input("After independently checking Ministry authorization, type AUTHORIZE: ")
        if confirmation != "AUTHORIZE":
            parser.error("Authorization cancelled")
        user.role = "ministry"
        user.requested_role = None
        user.verification_status = "approved"
        for document in Credential.query.filter_by(user_id=user.id).all():
            document.status = "approved"
            document.review_note = "Independent Ministry authorization confirmed by local operator"
        db.session.commit()
        print("Ministry access authorized by local operator")
