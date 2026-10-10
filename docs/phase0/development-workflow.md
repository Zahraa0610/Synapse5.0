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

MAAK_BACKEND_URL controls the Vite development proxy target (default http://127.0.0.1:5000). An old backend returns 404 for /auth/logout; restart the updated backend or point the frontend at the updated server. Do not silently clear a still-valid session when revocation fails. An already-invalid session (401) signs out successfully.

Vite reads MAAK_BACKEND_URL from both the process environment and ignored frontend/.env.local. Local .env.local now selects http://127.0.0.1:5001, so existing frontend servers on ports 5173 and 5174 both reach the updated isolated backend. This local environment file is not committed. Refresh/sign in again when switching from the obsolete backend; patient records still require active grants. Additional chart/doctor test records are explicitly synthetic and exist only in the development copy.

## Active isolated local stack after sign-out recovery

The older server on port 5000 does not register /auth/logout. Multiple Python servers were found; none was stopped. A consistent copy of the original DB was migrated at backend/maak-logout-development.db and started on port 5001. Frontend on localhost:5173 proxies to it. Existing account records are preserved in this copy; new development edits affect the copy. Old JWTs require signing in again. A synthetic integration account was created only in the development copy to verify real HTTP logout/revocation.

To restart this isolated stack, from backend:
```powershell
$env:MAAK_DATABASE_URL = 'sqlite:///' + (Join-Path (Get-Location).Path 'maak-logout-development.db')
..\.venv\bin\python.exe -c "from app import create_app; create_app().run(host='127.0.0.1', port=5001, debug=False)"
```
From frontend in another terminal:
```powershell
$env:MAAK_BACKEND_URL = 'http://127.0.0.1:5001'
npm.cmd run dev -- --port 5173 --strictPort
```
Set a private stable MAAK_SECRET before restarting if sessions must survive server restarts. Do not switch a live production database or stop unidentified processes.

## First authorized Ministry reviewer
Register a Ministry request, upload identity evidence from account page, independently validate appointment/authority, then run:
```powershell
cd backend
..\.venv\bin\python.exe manage.py authorize-ministry --email <registered-email>
```
The operator must type AUTHORIZE after independent checks. This is not an automatic licensing service. Refresh account state/re-login to see the new dashboard. Approved reviewers inspect documents in the verification queue, assign a shelter when approving coordinators, and approve/reject clinical/NGO applications. Medical access still requires patient grants.

## Required review
Check migration scripts on an isolated copied DB, permission negative tests, API field compatibility, no CSS/design changes, no secrets/uploads/DBs staged. Production readiness additionally requires rate limiting, medical access auditing, emergency consent, storage protection, deployment backups and security review. Do not proceed to Phase 1 through this task.
