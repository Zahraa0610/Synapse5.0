# Database foundation

SQLite remains supported; PostgreSQL migration is not approved or performed. SQLite is practical for hackathon/local development and isolated tests. For concurrent institutional deployment, PostgreSQL is justified by write concurrency, managed backups and row locking. Migrate only after approval: encrypted verified snapshot, immutable schema revisions, copied data, FK/count checks, staging validation and planned cutover with rollback. Do not share a live SQLite file between developers.

## Existing schema
Profile.owner_user_id represents the owning patient/caregiver; caregiver dependents reuse profiles with relationship. Medical conditions, allergies, medication and vaccination records are MedicalEntry.entry_type values; these are not separate tables. Roles are User.role strings, not a role join table. Shelter assignment uses User.shelter_id. Organizations/members and credential review are additive Phase 0 tables. Dependencies, appointments, dialysis, transport, donations and complaints already exist; NGO requests represent coordination, while Ministry reports are computed aggregates.

## Versioned migrations
0001_existing_schema.sql is the frozen existing schema, without demo/user data. On a legacy database the runner verifies the existing table set before recording baseline; on a fresh database it creates the baseline. 0002_foundation.sql adds User.requested_role, auth_sessions, credentials, organizations and organization_members, FK relationships, credential status/self-review constraints, membership uniqueness, and relationship indexes. 0003_credential_categories.sql adds identity/professional/practice categories; clinical approval requires both identity and professional evidence. Migrations acquire a SQLite write lock and commit atomically; recorded revisions make reruns idempotent. No columns or original tables are removed. Foreign keys are enabled on application connections. Existing orphan rows are reported with PRAGMA foreign_key_check, not deleted.

Run migrations explicitly only against the intended development/copy database. Startup performs no migration unless AUTO_MIGRATE is explicitly configured in tests. Original backend/maak.db was never migrated or seeded. Migrations were exercised on fresh DBs, repeated upgrades, synthetic legacy data and a copy of the verified 25-table recovery snapshot; existing rows/columns remained identical and the snapshot copy had zero FK violations.

## Compatibility and remaining work
Old JWTs have no session ID and are rejected; users must sign in again. Legacy medical data is unchanged. Existing privileged accounts need explicit authorization review; do not automatically trust older self-selected roles or seed credentials. Existing approved credentials retain their status during migration; audit them before deploying. Backfill requested roles only after operator review.

New credentials use pending/approved/rejected; the API queue includes legacy documents_received/checking during transition. Legacy User.license_file is preserved. Do not drop it until private-file migration and caller compatibility are verified. The organizations tables establish relationships but have no new user-facing module. Future caregiver multi-user grants, normalized medications and professional licenses, shelter membership history, money decimals and audit events require separate reviewed revisions. AccessGrant currently has a query index; adding uniqueness needs a non-destructive duplicate reconciliation plan first. Volunteer task and donation allocation races need conditional writes/transactions in their feature phases.

## Tables and foreign keys

| Model | Table | Foreign keys |
|---|---|---|
| User | `users` | shelters.id |
| Shelter | `shelters` | None |
| Profile | `profiles` | users.id, shelters.id |
| MedicalEntry | `medical_entries` | profiles.id, users.id |
| Attachment | `attachments` | medical_entries.id |
| AccessGrant | `access_grants` | profiles.id, users.id, users.id |
| Dependency | `dependencies` | profiles.id |
| PersonalSupply | `personal_supplies` | profiles.id |
| DialysisSession | `dialysis_sessions` | profiles.id |
| DialysisSeat | `dialysis_seats` | None |
| Pregnancy | `pregnancies` | profiles.id |
| InventoryItem | `inventory_items` | shelters.id |
| ResourceExchange | `resource_exchanges` | shelters.id, shelters.id, users.id |
| Task | `tasks` | shelters.id, users.id, resource_exchanges.id |
| Announcement | `announcements` | shelters.id |
| Relocation | `relocations` | shelters.id, shelters.id, profiles.id, users.id |
| Outbreak | `outbreaks` | shelters.id, users.id |
| Appointment | `appointments` | profiles.id |
| TransportRequest | `transport_requests` | profiles.id, users.id, appointments.id, users.id |
| SupportFlag | `support_flags` | profiles.id, users.id |
| Complaint | `complaints` | shelters.id, users.id |
| Donation | `donations` | users.id, shelters.id, profiles.id, users.id |
| NgoRequest | `ngo_requests` | users.id, shelters.id |
| HistorySnapshot | `history_snapshots` | shelters.id |
| CriticalityReview | `criticality_reviews` | profiles.id, users.id |
| AuthSession | `auth_sessions` | users.id |
| Credential | `credentials` | users.id, users.id |
| Organization | `organizations` | None |
| OrganizationMember | `organization_members` | organizations.id, users.id |
