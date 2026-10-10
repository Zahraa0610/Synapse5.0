"""Small admin commands for Ma'ak.

    python manage.py reset          Delete all data and create empty tables
    python manage.py demo           Reset, then load the fictional demo data
    python manage.py create-admin   Create the first Ministry of Public Health account
"""

import getpass
import sys

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db


def reset():
    from sqlalchemy import inspect, text

    # Drop every table, including ones left over from older versions.
    with db.engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        for name in inspect(conn).get_table_names():
            conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
    db.create_all()
    print("Database is empty and ready.")


def demo():
    from app.demo_data import load_demo_data

    reset()
    load_demo_data()
    print("Demo data loaded. Start with: python run.py --demo")


def create_admin():
    from app.models import User

    db.create_all()  # works on a brand-new install too

    name = input("Full name: ").strip()
    email = input("Email: ").strip().lower()
    password = getpass.getpass("Password (6+ characters): ")
    if not name or not email or len(password) < 6:
        sys.exit("Name, email and a password of 6+ characters are required.")
    if User.query.filter_by(email=email).first():
        sys.exit("An account with this email already exists.")
    db.session.add(
        User(
            full_name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="ministry",
            verification_status="approved",
        )
    )
    db.session.commit()
    print(f"Ministry admin {email} created. They can approve doctors, NGOs and other Ministry staff.")


COMMANDS = {"reset": reset, "demo": demo, "create-admin": create_admin}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    with create_app(check_schema=False).app_context():
        COMMANDS[sys.argv[1]]()
