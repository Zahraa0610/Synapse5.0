# Ma'ak — health coordination for displaced people in Lebanon

Ma'ak connects displaced families, shelter coordinators, volunteers, doctors, donors, NGOs and the
Ministry of Public Health around one thing: keeping people's health care going when they have to move.

- **Families** keep a digital health passport (with an offline emergency QR card), track critical
  needs such as oxygen, dialysis, pregnancy and nutrition, request transport, file complaints, and —
  if they live outside a shelter — ask donors for help.
- **Shelter coordinators** manage capacity, supplies and shortages, residents' criticality,
  exchanges with other shelters, donations, volunteer tasks, complaints and a monthly report.
- **Volunteers** accept delivery and companion tasks, record complaints, and report people who may
  need mental health support.
- **Doctors, nurses and psychologists** (license-verified) open passports by ID, add clinician
  records and confirm whether a patient is critical.
- **Donors** give money or supplies to verified shelter needs, medical cases or families.
- **The Ministry** sees national shelter priorities, complaints and their trends, donation
  transparency and gaps, high-risk population counts, outbreak reports and demand forecasts.
- **NGOs** offer assistance that the Ministry connects to shelters.

The app works in **English and Arabic** (right-to-left).

## Tech

| Part | Stack |
|---|---|
| Backend | Python 3, Flask, Flask-SQLAlchemy (SQLite), JWT auth |
| Frontend | React 19, React Router, Vite |

## Run it

You need **Python 3.10+** and **Node.js 18+**.

**1. Backend** (terminal 1)

```bash
cd backend
pip install -r requirements.txt
python manage.py create-admin     # first time only: creates the first Ministry account
python run.py                     # http://127.0.0.1:5000
```

**2. Frontend** (terminal 2)

```bash
cd frontend
npm install
npm run dev                       # open http://localhost:5173
```

A normal start is an **empty** system. The Ministry admin registers shelters (Ministry → Shelters →
Register a shelter) and approves clinician and NGO accounts; everyone else signs up from the app.

## Demo mode

For presentations there is a fictional scenario — 8 shelters across Lebanon's regions, families,
volunteers, a doctor, a donor, the Ministry and an NGO, with months of history.

```bash
cd backend
python manage.py demo     # wipes the database and loads the demo scenario
python run.py --demo      # demo mode: shows quick-login buttons on the sign-in page
```

Demo mode only changes two things: the sign-in page shows "Try a role" buttons, and phone login shows
the one-time code on screen (normally it is printed in the server console until an SMS provider is
connected in `send_login_code` in `backend/app/routes_auth.py`). All demo content lives in
`backend/app/demo_data.py`; nothing in the app code depends on it. See [DEMO.md](DEMO.md) for a
walkthrough you can follow while recording.

## Admin commands

```bash
python manage.py reset          # delete all data, create empty tables
python manage.py demo           # reset, then load the demo scenario
python manage.py create-admin   # create a Ministry of Public Health account
```

If the backend says the database is from an older version, run `python manage.py reset`
(or `python manage.py demo`).

## Configuration

| Variable | Purpose |
|---|---|
| `MAAK_SECRET` | Secret used to sign login tokens. **Set this in any real deployment.** |
| `MAAK_DEMO=1` | Same as `python run.py --demo`. |

## Design principles

- **People decide.** Criticality, outbreak flags, recommendations and forecasts are suggestions that
  a coordinator, clinician or Ministry officer confirms.
- **Patient-entered and clinician-entered records are always labelled.**
- **The Ministry sees aggregated counts**, not individual health passports.
- **No exact addresses** are asked for in donation requests from families outside shelters.

## Project layout

```
backend/
  app/
    models.py          database tables
    domain.py          shared logic: criticality, priorities, reports, forecasts
    routes_*.py        API endpoints by area
    demo_data.py       fictional demo scenario (only loaded on request)
  manage.py            admin commands
  run.py               start the server
frontend/
  src/
    main.jsx           routes
    Shell.jsx          navigation per role
    AuthPages.jsx      landing, sign in, sign up, emergency card
    PatientPages.jsx   family pages: home, passport, care, requests
    RolePages.jsx      volunteer, donor, shelter, clinician, Ministry, NGO pages
    context.jsx        language (EN/AR) and sign-in state
```
