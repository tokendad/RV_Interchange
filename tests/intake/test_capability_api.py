import asyncio
import io
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from intake import db
from intake import artifacts as artifact_module
from intake.routers import capabilities as capability_routes
from intake.app import create_app
from intake.config import Settings
from intake.repositories import (
    CapabilityRepository,
    ContributorRepository,
    SubmissionRepository,
)
from intake.security import ContactCipher, TokenCodec


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
STATUS_SECRET = "status-capability-secret-" * 2
FOLLOW_UP_SECRET = "follow-up-capability-secret-" * 2
WITHDRAWAL_SECRET = "withdrawal-capability-secret-" * 2
OTHER_STATUS_SECRET = "other-status-capability-secret-" * 2
GENERIC_NOT_FOUND = {"detail": "capability not found"}
MISSING = object()


class MutableClock:
    def __init__(self, value: datetime):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


@dataclass
class CapabilityHarness:
    settings: Settings
    client: TestClient
    clock: MutableClock
    submission_id: str
    other_submission_id: str

    def follow_up(self, metadata: dict, artifacts=()):
        parts = [("metadata", (None, json.dumps(metadata), "application/json"))]
        parts.extend(
            ("artifacts", (filename, content, media_type))
            for filename, content, media_type in artifacts
        )
        return self.client.post(
            f"/submission/v1/submissions/{self.submission_id}/follow-ups",
            files=parts,
        )


def _submission(contributor_id: str, *, summary: str) -> dict[str, object]:
    now = NOW.isoformat()
    return {
        "contributor_id": contributor_id,
        "intent": "installation_result",
        "target_component_id": "component-a",
        "summary": summary,
        "context_json": {
            "kind": "installation_result",
            "outcome": "success",
            "notes": "Original evidence remains immutable.",
        },
        "priority": "normal",
        "abuse_digest": "private-abuse-digest",
        "terms_version": "2026-08-21",
        "evidence_license_version": "CC0-1.0",
        "consented_at": now,
        "public_reason": "Waiting for an additional measurement.",
        "created_at": now,
        "updated_at": now,
    }


def _capabilities(codec: TokenCodec, secrets: dict[str, str]):
    expires_at = (NOW + timedelta(days=30)).isoformat()
    return [
        {
            "purpose": purpose,
            "token_digest": codec.digest(secret),
            "expires_at": expires_at,
            "created_at": NOW.isoformat(),
        }
        for purpose, secret in secrets.items()
    ]


@pytest.fixture
def harness(tmp_path):
    settings = Settings.for_tests(tmp_path)
    clock = MutableClock(NOW)
    client = TestClient(
        create_app(settings, turnstile_verifier=object(), clock=clock),
        base_url="https://testserver",
    )
    with client:
        codec = TokenCodec(settings.read_key("token"))
        cipher = ContactCipher(settings.read_key("contact"))
        with db.connect(settings.database_path) as conn:
            with db.transaction(conn):
                contributors = ContributorRepository(conn)
                first_contributor = contributors.create(
                    codec.digest("first@example.com"),
                    cipher.encrypt("first@example.com"),
                    NOW.isoformat(),
                )
                second_contributor = contributors.create(
                    codec.digest("second@example.com"),
                    cipher.encrypt("second@example.com"),
                    NOW.isoformat(),
                )
                submissions = SubmissionRepository(conn)
                submission_id = submissions.create_with_children(
                    _submission(first_contributor, summary="First private summary."),
                    [
                        {
                            "claim_type": "installation_outcome",
                            "proposed_json": {"private": "claim detail"},
                            "created_at": NOW.isoformat(),
                        }
                    ],
                    [],
                    _capabilities(
                        codec,
                        {
                            "status": STATUS_SECRET,
                            "follow_up": FOLLOW_UP_SECRET,
                            "withdrawal": WITHDRAWAL_SECRET,
                        },
                    ),
                    [],
                )
                other_submission_id = submissions.create_with_children(
                    _submission(second_contributor, summary="Second private summary."),
                    [],
                    [],
                    _capabilities(codec, {"status": OTHER_STATUS_SECRET}),
                    [],
                )
        yield CapabilityHarness(
            settings,
            client,
            clock,
            submission_id,
            other_submission_id,
        )


def _status(harness: CapabilityHarness, submission_id: str, capability: str):
    return harness.client.post(
        "/submission/v1/status-queries",
        json={"submission_id": submission_id, "capability": capability},
    )


