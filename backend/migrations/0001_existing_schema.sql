CREATE TABLE access_grants (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	grantee_user_id INTEGER NOT NULL,
	granted_by_user_id INTEGER,
	status VARCHAR(20) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id),
	FOREIGN KEY(grantee_user_id) REFERENCES users (id),
	FOREIGN KEY(granted_by_user_id) REFERENCES users (id)
);

CREATE TABLE announcements (
	id INTEGER NOT NULL,
	kind VARCHAR(40) NOT NULL,
	title VARCHAR(200) NOT NULL,
	location VARCHAR(200),
	starts_at DATETIME,
	details TEXT,
	shelter_id INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id)
);

CREATE TABLE appointments (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	facility VARCHAR(200) NOT NULL,
	scheduled_at DATETIME NOT NULL,
	kind VARCHAR(80) NOT NULL,
	notes TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE TABLE attachments (
	id INTEGER NOT NULL,
	entry_id INTEGER NOT NULL,
	filename VARCHAR(255) NOT NULL,
	stored_name VARCHAR(255) NOT NULL,
	mime_type VARCHAR(120),
	PRIMARY KEY (id),
	FOREIGN KEY(entry_id) REFERENCES medical_entries (id)
);

CREATE TABLE complaints (
	id INTEGER NOT NULL,
	shelter_id INTEGER,
	region VARCHAR(80),
	category VARCHAR(80) NOT NULL,
	description TEXT NOT NULL,
	source VARCHAR(40) NOT NULL,
	submitted_by INTEGER,
	status VARCHAR(30) NOT NULL,
	photo_stored_name VARCHAR(255),
	created_at DATETIME NOT NULL,
	resolved_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(submitted_by) REFERENCES users (id)
);

CREATE TABLE criticality_reviews (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	reviewer_id INTEGER,
	classification VARCHAR(20) NOT NULL,
	note TEXT,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id),
	FOREIGN KEY(reviewer_id) REFERENCES users (id)
);

CREATE TABLE dependencies (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	kind VARCHAR(40) NOT NULL,
	device_name VARCHAR(160),
	supply_description VARCHAR(200),
	supply_level_percent INTEGER,
	hours_remaining INTEGER,
	notes TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE TABLE dialysis_seats (
	id INTEGER NOT NULL,
	facility_name VARCHAR(200) NOT NULL,
	region VARCHAR(80) NOT NULL,
	seats_available INTEGER NOT NULL,
	next_opening DATETIME,
	notes VARCHAR(240),
	PRIMARY KEY (id)
);

CREATE TABLE dialysis_sessions (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	facility_name VARCHAR(200) NOT NULL,
	scheduled_at DATETIME NOT NULL,
	status VARCHAR(20) NOT NULL,
	seat_note VARCHAR(160),
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE TABLE donations (
	id INTEGER NOT NULL,
	donor_id INTEGER NOT NULL,
	kind VARCHAR(20) NOT NULL,
	amount FLOAT,
	currency VARCHAR(8),
	item_description VARCHAR(200),
	target_type VARCHAR(20) NOT NULL,
	target_shelter_id INTEGER,
	target_profile_id INTEGER,
	cause_label VARCHAR(200),
	status VARCHAR(20) NOT NULL,
	coordinator_id INTEGER,
	from_recommendation BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(donor_id) REFERENCES users (id),
	FOREIGN KEY(target_shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(target_profile_id) REFERENCES profiles (id),
	FOREIGN KEY(coordinator_id) REFERENCES users (id)
);

CREATE TABLE history_snapshots (
	id INTEGER NOT NULL,
	month VARCHAR(7) NOT NULL,
	shelter_id INTEGER NOT NULL,
	shortage_count INTEGER NOT NULL,
	occupancy INTEGER NOT NULL,
	complaint_count INTEGER NOT NULL,
	critical_count INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id)
);

CREATE TABLE inventory_items (
	id INTEGER NOT NULL,
	shelter_id INTEGER NOT NULL,
	item_name VARCHAR(160) NOT NULL,
	category VARCHAR(40) NOT NULL,
	quantity INTEGER NOT NULL,
	unit VARCHAR(40),
	status VARCHAR(20) NOT NULL,
	is_equipment BOOLEAN NOT NULL,
	is_specialized BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id)
);

CREATE TABLE medical_entries (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	entry_type VARCHAR(40) NOT NULL,
	title VARCHAR(200) NOT NULL,
	details TEXT,
	occurred_on DATE,
	author_type VARCHAR(20) NOT NULL,
	author_user_id INTEGER,
	facility_name VARCHAR(200),
	doctor_name VARCHAR(160),
	result_text TEXT,
	vaccine_status VARCHAR(20),
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id),
	FOREIGN KEY(author_user_id) REFERENCES users (id)
);

CREATE TABLE ngo_requests (
	id INTEGER NOT NULL,
	ngo_user_id INTEGER NOT NULL,
	organization VARCHAR(160),
	description TEXT NOT NULL,
	shelter_id INTEGER,
	status VARCHAR(20) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(ngo_user_id) REFERENCES users (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id)
);

