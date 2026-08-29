import json

from intake import repositories


def seed_submission(conn, status="accepted"):
    contributor = repositories.ContributorRepository(conn).create(
        "promotion-contributor-" + status + str(conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]), b"cipher", "2026-01-01T00:00:00Z"
    )
    return repositories.SubmissionRepository(conn).create_with_children(
        {
            "contributor_id": contributor,
            "intent": "installation_result",
            "status": status,
            "summary": "Observed fit",
            "context_json": {},
            "priority": "normal",
            "abuse_digest": "abuse",
            "terms_version": "v1",
            "evidence_license_version": "v1",
            "consented_at": "2026-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        [],
        [],
        [],
        [],
    )


def seed_accepted_claim(conn, submission_id):
    claim_id = "claim-" + submission_id
    conn.execute(
        """INSERT INTO submission_claims
           (id, submission_id, claim_type, proposed_json, status, created_at, decided_at)
           VALUES (?, ?, 'attribute', ?, 'accepted', ?, ?)""",
        (claim_id, submission_id, json.dumps({"model": "SF-30FQ"}),
         "2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"),
    )
    return claim_id


def seed_accepted_evidence(conn):
    submission_id = seed_submission(conn)
    claim_id = seed_accepted_claim(conn, submission_id)
    artifact_id = "artifact-" + submission_id
    conn.execute(
        """INSERT INTO submission_artifacts
           (id, submission_id, storage_key, original_name, declared_media_type,
            detected_media_type, raw_sha256, stored_sha256, size_bytes, width,
            height, scan_status, retention_class, created_at)
           VALUES (?, ?, ?, 'plate.jpg', 'image/jpeg', 'image/jpeg', ?, ?,
                   10, 1, 1, 'clean', 'accepted_evidence', ?)""",
        (artifact_id, submission_id, "storage/" + artifact_id, "a" * 64,
         "b" * 64, "2026-01-01T00:00:00Z"),
    )
    return conn, submission_id, claim_id, artifact_id
