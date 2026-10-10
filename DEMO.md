# Demo video walkthrough

A 4–5 minute story you can follow while recording. Every account's password is `maak1234`,
but in demo mode you can just click the role buttons on the sign-in page.

## Before recording

```bash
cd backend
python manage.py demo      # fresh demo data (run again before every take)
python run.py --demo
```

```bash
cd frontend
npm run dev
```

- Open http://localhost:5173 in a clean browser window, zoom to 110–125% so text is readable.
- For the phone-sized screens (family, volunteer, donor), open DevTools (F12) → device toolbar
  (Ctrl + Shift + M) → choose a phone such as iPhone 12.
- For the coordinator, doctor and Ministry screens, switch back to the desktop view.
- Record with OBS Studio, or Windows Game Bar (Win + Alt + R).

## The story

**1. The problem (on the landing page, 20 s)**
"When families are displaced, their medical history, medicines and care get lost. Ma'ak keeps them
connected to shelters, volunteers, doctors, donors and the Ministry."

**2. A family — Rania (phone view, 60 s)** — click **Family**
- Home: her family (her mother Salma is marked *Critical*), and nearby doctor visits.
- **Health passport**: Salma's ID (MAK-…), conditions, records marked doctor-entered or
  patient-entered. Tap **Save on this phone** → the emergency QR card works offline.
- **Care** → tap **Medical devices and power**: oxygen at low level, shelters with backup power →
  **Request a move**.
- Switch the language to **عربي** for a few seconds to show the Arabic version.

**3. A family outside the shelters — Hussein (phone view, 30 s)** — sign out, click **Family (renting)**
- **Requests → Ask for donations**: show his open request for food and baby formula.

**4. A donor — Lina (phone view, 30 s)** — click **Donor**
- **Needs**: verified shelter shortages, medical cases, and Hussein's request
  ("Family outside a shelter"). **Give** → "Thank you!".
- **My donations** shows it as pledged.

**5. A volunteer — Rana (phone view, 40 s)** — click **Volunteer**
- **Tasks**: accept "Carry insulin pens to Alay".
- **Support**: report a child who is being bullied — describe, tick signs, send.
- **Complaints**: record a complaint a resident made by phone.

**6. The shelter coordinator — Jad (desktop, 50 s)** — click **Shelter**
- **Overview**: occupancy, shortages, and the move request for Nabil (he needs power for his ventilator) → set it to *Escalated*.
- **Supplies and shortages**: filter *Low or missing*, add an item.
- **Residents**: confirm a resident as *Critical*.
- **Monthly report**: generated automatically → **Download CSV**.

**7. The doctor — Nadine (desktop, 30 s)** — click **Doctor**
- **Patients**: switch a patient between *Critical* and *Not critical*.
- **Find passport**: paste a passport ID, open it, add a clinician record.

**8. The Ministry (desktop, 50 s)** — click **Ministry**
- **Overview**: shelters ranked by need, demand forecast, the verification queue (approve a doctor).
- **Complaints**: change a status; recurring problems by shelter; trends by region.
- **Donations**: where gifts went and which shortages are still uncovered.
- **Reports**: high-risk counts (elderly, children, pregnant, disability, device-dependent) and
  outbreak reports.

**9. Close (10 s)**
"Every suggestion — criticality, priority, forecasts — is confirmed by a person. Ma'ak supports
decisions; it doesn't replace them."

## Tips

- Do one dry run first; then `python manage.py demo` to reset before the real take.
- Keep each screen on view for 2–3 seconds before clicking, so viewers can follow.
- If you speak over the video, record the voice separately and add it in editing (e.g. CapCut or
  Clipchamp, both free) — it is much easier than talking while clicking.