CREATE TABLE outbreaks (
	id INTEGER NOT NULL,
	shelter_id INTEGER NOT NULL,
	suspected_illness VARCHAR(160) NOT NULL,
	case_count INTEGER NOT NULL,
	notes TEXT,
	status VARCHAR(20) NOT NULL,
	created_by INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE TABLE personal_supplies (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	item_name VARCHAR(160) NOT NULL,
	category VARCHAR(40) NOT NULL,
	quantity_note VARCHAR(120),
	status VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE TABLE pregnancies (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	weeks INTEGER NOT NULL,
	due_date DATE,
	risk_level VARCHAR(20) NOT NULL,
	risk_notes TEXT,
	next_appointment DATETIME,
	PRIMARY KEY (id),
	UNIQUE (profile_id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

CREATE TABLE profiles (
	id INTEGER NOT NULL,
	owner_user_id INTEGER,
	full_name VARCHAR(160) NOT NULL,
	relationship VARCHAR(40) NOT NULL,
	date_of_birth DATE,
	sex VARCHAR(20),
	blood_type VARCHAR(8),
	shelter_id INTEGER,
	disability BOOLEAN NOT NULL,
	disability_notes VARCHAR(240),
	emergency_contact_name VARCHAR(160),
	emergency_contact_phone VARCHAR(40),
	emergency_token VARCHAR(64) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(owner_user_id) REFERENCES users (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id),
	UNIQUE (emergency_token)
);

CREATE TABLE relocations (
	id INTEGER NOT NULL,
	shelter_id INTEGER NOT NULL,
	destination_shelter_id INTEGER,
	profile_id INTEGER,
	reason TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	created_by INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(destination_shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE TABLE resource_exchanges (
	id INTEGER NOT NULL,
	from_shelter_id INTEGER NOT NULL,
	to_shelter_id INTEGER NOT NULL,
	item_name VARCHAR(160) NOT NULL,
	quantity INTEGER NOT NULL,
	status VARCHAR(20) NOT NULL,
	needs_volunteer BOOLEAN NOT NULL,
	created_by INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(from_shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(to_shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE TABLE shelters (
	id INTEGER NOT NULL,
	name VARCHAR(160) NOT NULL,
	region VARCHAR(80) NOT NULL,
	kind VARCHAR(40) NOT NULL,
	address VARCHAR(200),
	capacity INTEGER NOT NULL,
	occupancy INTEGER NOT NULL,
	accessible BOOLEAN NOT NULL,
	accessible_spaces INTEGER NOT NULL,
	has_backup_power BOOLEAN NOT NULL,
	electricity_hours INTEGER NOT NULL,
	notes TEXT,
	PRIMARY KEY (id)
);

CREATE TABLE support_flags (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	flagged_by INTEGER,
	reason TEXT NOT NULL,
	includes_bullying BOOLEAN NOT NULL,
	status VARCHAR(20) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id),
	FOREIGN KEY(flagged_by) REFERENCES users (id)
);

CREATE TABLE tasks (
	id INTEGER NOT NULL,
	kind VARCHAR(40) NOT NULL,
	title VARCHAR(200) NOT NULL,
	details TEXT,
	location VARCHAR(200),
	scheduled_at DATETIME,
	shelter_id INTEGER,
	status VARCHAR(20) NOT NULL,
	assignee_user_id INTEGER,
	exchange_id INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id),
	FOREIGN KEY(assignee_user_id) REFERENCES users (id),
	FOREIGN KEY(exchange_id) REFERENCES resource_exchanges (id)
);

CREATE TABLE transport_requests (
	id INTEGER NOT NULL,
	profile_id INTEGER NOT NULL,
	requester_id INTEGER,
	destination VARCHAR(200) NOT NULL,
	destination_type VARCHAR(40) NOT NULL,
	wheelchair_required BOOLEAN NOT NULL,
	appointment_id INTEGER,
	status VARCHAR(20) NOT NULL,
	provider_user_id INTEGER,
	notes TEXT,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(profile_id) REFERENCES profiles (id),
	FOREIGN KEY(requester_id) REFERENCES users (id),
	FOREIGN KEY(appointment_id) REFERENCES appointments (id),
	FOREIGN KEY(provider_user_id) REFERENCES users (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL,
	full_name VARCHAR(160) NOT NULL,
	phone VARCHAR(40),
	email VARCHAR(160),
	password_hash VARCHAR(255) NOT NULL,
	role VARCHAR(40) NOT NULL,
	specialty VARCHAR(120),
	license_number VARCHAR(80),
	license_body VARCHAR(160),
	license_expires DATE,
	verification_status VARCHAR(40) NOT NULL,
	helper_type VARCHAR(40),
	shelter_id INTEGER,
	license_file VARCHAR(255),
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (phone),
	UNIQUE (email),
	FOREIGN KEY(shelter_id) REFERENCES shelters (id)
);