def _image_bytes(*, exif: bool = False) -> bytes:
    output = io.BytesIO()
    options = {}
    if exif:
        metadata = Image.Exif()
        metadata[0x010F] = "private camera"
        options["exif"] = metadata
    Image.new("RGB", (7, 5), (17, 34, 51)).save(
        output, format="JPEG", **options
    )
    return output.getvalue()


def test_status_response_is_redacted_and_capability_is_reusable(harness):
    first = _status(harness, harness.submission_id, STATUS_SECRET)
    second = _status(harness, harness.submission_id, STATUS_SECRET)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert set(first.json()) == {
        "submission_id",
        "status",
        "public_reason",
        "evidence_state",
        "integration_state",
        "updated_at",
    }
    assert first.json() == {
        "submission_id": harness.submission_id,
        "status": "received",
        "public_reason": "Waiting for an additional measurement.",
        "evidence_state": "pending",
        "integration_state": "not_applicable",
        "updated_at": NOW.isoformat(),
    }
    serialized = first.text
    assert "first@example.com" not in serialized
    assert "private-abuse-digest" not in serialized
    assert "private summary" not in serialized
    assert "claim detail" not in serialized


@pytest.mark.parametrize(
    "invalid_kind",
    ["missing", "expired", "revoked", "consumed", "wrong-purpose", "wrong-submission"],
)
def test_every_invalid_status_capability_has_the_same_not_found_shape(
    harness, invalid_kind
):
    submission_id = harness.submission_id
    capability = STATUS_SECRET
    codec = TokenCodec(harness.settings.read_key("token"))
    with db.connect(harness.settings.database_path) as conn:
        if invalid_kind == "missing":
            capability = "absent-capability-secret-" * 2
        elif invalid_kind == "wrong-purpose":
            capability = FOLLOW_UP_SECRET
        elif invalid_kind == "wrong-submission":
            capability = OTHER_STATUS_SECRET
        else:
            column = {
                "expired": "expires_at",
                "revoked": "revoked_at",
                "consumed": "consumed_at",
            }[invalid_kind]
            value = (
                (NOW - timedelta(seconds=1)).isoformat()
                if invalid_kind == "expired"
                else NOW.isoformat()
            )
            conn.execute(
                f"UPDATE submission_capabilities SET {column} = ? "
                "WHERE submission_id = ? AND purpose = 'status' "
                "AND token_digest = ?",
                (value, submission_id, codec.digest(STATUS_SECRET)),
            )

    response = _status(harness, submission_id, capability)

    assert response.status_code == 404
    assert response.json() == GENERIC_NOT_FOUND
    assert capability not in response.text


def test_capability_is_bound_to_submission_even_across_contributors(harness):
    response = _status(harness, harness.other_submission_id, STATUS_SECRET)

    assert response.status_code == 404
    assert response.json() == GENERIC_NOT_FOUND


@pytest.mark.parametrize("endpoint", ["status", "follow-up", "withdrawal"])
@pytest.mark.parametrize(
    "invalid_capability",
    [
        MISSING,
        None,
        "short-secret",
        "oversized-secret-marker-" * 30,
        "extreme-oversized-secret-marker-" * 1000,
        12345,
        {"secret": "wrong-type-marker"},
    ],
    ids=[
        "absent",
        "null",
        "short",
        "oversized",
        "extreme-oversized",
        "number",
        "object",
    ],
)
def test_malformed_capabilities_are_constant_non_reflective_not_found(
    harness, endpoint, invalid_capability
):
    body = {} if invalid_capability is MISSING else {"capability": invalid_capability}
    if endpoint == "status":
        response = harness.client.post(
            "/submission/v1/status-queries",
            json={"submission_id": harness.submission_id, **body},
        )
    elif endpoint == "withdrawal":
        response = harness.client.post(
            f"/submission/v1/submissions/{harness.submission_id}/withdrawals",
            json=body,
        )
    else:
        response = harness.follow_up({"message": "Additional evidence.", **body})

    assert response.status_code == 404
    assert response.json() == GENERIC_NOT_FOUND
    for marker in (
        "short-secret",
        "oversized-secret-marker",
        "extreme-oversized-secret-marker",
        "wrong-type-marker",
    ):
        assert marker not in response.text


