CREATE TABLE contributors (
    id TEXT PRIMARY KEY,
    email_digest TEXT NOT NULL UNIQUE,
    email_ciphertext BLOB NOT NULL,
    verified_at TEXT,
    last_activity_at TEXT NOT NULL,
    blocked_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE submission_sessions (
    id TEXT PRIMARY KEY,
    contributor_id TEXT NOT NULL REFERENCES contributors(id),
    token_digest TEXT NOT NULL UNIQUE,
    csrf_digest TEXT UNIQUE,
    state TEXT NOT NULL CHECK (
        state IN ('pending', 'active', 'consumed', 'expired', 'revoked')
    ),
    submission_count INTEGER NOT NULL DEFAULT 0 CHECK (
        submission_count BETWEEN 0 AND 5
    ),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    consumed_at TEXT
);

CREATE INDEX submission_sessions_contributor_idx
    ON submission_sessions(contributor_id, state);

CREATE TABLE submissions (
    id TEXT PRIMARY KEY,
    contributor_id TEXT NOT NULL REFERENCES contributors(id),
    intent TEXT NOT NULL CHECK (
        intent IN (
            'installation_result',
            'documentation_citation',
            'data_correction'
        )
    ),
    status TEXT NOT NULL CHECK (
        status IN (
            'received',
            'held',
            'under_review',
            'needs_information',
            'accepted',
            'partially_accepted',
            'rejected',
            'duplicate',
            'withdrawn'
        )
    ),
    target_component_id TEXT,
    target_edge_key_json TEXT CHECK (
        target_edge_key_json IS NULL OR json_valid(target_edge_key_json)
    ),
    target_namespace TEXT,
    target_identifier TEXT,
    summary TEXT NOT NULL,
    context_json TEXT NOT NULL CHECK (json_valid(context_json)),
    priority TEXT NOT NULL CHECK (priority IN ('normal', 'high', 'safety')),
    abuse_digest TEXT NOT NULL,
    terms_version TEXT NOT NULL,
    evidence_license_version TEXT NOT NULL,
    consented_at TEXT NOT NULL,
    public_reason TEXT,
    evidence_state TEXT NOT NULL DEFAULT 'pending' CHECK (
        evidence_state IN ('pending', 'available', 'unavailable')
    ),
    integration_state TEXT NOT NULL DEFAULT 'not_applicable' CHECK (
        integration_state IN ('not_applicable', 'pending', 'integrated')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    withdrawn_at TEXT
);

CREATE INDEX submissions_contributor_idx
    ON submissions(contributor_id, created_at);
CREATE INDEX submissions_queue_idx
    ON submissions(status, priority, created_at);

CREATE TABLE submission_capabilities (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    purpose TEXT NOT NULL CHECK (
        purpose IN ('status', 'follow_up', 'withdrawal')
    ),
    token_digest TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX submission_capabilities_one_live_idx
    ON submission_capabilities(submission_id, purpose)
    WHERE consumed_at IS NULL AND revoked_at IS NULL;

CREATE TABLE submission_claims (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    claim_type TEXT NOT NULL CHECK (
        claim_type IN (
            'observed_identifier',
            'attribute',
            'installation_outcome',
            'document_assertion',
            'supersession_assertion',
            'correction'
        )
    ),
    proposed_json TEXT NOT NULL CHECK (json_valid(proposed_json)),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'accepted', 'rejected', 'duplicate')
    ),
    decision_reason_code TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    UNIQUE(submission_id, id)
);

CREATE INDEX submission_claims_submission_idx
    ON submission_claims(submission_id, status);

CREATE TABLE submission_artifacts (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    storage_key TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    declared_media_type TEXT NOT NULL,
    detected_media_type TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL,
    stored_sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    scan_status TEXT NOT NULL CHECK (
        scan_status IN ('pending', 'clean', 'rejected', 'failed')
    ),
    retention_class TEXT NOT NULL CHECK (
        retention_class IN ('unverified', 'rejected', 'accepted_evidence')
    ),
    created_at TEXT NOT NULL,
    purge_after TEXT,
    purged_at TEXT
);

CREATE INDEX submission_artifacts_submission_idx
    ON submission_artifacts(submission_id, scan_status);

CREATE TABLE email_outbox (
    id TEXT PRIMARY KEY,
    submission_id TEXT REFERENCES submissions(id),
    template TEXT NOT NULL,
    recipient_ciphertext BLOB NOT NULL,
    template_data_json TEXT NOT NULL CHECK (json_valid(template_data_json)),
    state TEXT NOT NULL DEFAULT 'pending' CHECK (
        state IN ('pending', 'sending', 'sent', 'retry', 'failed')
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (
        attempt_count BETWEEN 0 AND 6
    ),
    next_attempt_at TEXT NOT NULL,
    claimed_at TEXT,
    provider_reference TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    sent_at TEXT
);

CREATE INDEX email_outbox_delivery_idx
    ON email_outbox(state, next_attempt_at, created_at);

CREATE TABLE rate_limit_events (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    subject_digest TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX rate_limit_events_lookup_idx
    ON rate_limit_events(scope, subject_digest, occurred_at);
