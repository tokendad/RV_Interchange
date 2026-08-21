import json
import sqlite3
import uuid

import pytest

from intake import db, repositories


NOW = "2026-08-21T12:00:00+00:00"
PENDING_EXPIRY = "2026-08-21T12:15:00+00:00"
SESSION_EXPIRY = "2026-08-22T12:00:00+00:00"
CAPABILITY_EXPIRY = "2026-09-20T12:00:00+00:00"


@pytest.fixture
def persisted(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        yield db, repositories, conn


def _contributor(repositories, conn):
    return repositories.ContributorRepository(conn).create(
        "email-digest", b"encrypted-email", NOW
    )


def _active_session(repositories, conn, contributor_id):
    sessions = repositories.SessionRepository(conn)
    session_id = sessions.create_pending(
        contributor_id, "verification-digest", PENDING_EXPIRY, NOW
    )
    row = sessions.activate(
        "verification-digest",
        "session-digest",
        "csrf-digest",
        SESSION_EXPIRY,
        NOW,
    )
    assert row["id"] == session_id
    return session_id


def _submission_payload(contributor_id):
    return {
        "contributor_id": contributor_id,
        "intent": "installation_result",
        "status": "received",
        "target_component_id": "component-1",
        "target_edge_key_json": {
            "from_component_id": "component-1",
            "to_component_id": "component-2",
            "type": "replacement",
        },
        "target_namespace": "mfg",
        "target_identifier": "PART-1",
        "summary": "A verified installation result.",
        "context_json": {"z": 1, "a": ["first"]},
        "priority": "normal",
        "abuse_digest": "rotating-abuse-digest",
        "terms_version": "2026-08-21",
        "evidence_license_version": "CC0-1.0",
        "consented_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }


def _children():
    return (
        [
            {
                "claim_type": "installation_outcome",
                "proposed_json": {"worked": True, "notes": "confirmed"},
                "created_at": NOW,
            }
        ],
        [
            {
                "storage_key": "submission/artifact.webp",
                "original_name": "photo.webp",
                "declared_media_type": "image/webp",
                "detected_media_type": "image/webp",
                "raw_sha256": "a" * 64,
                "stored_sha256": "b" * 64,
                "size_bytes": 123,
                "width": 20,
                "height": 10,
                "scan_status": "clean",
                "retention_class": "unverified",
                "created_at": NOW,
                "purge_after": "2026-08-28T12:00:00+00:00",
            }
        ],
        [
            {
                "purpose": "status",
                "token_digest": "status-digest",
                "expires_at": CAPABILITY_EXPIRY,
                "created_at": NOW,
            },
            {
                "purpose": "follow_up",
                "token_digest": "follow-up-digest",
                "expires_at": CAPABILITY_EXPIRY,
                "created_at": NOW,
            },
            {
                "purpose": "withdrawal",
                "token_digest": "withdrawal-digest",
                "expires_at": CAPABILITY_EXPIRY,
                "created_at": NOW,
            },
        ],
        [
            {
                "template": "submission_received",
                "recipient_ciphertext": b"encrypted-email",
                "template_data_json": {"submission": "receipt", "z": 2},
                "next_attempt_at": NOW,
                "created_at": NOW,
            }
        ],
    )


def test_repositories_create_random_uuid_identifiers(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        session_id = _active_session(repositories, conn, contributor_id)
        claims, artifacts, capabilities, outbox = _children()
        submission_id = repositories.SubmissionRepository(
            conn
        ).create_with_children(
            _submission_payload(contributor_id),
            claims,
            artifacts,
            capabilities,
            outbox,
        )

    public_ids = [contributor_id, session_id, submission_id]
    public_ids.extend(
        row[0]
        for table in (
            "submission_claims",
            "submission_artifacts",
            "submission_capabilities",
            "email_outbox",
        )
        for row in conn.execute(f"SELECT id FROM {table}")
    )
    assert all(str(uuid.UUID(value)) == value for value in public_ids)


def test_submission_accepts_server_preallocated_uuid_for_every_child(persisted):
    db, repositories, conn = persisted
    preallocated_id = "4cf3371c-80f4-40cd-b07d-c085280cfa80"

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        payload = _submission_payload(contributor_id)
        payload["id"] = preallocated_id
        claims, artifacts, capabilities, outbox = _children()
        submission_id = repositories.SubmissionRepository(conn).create_with_children(
            payload,
            claims,
            artifacts,
            capabilities,
            outbox,
        )

    assert submission_id == preallocated_id
    assert conn.execute("SELECT id FROM submissions").fetchone()[0] == preallocated_id
    for table in (
        "submission_claims",
        "submission_artifacts",
        "submission_capabilities",
        "email_outbox",
    ):
        assert {
            row[0] for row in conn.execute(f"SELECT submission_id FROM {table}")
        } == {preallocated_id}


@pytest.mark.parametrize(
    "invalid_id",
    ["not-a-uuid", "4CF3371C-80F4-40CD-B07D-C085280CFA80"],
)
def test_submission_rejects_invalid_preallocated_uuid_before_writes(
    persisted, invalid_id
):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
    payload = _submission_payload(contributor_id)
    payload["id"] = invalid_id

    with pytest.raises(ValueError, match="invalid submission id"):
        with db.transaction(conn):
            repositories.SubmissionRepository(conn).create_with_children(
                payload, *_children()
            )

    assert conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0] == 0
    for table in (
        "submission_claims",
        "submission_artifacts",
        "submission_capabilities",
        "email_outbox",
    ):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_token_digests_are_unique(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        sessions = repositories.SessionRepository(conn)
        sessions.create_pending(
            contributor_id, "duplicate-digest", PENDING_EXPIRY, NOW
        )
        with pytest.raises(sqlite3.IntegrityError):
            sessions.create_pending(
                contributor_id, "duplicate-digest", PENDING_EXPIRY, NOW
            )


def test_session_activation_authentication_and_five_submission_reservation(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        sessions = repositories.SessionRepository(conn)
        session_id = _active_session(repositories, conn, contributor_id)

        authenticated = sessions.authenticate(
            "session-digest", "2026-08-21T13:00:00+00:00"
        )
        assert authenticated["id"] == session_id
        assert authenticated["csrf_digest"] == "csrf-digest"
        assert sessions.authenticate("verification-digest", NOW) is None

        for _ in range(5):
            sessions.reserve_submission(session_id)
        with pytest.raises(repositories.SubmissionLimitExceeded):
            sessions.reserve_submission(session_id)

    assert conn.execute(
        "SELECT submission_count FROM submission_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()[0] == 5


def test_expired_or_blocked_session_does_not_authenticate(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        _active_session(repositories, conn, contributor_id)

        sessions = repositories.SessionRepository(conn)
        assert sessions.authenticate(
            "session-digest", "2026-08-23T12:00:00+00:00"
        ) is None
        conn.execute(
            "UPDATE contributors SET blocked_at = ? WHERE id = ?",
            (NOW, contributor_id),
        )
        assert sessions.authenticate("session-digest", NOW) is None


def test_submission_and_all_children_rollback_together(persisted):
    db, repositories, conn = persisted
    contributor_id = None

    with pytest.raises(RuntimeError, match="abort service transaction"):
        with db.transaction(conn):
            contributor_id = _contributor(repositories, conn)
            claims, artifacts, capabilities, outbox = _children()
            repositories.SubmissionRepository(conn).create_with_children(
                _submission_payload(contributor_id),
                claims,
                artifacts,
                capabilities,
                outbox,
            )
            raise RuntimeError("abort service transaction")

    assert contributor_id is not None
    for table in (
        "contributors",
        "submissions",
        "submission_claims",
        "submission_artifacts",
        "submission_capabilities",
        "email_outbox",
    ):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_outbox_child_ignores_conflicting_caller_submission_id(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        submissions = repositories.SubmissionRepository(conn)
        conflicting_id = submissions.create_with_children(
            _submission_payload(contributor_id), [], [], [], []
        )
        outbox = _children()[3]
        outbox[0]["submission_id"] = conflicting_id

        submission_id = submissions.create_with_children(
            _submission_payload(contributor_id), [], [], [], outbox
        )

    assert submission_id != conflicting_id
    assert conn.execute(
        "SELECT submission_id FROM email_outbox"
    ).fetchone()[0] == submission_id


def test_json_is_stored_compact_and_with_sorted_keys(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        claims, artifacts, capabilities, outbox = _children()
        submission_id = repositories.SubmissionRepository(
            conn
        ).create_with_children(
            _submission_payload(contributor_id),
            claims,
            artifacts,
            capabilities,
            outbox,
        )

    submission = conn.execute(
        "SELECT context_json, target_edge_key_json FROM submissions WHERE id = ?",
        (submission_id,),
    ).fetchone()
    assert submission["context_json"] == '{"a":["first"],"z":1}'
    assert submission["target_edge_key_json"] == (
        '{"from_component_id":"component-1",'
        '"to_component_id":"component-2","type":"replacement"}'
    )
    assert conn.execute(
        "SELECT proposed_json FROM submission_claims"
    ).fetchone()[0] == '{"notes":"confirmed","worked":true}'
    assert conn.execute(
        "SELECT template_data_json FROM email_outbox"
    ).fetchone()[0] == '{"submission":"receipt","z":2}'


def test_public_status_follow_up_and_withdrawal_are_redacted_and_bounded(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        claims, artifacts, capabilities, outbox = _children()
        submissions = repositories.SubmissionRepository(conn)
        submission_id = submissions.create_with_children(
            _submission_payload(contributor_id),
            claims,
            artifacts,
            capabilities,
            outbox,
        )
        conn.execute(
            "UPDATE submissions SET status = ? WHERE id = ?",
            ("needs_information", submission_id),
        )
        submissions.append_follow_up(
            submission_id, {"message": "Additional measurements."}, NOW
        )

        public = submissions.public_status(submission_id)
        assert public == {
            "submission_id": submission_id,
            "status": "under_review",
            "public_reason": None,
            "evidence_state": "pending",
            "integration_state": "not_applicable",
            "updated_at": NOW,
        }
        submissions.withdraw(submission_id, NOW)

    context = json.loads(
        conn.execute(
            "SELECT context_json FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()[0]
    )
    assert context["follow_ups"] == [{"message": "Additional measurements."}]
    assert conn.execute(
        "SELECT status FROM submissions WHERE id = ?", (submission_id,)
    ).fetchone()[0] == "withdrawn"
    assert repositories.SubmissionRepository(conn).public_status("missing") is None


def test_live_capability_is_unique_per_submission_and_purpose(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        claims, artifacts, capabilities, outbox = _children()
        submission_id = repositories.SubmissionRepository(
            conn
        ).create_with_children(
            _submission_payload(contributor_id),
            claims,
            artifacts,
            capabilities,
            outbox,
        )
        capability_repository = repositories.CapabilityRepository(conn)
        with pytest.raises(sqlite3.IntegrityError):
            capability_repository.create(
                submission_id,
                "status",
                "replacement-status-digest",
                CAPABILITY_EXPIRY,
                NOW,
            )


def test_specialized_repositories_use_the_callers_connection(persisted):
    db, repositories, conn = persisted

    with db.transaction(conn):
        contributor_id = _contributor(repositories, conn)
        claims, artifacts, capabilities, outbox = _children()
        submission_id = repositories.SubmissionRepository(
            conn
        ).create_with_children(
            _submission_payload(contributor_id), claims, [], [], []
        )
        artifact_id = repositories.ArtifactRepository(conn).create(
            submission_id, artifacts[0]
        )
        capability_id = repositories.CapabilityRepository(conn).create(
            submission_id,
            "status",
            "new-status-digest",
            CAPABILITY_EXPIRY,
            NOW,
        )
        outbox_id = repositories.OutboxRepository(conn).enqueue(
            {**outbox[0], "submission_id": submission_id}
        )
        rates = repositories.RateLimitRepository(conn)
        event_id = rates.record("verification", "ip-digest", NOW)
        assert rates.count_since(
            "verification", "ip-digest", "2026-08-21T11:00:00+00:00"
        ) == 1

    assert all(
        str(uuid.UUID(value)) == value
        for value in (artifact_id, capability_id, outbox_id, event_id)
    )