def test_replacing_status_capability_revokes_the_previous_secret(harness):
    replacement = "replacement-status-capability-" * 2
    codec = TokenCodec(harness.settings.read_key("token"))
    with db.connect(harness.settings.database_path) as conn:
        with db.transaction(conn):
            CapabilityRepository(conn).replace(
                harness.submission_id,
                "status",
                codec.digest(replacement),
                (NOW + timedelta(days=30)).isoformat(),
                NOW.isoformat(),
            )

    old = _status(harness, harness.submission_id, STATUS_SECRET)
    new = _status(harness, harness.submission_id, replacement)

    assert old.status_code == 404
    assert old.json() == GENERIC_NOT_FOUND
    assert new.status_code == 200
    with db.connect(harness.settings.database_path) as conn:
        persisted = json.dumps(
            [dict(row) for row in conn.execute("SELECT * FROM submission_capabilities")]
        )
    assert STATUS_SECRET not in persisted
    assert replacement not in persisted


def test_follow_up_only_appends_bounded_text_and_sanitized_images(harness):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'needs_information' WHERE id = ?",
            (harness.submission_id,),
        )
        before = dict(
            conn.execute(
                "SELECT summary, context_json FROM submissions WHERE id = ?",
                (harness.submission_id,),
            ).fetchone()
        )

    response = harness.follow_up(
        {"capability": FOLLOW_UP_SECRET, "message": "  Measured 12.4 volts.  "},
        [("measurement.jpg", _image_bytes(exif=True), "image/jpeg")],
    )

    assert response.status_code == 201
    assert response.json() == {
        "submission_id": harness.submission_id,
        "status": "under_review",
    }
    with db.connect(harness.settings.database_path) as conn:
        submission = conn.execute(
            "SELECT summary, context_json, status FROM submissions WHERE id = ?",
            (harness.submission_id,),
        ).fetchone()
        artifacts = conn.execute(
            "SELECT * FROM submission_artifacts WHERE submission_id = ?",
            (harness.submission_id,),
        ).fetchall()
    context = json.loads(submission["context_json"])
    assert submission["summary"] == before["summary"]
    assert {key: context[key] for key in ("kind", "outcome", "notes")} == json.loads(
        before["context_json"]
    )
    assert submission["status"] == "under_review"
    assert context["follow_ups"] == [
        {
            "message": "Measured 12.4 volts.",
            "artifact_ids": [artifacts[0]["id"]],
        }
    ]
    assert len(artifacts) == 1
    assert artifacts[0]["original_name"] == "measurement.jpg"
    stored = harness.settings.artifact_root / artifacts[0]["storage_key"]
    with Image.open(stored) as image:
        assert image.getexif() == {}


def test_follow_up_capability_is_single_use_and_replay_is_generic(harness):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'needs_information' WHERE id = ?",
            (harness.submission_id,),
        )

    first = harness.follow_up(
        {"capability": FOLLOW_UP_SECRET, "message": "Additional evidence."}
    )
    replay = harness.follow_up(
        {"capability": FOLLOW_UP_SECRET, "message": "Replay attempt."}
    )

    assert first.status_code == 201
    assert replay.status_code == 404
    assert replay.json() == GENERIC_NOT_FOUND
    with db.connect(harness.settings.database_path) as conn:
        consumed_at = conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'follow_up'",
            (harness.submission_id,),
        ).fetchone()[0]
    assert consumed_at == NOW.isoformat()


@pytest.mark.parametrize(
    "metadata",
    [
        {"capability": FOLLOW_UP_SECRET, "message": "x" * 4001},
        {
            "capability": FOLLOW_UP_SECRET,
            "message": "Additional evidence.",
            "summary": "Replace the original summary.",
        },
        {
            "capability": FOLLOW_UP_SECRET,
            "message": "Additional evidence.",
            "claims": [{"proposed": {"confidence": 1}}],
        },
    ],
    ids=["over-text-limit", "summary-edit", "claim-edit"],
)
def test_follow_up_rejects_over_limit_text_and_attempted_edits(harness, metadata):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'needs_information' WHERE id = ?",
            (harness.submission_id,),
        )
        original = conn.execute(
            "SELECT context_json FROM submissions WHERE id = ?",
            (harness.submission_id,),
        ).fetchone()[0]

    response = harness.follow_up(metadata)

    assert response.status_code == 422
    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute(
            "SELECT context_json FROM submissions WHERE id = ?",
            (harness.submission_id,),
        ).fetchone()[0] == original
        assert conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'follow_up'",
            (harness.submission_id,),
        ).fetchone()[0] is None


