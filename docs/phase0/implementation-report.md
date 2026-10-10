# Phase 0 implementation handoff

| Component | Existing | Working | Missing | Next action |
|---|---|---|---|---|
| Git recovery | Incomplete committed snapshot and local application work | 14-file recovery commit; main pushed; dedicated foundation branch | Human PR review | Review foundation PR; do not auto-merge |
| Authentication | Password login, universal phone OTP and JWT | Password hashing, 8-hour persisted sessions, backend logout/revocation, refresh API | Real SMS, production abuse protection | Configure provider and rate limits separately |
| Verification | License upload and status UI | Private documents, manual review, rejection, independent Ministry gate | External licensing service; browser checks | Review real documents through approved process |
| Authorization | Roles, patient grants, some object checks | Pending privilege requests, approval gates, assigned shelter scope, negative privacy tests | Fine-grained future org/caregiver scope and audit trail | Adopt shared checks for every future endpoint |
| Database | 25 SQLAlchemy tables/SQLite | Versioned additive migrations; four new tables; indexes/FKs; isolated preservation checks | Future deployment DB decision | Keep SQLite local; review PostgreSQL later |
| Frontend integration | React role pages and centralized state | Configurable API URL, expiration event, async backend logout, role route checks, manual review UI | Browser/PDF validation; complete translations | Validate against supplied PDF and browser |
| Product modules | Existing passport/care/shelter/volunteer/transport/complaint/donation/NGO/oversight pages | Existing smoke exercised representative paths | Full approved feature validation | All 57 features mapped; no Phase 1 work |

Existing layout components, CSS, module pages, models, blueprints, patient ownership and grant logic were reused. No CSS changed in Phase 0. Copy corrections remove false OTP/credential success claims. New foundation files: migrations.py, three SQL revisions, manage.py, test_foundation.py, test-foundation.mjs and phase0 documentation.

Auth endpoints modified: register, login, me, verification-file, verification review/queue and shelter assignment. New endpoints: auth/logout, auth/phone-code (honest unavailable response), me/credentials and credentials/id/file. Shared authorization affects all existing protected endpoints; care records now require patient ownership/clinical grant, record deletion checks current access, support flags check object ownership, and transport completion checks assigned providers.

Schema changes: users.requested_role; auth_sessions; credentials; organizations; organization_members; credential review constraints, membership uniqueness and relationship indexes. Existing original DB is untouched by application startup/migration tests; all migrations target isolated copies/test DBs. An external live database difference was observed and separately backed up; this report does not claim byte equality with the prior snapshot.

See validation-report.md for executed results and failures/retries. Remaining Phase 0 work: PDF layout gap review and real-browser end-to-end validation. External SMS/licensing service integrations are blocked. Parallel development can use the documented module/API boundaries and private databases, with shared core-file/migration coordination and human review; do not treat this as production-ready or Phase 0 fully complete.
