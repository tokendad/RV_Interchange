CREATE TABLE reviewer_roles (
    email_digest TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('trusted', 'admin')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    granted_at TEXT NOT NULL,
    revoked_at TEXT,
    PRIMARY KEY (email_digest, role)
);

CREATE TABLE reviewer_capabilities (
    email_digest TEXT NOT NULL,
    capability TEXT NOT NULL CHECK (capability IN ('publisher')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    granted_at TEXT NOT NULL,
    revoked_at TEXT,
    PRIMARY KEY (email_digest, capability)
);

CREATE TABLE review_decisions (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    claim_id TEXT REFERENCES submission_claims(id),
    reviewer_digest TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('decision', 'request_information')),
    reason_code TEXT NOT NULL,
    note TEXT,
    prior_status TEXT NOT NULL,
    resulting_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE review_assessments (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    claim_id TEXT REFERENCES submission_claims(id),
    reviewer_digest TEXT NOT NULL,
    assessment TEXT NOT NULL CHECK (assessment IN ('endorse', 'dispute', 'spam')),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX review_queue_idx ON submissions(status, priority, created_at, id);
CREATE INDEX review_decisions_submission_idx ON review_decisions(submission_id, created_at);
CREATE INDEX review_assessments_submission_idx ON review_assessments(submission_id, created_at);