def test_follow_up_wrong_state_rolls_back_consumption_and_discards_image(harness):
    response = harness.follow_up(
        {"capability": FOLLOW_UP_SECRET, "message": "Additional evidence."},
        [("measurement.jpg", _image_bytes(), "image/jpeg")],
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "submission does not accept follow-up"}
    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'follow_up'",
            (harness.submission_id,),
        ).fetchone()[0] is None
        assert conn.execute("SELECT COUNT(*) FROM submission_artifacts").fetchone()[0] == 0
    assert not any(
        path.is_file() for path in harness.settings.artifact_root.rglob("*")
    )


def test_follow_up_transaction_failure_discards_image_and_preserves_capability(harness):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'needs_information' WHERE id = ?",
            (harness.submission_id,),
        )
        conn.execute(
            """
            CREATE TRIGGER fail_follow_up_artifact
            BEFORE INSERT ON submission_artifacts
            BEGIN
                SELECT RAISE(ABORT, 'simulated follow-up transaction failure');
            END
            """
        )

    with pytest.raises(
        sqlite3.IntegrityError, match="simulated follow-up transaction failure"
    ):
        harness.follow_up(
            {"capability": FOLLOW_UP_SECRET, "message": "Additional evidence."},
            [("measurement.jpg", _image_bytes(), "image/jpeg")],
        )

    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'follow_up'",
            (harness.submission_id,),
        ).fetchone()[0] is None
        assert conn.execute("SELECT COUNT(*) FROM submission_artifacts").fetchone()[0] == 0
    assert not any(
        path.is_file() for path in harness.settings.artifact_root.rglob("*")
    )


def test_follow_up_rechecks_expiry_after_sanitation_inside_transaction(
    harness, monkeypatch
):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'needs_information' WHERE id = ?",
            (harness.submission_id,),
        )
    original_sanitize = artifact_module.ArtifactStore.sanitize

    def sanitize_after_expiry(store, upload, submission_id):
        result = original_sanitize(store, upload, submission_id)
        harness.clock.value = NOW + timedelta(days=31)
        return result

    monkeypatch.setattr(
        artifact_module.ArtifactStore, "sanitize", sanitize_after_expiry
    )

    response = harness.follow_up(
        {"capability": FOLLOW_UP_SECRET, "message": "Additional evidence."},
        [("measurement.jpg", _image_bytes(), "image/jpeg")],
    )

    assert response.status_code == 404
    assert response.json() == GENERIC_NOT_FOUND
    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'follow_up'",
            (harness.submission_id,),
        ).fetchone()[0] is None
        assert conn.execute("SELECT COUNT(*) FROM submission_artifacts").fetchone()[0] == 0
    assert not any(
        path.is_file() for path in harness.settings.artifact_root.rglob("*")
    )


def test_withdrawal_is_pre_promotion_and_single_use(harness):
    first = harness.client.post(
        f"/submission/v1/submissions/{harness.submission_id}/withdrawals",
        json={"capability": WITHDRAWAL_SECRET},
    )
    replay = harness.client.post(
        f"/submission/v1/submissions/{harness.submission_id}/withdrawals",
        json={"capability": WITHDRAWAL_SECRET},
    )

    assert first.status_code == 200
    assert first.json() == {
        "submission_id": harness.submission_id,
        "status": "withdrawn",
    }
    assert replay.status_code == 404
    assert replay.json() == GENERIC_NOT_FOUND
    with db.connect(harness.settings.database_path) as conn:
        row = conn.execute(
            "SELECT status, withdrawn_at FROM submissions WHERE id = ?",
            (harness.submission_id,),
        ).fetchone()
    assert dict(row) == {"status": "withdrawn", "withdrawn_at": NOW.isoformat()}


def test_withdrawal_rechecks_expiry_after_immediate_lock(harness, monkeypatch):
    original_transaction = capability_routes.db.transaction

    @contextmanager
    def expire_after_lock(conn):
        with original_transaction(conn):
            harness.clock.value = NOW + timedelta(days=31)
            yield conn

    monkeypatch.setattr(capability_routes.db, "transaction", expire_after_lock)

    response = harness.client.post(
        f"/submission/v1/submissions/{harness.submission_id}/withdrawals",
        json={"capability": WITHDRAWAL_SECRET},
    )

    assert response.status_code == 404
    assert response.json() == GENERIC_NOT_FOUND
    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'withdrawal'",
            (harness.submission_id,),
        ).fetchone()[0] is None


