CREATE UNIQUE INDEX submission_artifacts_submission_id_id_uq
    ON submission_artifacts(submission_id, id);

CREATE UNIQUE INDEX submission_claims_submission_id_id_uq
    ON submission_claims(submission_id, id);

CREATE TABLE observation_drafts (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    created_by_digest TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'manufacturer_page', 'manufacturer_pdf', 'manual_measurement',
        'dataplate_photo', 'dealer_call', 'field_report', 'other',
        'retailer_page', 'retailer_prose', 'forum_post'
    )),
    source_name TEXT NOT NULL CHECK (length(source_name) BETWEEN 1 AND 300),
    source_url TEXT,
    raw_content TEXT NOT NULL CHECK (length(raw_content) BETWEEN 1 AND 12000),
    extracted_json TEXT NOT NULL CHECK (json_valid(extracted_json)),
    default_source_tier INTEGER NOT NULL CHECK (default_source_tier BETWEEN 1 AND 9),
    state TEXT NOT NULL CHECK (state IN ('draft', 'ready', 'promoted', 'superseded')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(submission_id, id)
);

CREATE TABLE observation_draft_claims (
    submission_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (draft_id, claim_id),
    FOREIGN KEY (submission_id, draft_id) REFERENCES observation_drafts(submission_id, id),
    FOREIGN KEY (submission_id, claim_id) REFERENCES submission_claims(submission_id, id)
);

CREATE TABLE observation_draft_artifacts (
    submission_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    PRIMARY KEY (draft_id, artifact_id),
    FOREIGN KEY (submission_id, draft_id) REFERENCES observation_drafts(submission_id, id),
    FOREIGN KEY (submission_id, artifact_id) REFERENCES submission_artifacts(submission_id, id)
);

CREATE TABLE promotion_receipts (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    observation_draft_id TEXT NOT NULL UNIQUE REFERENCES observation_drafts(id),
    canonical_observation_id INTEGER NOT NULL,
    canonical_payload_sha256 TEXT NOT NULL CHECK (length(canonical_payload_sha256) = 64),
    promoted_by_digest TEXT NOT NULL,
    source_tier INTEGER NOT NULL CHECK (source_tier BETWEEN 1 AND 9),
    promoted_at TEXT NOT NULL,
    integration_state TEXT NOT NULL DEFAULT 'pending'
        CHECK (integration_state IN ('pending', 'integrated', 'not_applicable'))
);

CREATE TABLE promotion_replay_keys (
    idempotency_key TEXT PRIMARY KEY,
    promotion_id TEXT NOT NULL REFERENCES promotion_receipts(id),
    request_sha256 TEXT NOT NULL CHECK (length(request_sha256) = 64),
    created_at TEXT NOT NULL
);

CREATE TABLE promotion_events (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    observation_draft_id TEXT NOT NULL,
    promotion_id TEXT REFERENCES promotion_receipts(id),
    actor_digest TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN (
        'draft_created', 'draft_ready', 'promoted', 'promotion_reconciled'
    )),
    prior_state TEXT,
    resulting_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (submission_id, observation_draft_id)
        REFERENCES observation_drafts(submission_id, id)
);

CREATE INDEX promotion_events_draft_idx ON promotion_events(observation_draft_id, created_at, id);
