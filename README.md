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
| Backend | Python 3, Flask, JWT auth |
| Database | Google Cloud **Firestore** (Firebase) |
| Verification codes | **WhatsApp** through Twilio |
| Frontend | React 19, React Router, Vite |

Passwords and verification codes are stored only as salted hashes (scrypt), never as plain text.

## Set up Firebase (database)

1. Go to <https://console.firebase.google.com> → **Add project** (Google Analytics is not needed).
2. In the project: **Build → Firestore Database → Create database** → choose a location
   (e.g. `europe-west`) → start in **production mode**. The app talks to Firestore from the
   backend with an admin key, so no public access rules are needed.
3. **Project settings (gear icon) → Service accounts → Generate new private key.** A JSON file
   downloads. Move it to `backend/firebase-key.json`. **Never commit this file** (it is in
   `.gitignore`).

## Set up WhatsApp codes (Twilio)

1. Create a free account at <https://www.twilio.com/try-twilio>.
2. In the Twilio console: **Messaging → Try it out → Send a WhatsApp message**. This is the
   WhatsApp **sandbox**: it shows a number (`+1 415 523 8886`) and a join phrase like `join red-tiger`.
3. On each phone that will receive codes, send that join phrase on WhatsApp to the sandbox number
   (once per phone).
4. Copy the **Account SID** and **Auth Token** from the Twilio console home page.

For a real launch, register your own WhatsApp sender in Twilio and an approved *authentication*
template, then set `TWILIO_WHATSAPP_FROM` to your number and `TWILIO_CONTENT_SID` to the template.
If Twilio is not configured, codes are printed in the backend console so development still works.

## Configure

Copy `backend/.env.example` to `backend/.env` and fill it in:

```
MAAK_SECRET=any-long-random-text
FIREBASE_CREDENTIALS=firebase-key.json
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

## Run it

You need **Python 3.10+** and **Node.js 18+**.

**Backend** (terminal 1)

```bash
cd backend
pip install -r requirements.txt
python manage.py create-admin     # first time only: the first Ministry of Public Health account
python run.py                     # http://127.0.0.1:5000
```

**Frontend** (terminal 2)

```bash
cd frontend
npm install
npm run dev                       # open http://localhost:5173
```

The system starts empty. The Ministry admin registers shelters (Ministry → Shelters → Register a
shelter) and approves clinician and NGO accounts; everyone else signs up in the app. Sign-up with a
phone number requires the WhatsApp code.

## Tests

The API tests run the real backend on an in-memory store (no Firebase or Twilio needed):

```bash
cd backend
python -m unittest discover tests
```

## Admin commands

```bash
python manage.py create-admin   # create a Ministry of Public Health account
python manage.py reset          # delete ALL data in Firestore (asks for confirmation)
```

## Design principles

- **People decide.** Criticality, outbreak flags, recommendations and forecasts are suggestions that
  a coordinator, clinician or Ministry officer confirms.
- **Patient-entered and clinician-entered records are always labelled.**
- **The Ministry sees aggregated counts**, not individual health passports.
- **No exact addresses** are asked for in donation requests from families outside shelters.
- **Login codes are single-use**, expire after 10 minutes, allow 5 attempts and one resend per minute;
  the API never reveals whether a phone number has an account.

## Project layout

```
backend/
  app/
    models.py          data models (one Firestore collection each)
    store.py           small model layer on Firestore (+ in-memory store for tests)
    whatsapp.py        sends verification codes through Twilio
    domain.py          shared logic: criticality, priorities, reports, forecasts
    routes_*.py        API endpoints by area
  tests/               end-to-end API tests
  manage.py            admin commands
  run.py               start the server
  .env.example         settings template
frontend/
  src/
    main.jsx           routes
    Shell.jsx          navigation per role
    AuthPages.jsx      landing, sign in, sign up, emergency card
    PatientPages.jsx   family pages: home, passport, care, requests
    RolePages.jsx      volunteer, donor, shelter, clinician, Ministry, NGO pages
    context.jsx        language (EN/AR) and sign-in state
```
