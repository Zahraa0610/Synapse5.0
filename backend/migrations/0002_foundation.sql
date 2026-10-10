ALTER TABLE users ADD COLUMN requested_role VARCHAR(40);
CREATE TABLE auth_sessions (
 id VARCHAR(64) PRIMARY KEY NOT NULL,
 user_id INTEGER NOT NULL REFERENCES users(id),
 expires_at DATETIME NOT NULL,
 revoked BOOLEAN NOT NULL DEFAULT 0
);
CREATE INDEX ix_auth_sessions_user_id ON auth_sessions(user_id);
CREATE TABLE credentials (
 id INTEGER PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES users(id),
 filename VARCHAR(255) NOT NULL,
 stored_name VARCHAR(255) NOT NULL UNIQUE,
 mime_type VARCHAR(120) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
 reviewer_id INTEGER REFERENCES users(id),
 review_note TEXT,
 created_at DATETIME NOT NULL,
 CHECK(reviewer_id IS NULL OR reviewer_id != user_id)
);
CREATE INDEX ix_credentials_user_id ON credentials(user_id);
CREATE TABLE organizations (id INTEGER PRIMARY KEY, name VARCHAR(160) NOT NULL UNIQUE, kind VARCHAR(40) NOT NULL);
CREATE TABLE organization_members (
 id INTEGER PRIMARY KEY,
 organization_id INTEGER NOT NULL REFERENCES organizations(id),
 user_id INTEGER NOT NULL REFERENCES users(id),
 UNIQUE(organization_id,user_id)
);
CREATE INDEX ix_organization_members_user_id ON organization_members(user_id);
CREATE INDEX ix_organization_members_organization_id ON organization_members(organization_id);
CREATE INDEX ix_profiles_owner_user_id ON profiles(owner_user_id);
CREATE INDEX ix_profiles_shelter_id ON profiles(shelter_id);
CREATE INDEX ix_medical_entries_profile_id ON medical_entries(profile_id);
CREATE INDEX ix_access_grants_profile_grantee ON access_grants(profile_id,grantee_user_id,status);
