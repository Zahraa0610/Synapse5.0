# Shared development workflow

## Git
main contains the reviewed recovered application, commit 0835b7b. phase1 is untouched and remains the remote default. Phase 0 changes are only on phase/00-foundation. Review its PR targeting main; never merge automatically. Each later prompt gets a separate feature branch from refreshed main, a scoped commit and reviewed PR. Use independent checkouts/worktrees and private development databases. Do not change schema/API contracts concurrently without coordination. Codex and Claude Code should own different module files; auth/http/models/migrations/context/api changes need explicit shared review.

## Local commands (PowerShell)
The discovered Python is MSYS/UCRT Python 3.12, which creates .venv/bin rather than Windows .venv/Scripts. A conventional Windows Python creates Scripts; substitute that interpreter path when applicable.

```powershell
python -m venv .venv
.\.venv\bin\python.exe -m pip install -r backend/requirements.txt
# Set MAAK_SECRET privately to a stable randomly generated value before starting.
cd backend
..\.venv\bin\python.exe manage.py upgrade
..\.venv\bin\python.exe run.py
```

In a second terminal:
```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```
Frontend http://localhost:5173; backend http://127.0.0.1:5000. Migrations default to backend/maak-dev.db. Do not point MAAK_DATABASE_URL to the original database. On a conventional Windows Python replace bin/python.exe with Scripts/python.exe.

```powershell
cd backend
..\.venv\bin\python.exe -m unittest test_foundation -v
..\.venv\bin\python.exe smoke.py
cd ../frontend
node test-foundation.mjs
npm.cmd run build
```

Optional demo fixtures: from backend, run `..\.venv\bin\python.exe -m flask --app run seed-demo` only in a dedicated disposable development database. No automatic demo seeding. Never treat synthetic fixtures as real records or verified external credentials.

## Environment
MAAK_SECRET: private stable signing key, at least 32 characters in production. Without it the ephemeral development key changes on restart. MAAK_DATABASE_URL: SQLAlchemy SQLite URL (default separate maak-dev.db). MAAK_CREDENTIAL_FOLDER: private credential directory. MAAK_CORS_ORIGINS: comma-separated exact browser origins, default localhost:5173. MAAK_ENV=production enables secret enforcement and disallows demo seeding. VITE_API_BASE_URL: frontend API URL, default /api. No SMS or licensing provider exists; phone authentication returns 503. No secrets in committed .env files.

## First authorized Ministry reviewer
Register a Ministry request, upload identity evidence from account page, independently validate appointment/authority, then run:
```powershell
cd backend
..\.venv\bin\python.exe manage.py authorize-ministry --email <registered-email>
```
The operator must type AUTHORIZE after independent checks. This is not an automatic licensing service. Refresh account state/re-login to see the new dashboard. Approved reviewers inspect documents in the verification queue, assign a shelter when approving coordinators, and approve/reject clinical/NGO applications. Medical access still requires patient grants.

## Required review
Check migration scripts on an isolated copied DB, permission negative tests, API field compatibility, no CSS/design changes, no secrets/uploads/DBs staged. Production readiness additionally requires rate limiting, medical access auditing, emergency consent, storage protection, deployment backups and security review. Do not proceed to Phase 1 through this task.
