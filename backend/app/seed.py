import secrets
from datetime import date, datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from .extensions import db
from .models import (
    Announcement,
    Appointment,
    Complaint,
    CriticalityReview,
    Dependency,
    DialysisSeat,
    DialysisSession,
    Donation,
    HistorySnapshot,
    InventoryItem,
    MedicalEntry,
    NgoRequest,
    Outbreak,
    PersonalSupply,
    Pregnancy,
    Profile,
    Relocation,
    ResourceExchange,
    Shelter,
    SupportFlag,
    Task,
    TransportRequest,
    User,
)


def seed():
    if User.query.first():
        return

    password = generate_password_hash("maak1234")
    today = date.today()
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    shelter_rows = [
        ("Alay Public School", "Mount Lebanon", "school", "Aley", 528, 412, True, 6, True, 18),
        ("Tyr Public School", "South", "school", "Tyr", 400, 390, False, 0, False, 4),
        ("Saida Technical Institute", "South", "center", "Saida", 260, 210, True, 4, True, 10),
        ("Bint Jbeil Community Center", "Nabatieh", "center", "Bint Jbeil", 180, 150, False, 0, False, 2),
        ("Tripoli Public School", "North", "school", "Tripoli", 610, 440, True, 8, True, 12),
        ("Baalbek Public School", "Baalbek-Hermel", "school", "Baalbek", 300, 280, False, 1, False, 3),
        ("Zahle Technical School", "Bekaa", "school", "Zahle", 240, 160, True, 5, True, 14),
        ("Akkar Municipal Shelter", "Akkar", "center", "Halba", 200, 190, False, 0, False, 1),
    ]
    shelters = {}
    for name, region, kind, address, capacity, occupancy, accessible, spaces, power, hours in shelter_rows:
        shelter = Shelter(
            name=name,
            region=region,
            kind=kind,
            address=address,
            capacity=capacity,
            occupancy=occupancy,
            accessible=accessible,
            accessible_spaces=spaces,
            has_backup_power=power,
            electricity_hours=hours,
        )
        db.session.add(shelter)
        db.session.flush()
        shelters[name] = shelter

    def user(full_name, email, phone, role, **extra):
        record = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=password,
            role=role,
            verification_status=extra.pop("verification_status", "not_required"),
            **extra,
        )
        db.session.add(record)
        db.session.flush()
        return record

    alay = shelters["Alay Public School"]
    rania = user("Rania Haddad", "rania@maak.test", "+96170111001", "caregiver", shelter_id=alay.id)
    rana = user(
        "Rana Saleh",
        "rana@maak.test",
        "+96170111002",
        "volunteer",
        helper_type="companion",
        verification_status="not_required",
    )
    user(
        "Karim Daoud",
        "karim@maak.test",
        "+96170111003",
        "volunteer",
        helper_type="transport",
    )
    nadine = user(
        "Nadine Saab",
        "nadine@maak.test",
        "+96170111004",
        "doctor",
        specialty="Internal medicine",
        license_number="38421",
        license_body="Order of Physicians — Beirut",
        license_expires=date(2027, 12, 1),
        verification_status="approved",
    )
    user(
        "Maya Haddad",
        "maya@maak.test",
        "+96170111005",
        "nurse",
        specialty="Community nursing",
        license_number="RN-2291",
        license_body="Order of Nurses",
        license_expires=date(2027, 6, 1),
        verification_status="approved",
    )
    user(
        "Hadi Karam",
        "hadi@maak.test",
        "+96170111006",
        "psychologist",
        specialty="Child psychology",
        license_number="PSY-118",
        license_body="Ministry of Public Health",
        license_expires=date(2026, 11, 1),
        verification_status="checking",
    )
    coordinator = user(
        "Jad Khoury",
        "jad@maak.test",
        "+96170111007",
        "shelter_coordinator",
        shelter_id=alay.id,
    )
    donor = user("Lina Fares", "lina@maak.test", "+96170111008", "donor")
    ministry = user(
        "Ministerial desk",
        "ministry@maak.test",
        "+96170111009",
        "ministry",
        verification_status="approved",
    )
    ngo = user(
        "Cedar Health Relief",
        "ngo@maak.test",
        "+96170111010",
        "ngo",
        verification_status="approved",
    )
    user("Records", "records@maak.test", None, "caregiver")

    def profile(full_name, relationship, dob, shelter, owner=None, **extra):
        record = Profile(
            owner_user_id=owner.id if owner else None,
            full_name=full_name,
            relationship=relationship,
            date_of_birth=dob,
            shelter_id=shelter.id if shelter else None,
            emergency_token=secrets.token_urlsafe(8),
            **extra,
        )
        db.session.add(record)
        db.session.flush()
        return record

    rania_profile = profile(
        "Rania Haddad",
        "self",
        date(1992, 3, 14),
        alay,
        rania,
        sex="female",
        blood_type="O+",
        emergency_contact_name="Jad Khoury",
        emergency_contact_phone="+96170111007",
    )
    salma = profile(
        "Salma Khoury",
        "child",
        date(2017, 4, 12),
        alay,
        rania,
        sex="female",
        blood_type="A+",
        emergency_contact_name="Rania Haddad",
        emergency_contact_phone="+96170111001",
    )
    nabil = profile(
        "Nabil Haddad",
        "parent",
        date(1952, 9, 2),
        alay,
        rania,
        sex="male",
        blood_type="B+",
        disability=True,
        disability_notes="Needs a wheelchair for longer distances",
        emergency_contact_name="Rania Haddad",
        emergency_contact_phone="+96170111001",
    )

    census = [
        ("Wadad Khoury", date(1948, 1, 8), alay, False),
        ("Georges Abi Rached", date(1944, 6, 19), alay, True),
        ("Hala Mansour", date(2019, 2, 2), alay, False),
        ("Samir Daher", date(1958, 11, 3), alay, False),
        ("Rita Nasr", date(1939, 5, 21), alay, True),
        ("Youssef Chamoun", date(1946, 7, 7), shelters["Tyr Public School"], True),
        ("Mariam Wehbe", date(1950, 8, 9), shelters["Tyr Public School"], False),
        ("Adam Saad", date(2018, 1, 15), shelters["Tyr Public School"], False),
        ("Nour Diab", date(1996, 4, 4), shelters["Tyr Public School"], False),
        ("Lea Azar", date(2016, 12, 1), shelters["Saida Technical Institute"], False),
        ("Fouad Harb", date(1955, 3, 3), shelters["Saida Technical Institute"], True),
        ("Sara Boutros", date(1994, 10, 10), shelters["Saida Technical Institute"], False),
        ("Elias Rahme", date(1942, 2, 18), shelters["Bint Jbeil Community Center"], True),
        ("Jana Osman", date(2015, 6, 6), shelters["Tripoli Public School"], False),
        ("Karim Ossman", date(2014, 9, 9), shelters["Tripoli Public School"], False),
        ("Rima Kabbara", date(1991, 1, 20), shelters["Tripoli Public School"], True),
        ("Tarek Haidar", date(1949, 12, 12), shelters["Baalbek Public School"], False),
        ("Maya Saleh", date(1998, 5, 5), shelters["Baalbek Public School"], False),
        ("Charbel Aoun", date(2013, 8, 8), shelters["Zahle Technical School"], False),
        ("Najwa Frem", date(1947, 4, 17), shelters["Zahle Technical School"], False),
        ("Amal Ismail", date(1993, 7, 23), shelters["Akkar Municipal Shelter"], False),
        ("Bilal Hassan", date(2012, 3, 11), shelters["Akkar Municipal Shelter"], False),
        ("Samih Khalil", date(2011, 11, 2), shelters["Akkar Municipal Shelter"], False),
        ("Zahra Mostafa", date(1945, 1, 30), shelters["Akkar Municipal Shelter"], True),
    ]
    census_profiles = []
    for name, dob, shelter, disability in census:
        census_profiles.append(
            profile(name, "other", dob, shelter, disability=disability, sex="unspecified", blood_type="")
        )

    def entry(person, entry_type, title, author, author_type, **extra):
        db.session.add(
            MedicalEntry(
                profile_id=person.id,
                entry_type=entry_type,
                title=title,
                author_user_id=author.id,
                author_type=author_type,
                **extra,
            )
        )

    entry(
        salma,
        "condition",
        "Type 1 diabetes",
        rania,
        "patient",
        details="Diagnosed in childhood. Insulin-dependent.",
        occurred_on=date(2021, 5, 2),
    )
    entry(
        salma,
        "condition",
        "Chronic kidney disease",
        nadine,
        "clinician",
        details="Under nephrology follow-up.",
        occurred_on=date(2024, 9, 18),
        facility_name="Rafik Hariri University Hospital",
        doctor_name="Nadine Saab",
    )
    entry(salma, "allergy", "Penicillin", rania, "patient", details="Rash after penicillin.")
    entry(
        salma,
        "medication",
        "Insulin",
        nadine,
        "clinician",
        details="Basal-bolus regimen.",
        facility_name="Rafik Hariri University Hospital",
        doctor_name="Nadine Saab",
    )
    entry(
        salma,
        "lab",
        "HbA1c",
        nadine,
        "clinician",
        result_text="9.4%",
        occurred_on=today - timedelta(days=20),
        facility_name="Rafik Hariri University Hospital",
        doctor_name="Nadine Saab",
    )
    entry(
        salma,
        "vaccine",
        "MMR",
        rania,
        "patient",
        vaccine_status="administered",
        occurred_on=date(2018, 6, 1),
    )
    entry(salma, "vaccine", "Polio booster", rania, "patient", vaccine_status="overdue")
    entry(
        nabil,
        "condition",
        "Chronic respiratory failure",
        nadine,
        "clinician",
        details="Uses a ventilator overnight.",
        facility_name="AUB Medical Center",
        doctor_name="Nadine Saab",
        occurred_on=date(2023, 2, 11),
    )
    entry(nabil, "medication", "Inhaled bronchodilator", rania, "patient")
    entry(
        rania_profile,
        "note",
        "Prenatal visit summary",
        nadine,
        "clinician",
        details="Blood pressure elevated. Continue follow-up.",
        facility_name="Alay Public School clinic",
        doctor_name="Nadine Saab",
        occurred_on=today - timedelta(days=12),
    )


    db.session.add(
        Dependency(
            profile_id=salma.id,
            kind="oxygen",
            device_name="Portable oxygen cylinder",
            supply_description="Cylinder at 14%",
            supply_level_percent=14,
            hours_remaining=6,
        )
    )
    db.session.add(
        Dependency(
            profile_id=nabil.id,
            kind="ventilator",
            device_name="Home ventilator",
            supply_description="Needs mains power and a backup battery",
            supply_level_percent=30,
            hours_remaining=8,
        )
    )
    db.session.add(
        Dependency(
            profile_id=census_profiles[0].id,
            kind="oxygen",
            device_name="Oxygen concentrator",
            supply_level_percent=18,
            hours_remaining=5,
        )
    )
    db.session.add(
        Dependency(
            profile_id=census_profiles[1].id,
            kind="electricity",
            device_name="Suction device",
            supply_level_percent=20,
            hours_remaining=4,
        )
    )
    db.session.add(
        Dependency(
            profile_id=census_profiles[2].id,
            kind="feeding",
            device_name="Enteral feeding pump",
            supply_level_percent=15,
            hours_remaining=10,
        )
    )
    db.session.add(
        Dependency(
            profile_id=census_profiles[3].id,
            kind="concentrator",
            device_name="Oxygen concentrator",
            supply_level_percent=22,
            hours_remaining=7,
        )
    )
    db.session.add(
        Dependency(
            profile_id=census_profiles[4].id,
            kind="ventilator",
            device_name="Ventilator",
            supply_level_percent=12,
            hours_remaining=3,
        )
    )

    db.session.add(
        PersonalSupply(
            profile_id=salma.id,
            item_name="Glucose test strips",
            category="food",
            quantity_note="4 strips",
            status="shortage",
        )
    )
    db.session.add(
        PersonalSupply(
            profile_id=census_profiles[2].id,
            item_name="Enteral formula",
            category="specialized_nutrition",
            quantity_note="One can",
            status="shortage",
        )
    )
    db.session.add(
        PersonalSupply(
            profile_id=rania_profile.id,
            item_name="Drinking water",
            category="food",
            quantity_note="6 liters",
            status="low",
        )
    )
    db.session.add(
        PersonalSupply(
            profile_id=salma.id,
            item_name="Insulin pen needles",
            category="other",
            quantity_note="2 needles",
            status="low",
        )
    )

    db.session.add(
        DialysisSession(
            profile_id=salma.id,
            facility_name="Saida Government Hospital",
            scheduled_at=now - timedelta(days=2),
            status="missed",
            seat_note="No transport",
        )
    )
    db.session.add(
        DialysisSession(
            profile_id=salma.id,
            facility_name="Saida Government Hospital",
            scheduled_at=now + timedelta(days=1, hours=9),
            status="scheduled",
            seat_note="Morning chair",
        )
    )
    db.session.add(
        Pregnancy(
            profile_id=rania_profile.id,
            weeks=28,
            due_date=today + timedelta(days=84),
            risk_level="high",
            risk_notes="Gestational hypertension",
            next_appointment=now + timedelta(days=10, hours=10),
        )
    )
    db.session.add(
        Pregnancy(
            profile_id=census_profiles[8].id,
            weeks=22,
            due_date=today + timedelta(days=120),
            risk_level="routine",
            next_appointment=now + timedelta(days=14),
        )
    )
    db.session.add(
        Pregnancy(
            profile_id=census_profiles[11].id,
            weeks=31,
            due_date=today + timedelta(days=60),
            risk_level="high",
            risk_notes="Previous cesarean",
            next_appointment=now + timedelta(days=6),
        )
    )
    db.session.add(
        Pregnancy(
            profile_id=census_profiles[15].id,
            weeks=18,
            due_date=today + timedelta(days=150),
            risk_level="routine",
        )
    )
    db.session.add(
        Pregnancy(
            profile_id=census_profiles[17].id,
            weeks=35,
            due_date=today + timedelta(days=30),
            risk_level="high",
            risk_notes="Reduced fetal movement reported",
        )
    )
    db.session.add(
        Pregnancy(
            profile_id=census_profiles[20].id,
            weeks=12,
            due_date=today + timedelta(days=190),
            risk_level="routine",
        )
    )

    for person in [salma, nabil, *census_profiles[:5]]:
        db.session.add(
            CriticalityReview(
                profile_id=person.id,
                reviewer_id=coordinator.id,
                classification="critical",
                note="Confirmed from reported device supply and treatment continuity.",
                created_at=now - timedelta(days=1),
            )
        )

    alay_inventory = [
        ("Insulin pens", "medication", 0, "pens", "shortage", False, True),
        ("Baby formula", "food", 4, "tins", "low", False, False),
        ("Sanitary pads", "hygiene", 0, "packs", "shortage", False, False),
        ("Paracetamol", "medication", 40, "boxes", "available", False, False),
        ("Oral rehydration salts", "food", 6, "sachets", "low", False, False),
        ("Specialized beds", "equipment", 0, "beds", "shortage", True, True),
        ("Oxygen cylinders", "equipment", 1, "cylinders", "shortage", True, True),
        ("Glucose test strips", "medication", 0, "boxes", "shortage", False, True),
        ("Enteral feeding formula", "nutrition", 0, "cans", "shortage", False, True),
        ("Drinking water", "food", 20, "liters", "low", False, False),
        ("Wheelchairs", "equipment", 3, "chairs", "available", True, True),
        ("Ventilator batteries", "equipment", 0, "batteries", "shortage", True, True),
        ("Pediatric amoxicillin", "medication", 0, "bottles", "shortage", False, False),
        ("Wound dressings", "hygiene", 25, "packs", "available", False, False),
        ("Adult diapers", "hygiene", 0, "packs", "shortage", False, False),
        ("Prenatal vitamins", "medication", 5, "bottles", "low", False, False),
    ]
    for name, category, qty, unit, status, equipment, specialized in alay_inventory:
        db.session.add(
            InventoryItem(
                shelter_id=alay.id,
                item_name=name,
                category=category,
                quantity=qty,
                unit=unit,
                status=status,
                is_equipment=equipment,
                is_specialized=specialized,
            )
        )

    other_inventory = {
        "Tyr Public School": [("Baby formula", "shortage"), ("Sanitary pads", "shortage"), ("Paracetamol", "low")],
        "Saida Technical Institute": [("Insulin pens", "available"), ("Oxygen cylinders", "low")],
        "Bint Jbeil Community Center": [("Drinking water", "shortage"), ("Wound dressings", "shortage")],
        "Tripoli Public School": [("Specialized beds", "shortage"), ("Baby formula", "available")],
        "Baalbek Public School": [("Enteral feeding formula", "shortage"), ("Oxygen cylinders", "shortage")],
        "Zahle Technical School": [("Insulin pens", "available"), ("Paracetamol", "available"), ("Sanitary pads", "available")],
        "Akkar Municipal Shelter": [("Drinking water", "shortage"), ("Baby formula", "shortage"), ("Adult diapers", "low")],
    }
    for shelter_name, items in other_inventory.items():
        shelter = shelters[shelter_name]
        for item_name, status in items:
            db.session.add(
                InventoryItem(
                    shelter_id=shelter.id,
                    item_name=item_name,
                    category="supplies",
                    quantity=30 if status == "available" else 0,
                    unit="units",
                    status=status,
                    is_equipment=item_name in {"Specialized beds", "Oxygen cylinders"},
                    is_specialized=item_name in {"Specialized beds", "Oxygen cylinders", "Insulin pens", "Enteral feeding formula"},
                )
            )

    exchange = ResourceExchange(
        from_shelter_id=shelters["Zahle Technical School"].id,
        to_shelter_id=alay.id,
        item_name="Insulin pens",
        quantity=12,
        status="accepted",
        needs_volunteer=True,
        created_by=coordinator.id,
    )
    db.session.add(exchange)
    db.session.flush()

    db.session.add(
        Task(
            kind="delivery",
            title="Carry insulin pens to Alay",
            details="12 insulin pens from Zahle Technical School. Hand them to the shelter coordinator.",
            location="Zahle Technical School to Alay Public School",
            scheduled_at=now + timedelta(days=1, hours=11),
            shelter_id=alay.id,
            status="open",
            exchange_id=exchange.id,
        )
    )
    db.session.add(
        Task(
            kind="companion",
            title="Hospital companion for Nabil Haddad",
            details="Non-medical guidance from the entrance to the respiratory clinic. No clinical care.",
            location="AUB Medical Center, Beirut",
            scheduled_at=now + timedelta(days=3, hours=8),
            shelter_id=alay.id,
            status="open",
        )
    )
    db.session.add(
        Task(
            kind="delivery",
            title="Baby formula drop",
            details="Deliver two tins already pledged by a donor.",
            location="Saida Technical Institute",
            scheduled_at=now + timedelta(days=2),
            shelter_id=shelters["Saida Technical Institute"].id,
            status="accepted",
            assignee_user_id=rana.id,
        )
    )
    db.session.add(
        Announcement(
            kind="doctor_visit",
            title="Dr. Nadine Saab is visiting",
            location="Alay Public School, ground-floor classroom",
            starts_at=now + timedelta(days=2, hours=10),
            details="Internal medicine clinic for residents. Bring your health passport.",
            shelter_id=alay.id,
        )
    )
    db.session.add(
        Announcement(
            kind="free_healthcare_day",
            title="Free healthcare day",
            location="Saida Technical Institute",
            starts_at=now + timedelta(days=5, hours=9),
            details="Vaccination catch-up and prenatal checks. No fee.",
            shelter_id=shelters["Saida Technical Institute"].id,
        )
    )

    prenatal = Appointment(
        profile_id=rania_profile.id,
        facility="Rafik Hariri University Hospital",
        scheduled_at=now + timedelta(days=10, hours=10),
        kind="prenatal",
        notes="High-risk follow-up",
    )
    dialysis_appt = Appointment(
        profile_id=salma.id,
        facility="Saida Government Hospital",
        scheduled_at=now + timedelta(days=1, hours=9),
        kind="dialysis",
    )
    nabil_appt = Appointment(
        profile_id=nabil.id,
        facility="AUB Medical Center",
        scheduled_at=now + timedelta(days=3, hours=8),
        kind="clinic",
        notes="Respiratory review",
    )
    db.session.add_all([prenatal, dialysis_appt, nabil_appt])
    db.session.flush()

    db.session.add(
        TransportRequest(
            profile_id=nabil.id,
            requester_id=rania.id,
            destination="AUB Medical Center",
            destination_type="hospital",
            wheelchair_required=True,
            appointment_id=nabil_appt.id,
            status="accepted",
            provider_user_id=ngo.id,
            notes="Wheelchair space required",
        )
    )
    db.session.add(
        TransportRequest(
            profile_id=rania_profile.id,
            requester_id=rania.id,
            destination="Rafik Hariri University Hospital",
            destination_type="hospital",
            wheelchair_required=False,
            appointment_id=prenatal.id,
            status="requested",
        )
    )

    db.session.add(
        SupportFlag(
            profile_id=census_profiles[2].id,
            person_description="Boy, about 9, classroom B",
            shelter_id=census_profiles[2].shelter_id,
            signs="Bullying of a child with a disability · Withdrawn or constantly sad",
            flagged_by=rana.id,
            reason="Child has been bullied in the shared classroom and stopped speaking at meals.",
            includes_bullying=True,
            status="open",
        )
    )
    db.session.add(
        Relocation(
            shelter_id=alay.id,
            destination_shelter_id=shelters["Saida Technical Institute"].id,
            profile_id=nabil.id,
            reason="Ventilator needs a shelter with backup power if Alay's generator hours drop.",
            status="requested",
            created_by=coordinator.id,
        )
    )
    db.session.add(
        Outbreak(
            shelter_id=shelters["Tyr Public School"].id,
            suspected_illness="Acute watery diarrhea",
            case_count=6,
            notes="Six residents in the same classroom developed symptoms within two days.",
            status="reported",
            created_by=coordinator.id,
        )
    )

    def complaint(shelter, category, description, source, status, created_by, days_ago, resolved_days_ago=None):
        created = now - timedelta(days=days_ago)
        resolved = now - timedelta(days=resolved_days_ago) if resolved_days_ago is not None else None
        db.session.add(
            Complaint(
                shelter_id=shelter.id,
                region=shelter.region,
                category=category,
                description=description,
                source=source,
                submitted_by=created_by.id,
                status=status,
                created_at=created,
                resolved_at=resolved,
            )
        )

    complaint(alay, "Medication shortage", "Insulin pens ran out for three residents.", "direct", "received", rania, 2)
    complaint(
        alay,
        "Medication shortage",
        "Insulin was restocked last month and has run out again.",
        "phone",
        "received",
        coordinator,
        1,
    )
    complaint(
        alay,
        "Medication shortage",
        "Previous insulin shortage was marked resolved after a delivery.",
        "note",
        "resolved",
        coordinator,
        40,
        30,
    )
    complaint(alay, "Water", "Drinking water is low on the second floor.", "in_person", "being_addressed", rania, 4)
    complaint(shelters["Tyr Public School"], "Sanitation", "Shared latrines are blocked.", "message", "under_review", rana, 3)
    complaint(shelters["Tyr Public School"], "Healthcare access", "Children missed vaccinations after displacement.", "email", "received", rana, 6)
    complaint(shelters["Akkar Municipal Shelter"], "Food", "Baby formula ran out over the weekend.", "phone", "received", coordinator, 2)
    complaint(shelters["Baalbek Public School"], "Power", "Backup generator failed during the night.", "in_person", "being_addressed", coordinator, 5)
    complaint(shelters["Tripoli Public School"], "Assistance", "Elderly residents need help reaching the clinic.", "direct", "resolved", coordinator, 20, 10)
    complaint(shelters["Nabatieh"] if False else shelters["Bint Jbeil Community Center"], "Water", "Water truck did not arrive.", "phone", "received", coordinator, 1)

    db.session.add(
        Donation(
            donor_id=donor.id,
            kind="money",
            amount=250,
            currency="USD",
            target_type="shelter",
            target_shelter_id=alay.id,
            cause_label="Alay Public School",
            status="received",
            from_recommendation=False,
        )
    )
    db.session.add(
        Donation(
            donor_id=donor.id,
            kind="physical",
            item_description="Sanitary pads",
            target_type="shelter",
            target_shelter_id=shelters["Tyr Public School"].id,
            cause_label="Tyr Public School",
            status="allocated",
            from_recommendation=True,
        )
    )

    db.session.add(
        NgoRequest(
            ngo_user_id=ngo.id,
            organization="Cedar Health Relief",
            description="Can deliver wheelchair-accessible rides and a small oxygen cylinder reserve.",
            shelter_id=alay.id,
            status="connected",
        )
    )
    db.session.add(
        NgoRequest(
            ngo_user_id=ngo.id,
            organization="Cedar Health Relief",
            description="Mobile vaccination team available next week.",
            status="submitted",
        )
    )

    db.session.add(
        DialysisSeat(
            facility_name="Saida Government Hospital",
            region="South",
            seats_available=1,
            next_opening=now + timedelta(days=1, hours=9),
            notes="One morning chair",
        )
    )
    db.session.add(
        DialysisSeat(
            facility_name="AUB Medical Center",
            region="Beirut",
            seats_available=2,
            next_opening=now + timedelta(days=2, hours=8),
            notes="Adult chairs",
        )
    )
    db.session.add(
        DialysisSeat(
            facility_name="Tripoli Government Hospital",
            region="North",
            seats_available=0,
            next_opening=now + timedelta(days=6),
            notes="Waiting list",
        )
    )

    for index, shelter in enumerate(shelters.values()):
        for month_offset in range(5, -1, -1):
            month_day = today.replace(day=1)
            year = month_day.year
            month = month_day.month - month_offset
            while month <= 0:
                month += 12
                year -= 1
            label = f"{year:04d}-{month:02d}"
            base = 4 + (index % 3)
            shortages = base + (5 - month_offset) if shelter.region in {"South", "Akkar", "Baalbek-Hermel"} else max(1, base - month_offset)
            if month_offset == 0 and shelter.name == "Alay Public School":
                shortages = 9
            db.session.add(
                HistorySnapshot(
                    month=label,
                    shelter_id=shelter.id,
                    shortage_count=shortages,
                    occupancy=max(20, shelter.occupancy - month_offset * 8),
                    complaint_count=max(0, 3 - month_offset // 2 + (index % 2)),
                    critical_count=2 + (index % 4),
                )
            )

    db.session.commit()
