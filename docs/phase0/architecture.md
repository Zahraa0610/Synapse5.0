# Ma?ak architecture

Existing application retained: React 19, React Router 7 and Vite 6; Flask 3.1, Flask-SQLAlchemy, SQLite and PyJWT. No new application or CSS changes in Phase 0. The supplied 18-page PDF was text-inspected and its embedded design images visually reviewed. Exact rendered app conformance remains unverified without a connected browser; known structural gaps are recorded in design-assessment.md.

## Frontend
App.jsx defines public welcome, login, registration and emergency routes plus authenticated role pages. Shell.jsx supplies mobile navigation and desktop sidebars. context.jsx centralizes auth and English/Arabic direction; translations remain incomplete across the existing pages. ui.jsx provides existing Field, Button, Pill and Note components. PatientPages, VolunteerPages, ShelterPages and DeskPages own their modules. api.js supplies configurable requests and file downloads. VITE_API_BASE_URL defaults to /api; Vite proxies this to localhost:5000.

Login/register persist a bearer JWT in localStorage. On refresh AuthProvider calls /auth/me. Backend 401 removes the token and clears centralized state. Logout calls /auth/logout before clearing local state; failed logout remains visible and does not falsely report server revocation. Cross-role routes redirect to the authorized dashboard or account page. localStorage increases XSS consequences: use a strict production CSP and review a future HttpOnly-cookie migration separately.

## Backend
create_app(config) registers auth, passport, care, people, shelter and oversight blueprints under /api. http.py centralizes bearer session verification, role approval checks, input error handling and existing medical uploads. domain.py holds serializers, patient grants, need suggestions and aggregate analytics. models.py retains the existing 25 tables and adds sessions, credentials and organization membership. migrations.py runs ordered SQLite migrations explicitly; startup never initializes or seeds existing data.

Default database: backend/maak-dev.db, separate from the original backend/maak.db. A random signing key is used if MAAK_SECRET is absent; set a stable private secret for sessions to survive server restarts. Production startup requires a secret of at least 32 characters. CORS defaults to localhost:5173 and is configured by an explicit origin list.

## Verification and file storage
Requested professional/institutional roles register as caregiver with requested_role and pending status. Public APIs cannot self-approve. Authorized Ministry reviewers inspect private documents and approve/reject clinical, NGO and coordinator requests. Coordinators require assigned shelters. Ministry activation requires the local operator command and independent identity/authority checks. External licensing and SMS verification are unavailable; no external success is claimed.

Medical attachments remain in configured UPLOAD_FOLDER and are downloaded only after patient access checks. New identity/credential documents use CREDENTIAL_FOLDER, UUID filenames, extension/signature checks and a 5 MB limit, and download only to the owner or approved Ministry reviewer. Files are outside frontend static hosting. Signature checks are not malware scanning; deployment must add scanner, retention policy and encrypted storage. Legacy license files remain preserved in their original location and require an explicit private-storage migration if present.

## Module contracts
Auth owns sessions, verification and assigned privileges; passport owns Profile/MedicalEntry/Attachment/AccessGrant; care owns dependencies, supplies, dialysis and pregnancy; people owns tasks, appointments, transport, support, complaints and donations; shelter owns inventory, exchanges, relocation and outbreaks; oversight owns NGO coordination and aggregate Ministry reporting. Ownership/grants must be checked server-side for every object operation.

See development-workflow.md for exact commands and environment configuration. Production deployment requires an HTTPS reverse proxy, a suitable WSGI server, private storage permissions, backups and security review; Flask's development server is for local development.

Registration now uses three existing steps for all roles: details, documents and review. Identity review is optional for non-privileged roles; privileged requests require identity evidence and clinical requests additionally require professional credentials. Any new document submission sets manual review pending.
