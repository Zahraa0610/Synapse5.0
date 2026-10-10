# Phase 0 — Secure Authentication, Database Foundation & Role-Based Access

Target: main. Review required; do not merge automatically.

The recovered application allowed universal phone-code login, non-revocable JWT logout and self-selected coordinator privileges. This change requires persisted revocable sessions, rejects unavailable phone verification honestly, records professional/institutional role requests as pending, and enables privileges only through authorized manual review or independent Ministry operator authorization. Patient grants remain required for clinical records, and coordinators are limited to assigned shelters.

Adds explicit versioned SQLite migrations, private credential storage and review states, organization relationships, configurable API/CORS/database settings, centralized expiration handling and role-aware routing. Existing frontend styling is retained. Startup no longer initializes/seeds the original database; the development database defaults to a separate file.

The reported sign-out error was traced to an older running backend returning 404 for /auth/logout. Adds a configurable development proxy and clear compatibility error; expired sessions (401) now sign out cleanly. A separate updated local stack using a migrated DB copy passed real HTTP login-state/logout/revocation checks through the frontend proxy. No unidentified servers were stopped.

Validation: eight backend foundation tests, actual HTTP health startup, isolated existing smoke, frontend routing/API tests and Vite production build passed. Fresh/repeated and legacy migrations passed; all existing rows and columns were preserved across 25 tables in an isolated recovery-copy migration. No original DB writes were performed. The live original database gained a user compared with the prior snapshot, so content-equivalence is not claimed; a fresh consistent snapshot was preserved.

Limitations: no real SMS/WhatsApp or external licensing provider; no connected browser for UI end-to-end tests; all 57 approved features are now mapped and the PDF reference reviewed, with existing visual gaps documented. Production rate limiting, audit logs, emergency consent/token lifecycle, legacy privilege review and storage hardening remain follow-up requirements. Review as a partial Phase 0 foundation; do not declare full Phase 0 completion until pending validation is resolved.
