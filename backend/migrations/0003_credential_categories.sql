ALTER TABLE credentials ADD COLUMN document_kind VARCHAR(20) NOT NULL DEFAULT 'identity' CHECK(document_kind IN ('identity','professional','practice'));