@pytest.mark.parametrize("integration_state", ["pending", "integrated"])
def test_withdrawal_after_promotion_is_rejected_without_consuming_capability(
    harness, integration_state
):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'accepted', integration_state = ? WHERE id = ?",
            (integration_state, harness.submission_id),
        )

    response = harness.client.post(
        f"/submission/v1/submissions/{harness.submission_id}/withdrawals",
        json={"capability": WITHDRAWAL_SECRET},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "submission cannot be withdrawn"}
    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute(
            "SELECT consumed_at FROM submission_capabilities "
            "WHERE submission_id = ? AND purpose = 'withdrawal'",
            (harness.submission_id,),
        ).fetchone()[0] is None


def test_follow_up_guard_authorizes_metadata_before_reading_artifact_stream(harness):
    boundary = "follow-up-boundary"
    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="metadata"\r\n'
        "Content-Type: application/json\r\n\r\n"
        + json.dumps(
            {"capability": "absent-capability-secret-" * 2, "message": "evidence"}
        )
        + "\r\n"
        + f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="artifacts"; filename="large.png"\r\n'
        + "Content-Type: image/png\r\n\r\n"
    ).encode()
    chunks = [prefix, b"x" * (10 * 1024 * 1024 + 1), b"unrequested-tail"]
    receive_calls = 0
    sent = []

    async def receive():
        nonlocal receive_calls
        chunk = chunks[receive_calls]
        receive_calls += 1
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": receive_calls < len(chunks),
        }

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": f"/submission/v1/submissions/{harness.submission_id}/follow-ups",
        "raw_path": b"",
        "query_string": b"",
        "headers": [
            ("host".encode(), "testserver".encode()),
            ("content-type".encode(), f"multipart/form-data; boundary={boundary}".encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 443),
    }

    asyncio.run(harness.client.app(scope, receive, send))

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 404
    assert receive_calls == 1
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    assert json.loads(body) == GENERIC_NOT_FOUND


@pytest.mark.parametrize(
    "content_type",
    [None, "application/json", "multipart/form-data"],
    ids=["missing", "wrong", "missing-boundary"],
)
def test_follow_up_guard_rejects_invalid_content_type_before_body_receive(
    harness, content_type
):
    receive_calls = 0
    sent = []

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b"private body", "more_body": False}

    async def send(message):
        sent.append(message)

    headers = [(b"host", b"testserver")]
    if content_type is not None:
        headers.append((b"content-type", content_type.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": f"/submission/v1/submissions/{harness.submission_id}/follow-ups",
        "raw_path": b"",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 443),
    }

    asyncio.run(harness.client.app(scope, receive, send))

    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    assert start["status"] == 400
    assert json.loads(body) == {"detail": "invalid multipart body"}
    assert receive_calls == 0


def test_follow_up_disk_spool_excludes_capability_from_coalesced_chunk(
    harness, monkeypatch
):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submissions SET status = 'needs_information' WHERE id = ?",
            (harness.submission_id,),
        )
    real_spool = capability_routes.tempfile.SpooledTemporaryFile
    captures = []

    @contextmanager
    def recording_spool(*args, **kwargs):
        with real_spool(*args, **kwargs) as spool:
            yield spool
            rolled = spool._rolled
            spool.seek(0)
            captures.append((rolled, spool.read()))

    monkeypatch.setattr(
        capability_routes,
        "tempfile",
        SimpleNamespace(SpooledTemporaryFile=recording_spool),
    )
    boundary = "coalesced-follow-up-boundary"
    artifact_marker = b"artifact-body-marker"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="metadata"\r\n'
        "Content-Type: application/json\r\n\r\n"
        + json.dumps(
            {"capability": FOLLOW_UP_SECRET, "message": "Additional evidence."}
        )
        + "\r\n"
        + f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="artifacts"; filename="large.png"\r\n'
        + "Content-Type: image/png\r\n\r\n"
    ).encode() + artifact_marker + b"x" * (2 * 1024 * 1024) + (
        f"\r\n--{boundary}--\r\n"
    ).encode()
    sent = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": f"/submission/v1/submissions/{harness.submission_id}/follow-ups",
        "raw_path": b"",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", f"multipart/form-data; boundary={boundary}".encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 443),
    }

    asyncio.run(harness.client.app(scope, receive, send))

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 400
    assert captures and any(rolled for rolled, _ in captures)
    assert any(artifact_marker in content for _, content in captures)
    assert all(FOLLOW_UP_SECRET.encode() not in content for _, content in captures)
