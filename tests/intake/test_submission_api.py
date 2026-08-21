import asyncio
import io
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from intake import db
from intake.app import create_app
from intake.artifacts import ArtifactStore
from intake.config import Settings
from intake.repositories import ContributorRepository, SessionRepository
from intake.security import ContactCipher, TokenCodec
from intake.turnstile import TurnstileRejected, TurnstileUnavailable


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
SESSION_TOKEN = "session-secret" * 4
CSRF_TOKEN = "csrf-secret" * 4
SESSION_COOKIE = "rvi_contribution_session"


class MutableClock:
    def __init__(self, value: datetime):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class SequenceSecrets:
    def __init__(self):
        self.values = [f"capability-{index:03d}-" * 3 for index in range(100)]
        self.issued = []

    def __call__(self) -> str:
        value = self.values.pop(0)
        self.issued.append(value)
        return value


class RecordingTurnstile:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = []

    def verify(self, token: str, remote_ip: str) -> None:
        self.calls.append((token, remote_ip))
        if self.error is not None:
            raise self.error


@dataclass
class SubmissionHarness:
    settings: Settings
    client: TestClient
    clock: MutableClock
    verifier: RecordingTurnstile
    secrets: SequenceSecrets
    session_id: str
    contributor_id: str
    email_digest: str

    def post(self, metadata: dict, *, artifacts=(), csrf: str = CSRF_TOKEN):
        parts = [
            (
                "metadata",
                (None, json.dumps(metadata), "application/json"),
            )
        ]
        parts.extend(
            (
                "artifacts",
                (filename, content, media_type),
            )
            for filename, content, media_type in artifacts
        )
        return self.client.post(
            "/submission/v1/submissions",
            files=parts,
            headers={"X-CSRF-Token": csrf},
        )


@pytest.fixture
def settings(tmp_path):
    return Settings.for_tests(tmp_path)


@pytest.fixture
def harness(settings):
    clock = MutableClock(NOW)
    verifier = RecordingTurnstile()
    secrets = SequenceSecrets()
    client = TestClient(
        create_app(
            settings,
            turnstile_verifier=verifier,
            clock=clock,
            secret_factory=secrets,
        ),
        base_url="https://testserver",
        client=("2001:db8::1", 50000),
    )
    with client:
        session_codec = TokenCodec(settings.read_key("session"))
        email_digest = TokenCodec(settings.read_key("token")).digest(
            "person@example.com"
        )
        with db.connect(settings.database_path) as conn:
            with db.transaction(conn):
                contributor_id = ContributorRepository(conn).create(
                    email_digest,
                    ContactCipher(settings.read_key("contact")).encrypt(
                        "person@example.com"
                    ),
                    NOW.isoformat(),
                )
                sessions = SessionRepository(conn)
                session_id = sessions.create_pending(
                    contributor_id,
                    "verification-digest",
                    (NOW + timedelta(minutes=15)).isoformat(),
                    NOW.isoformat(),
                )
                sessions.activate(
                    "verification-digest",
                    session_codec.digest(SESSION_TOKEN),
                    session_codec.digest(CSRF_TOKEN),
                    (NOW + timedelta(hours=24)).isoformat(),
                    NOW.isoformat(),
                )
        signed = session_codec.sign_session(
            SESSION_TOKEN, int((NOW + timedelta(hours=24)).timestamp())
        )
        client.cookies.set(
            SESSION_COOKIE,
            signed,
            path="/submission/v1/",
        )
        yield SubmissionHarness(
            settings,
            client,
            clock,
            verifier,
            secrets,
            session_id,
            contributor_id,
            email_digest,
        )


def _claim(claim_type="installation_outcome"):
    return {
        "claim_type": claim_type,
        "proposed": {"outcome": "success", "notes": "Observed directly."},
    }


def _metadata(intent="installation_result"):
    contexts = {
        "installation_result": {
            "kind": "installation_result",
            "outcome": "success",
            "notes": "Installed and tested under normal load.",
        },
        "documentation_citation": {
            "kind": "documentation_citation",
            "source_url": "https://example.com/manual.pdf",
            "document_title": "Manufacturer installation manual",
            "citation": "Page 14 identifies the supported replacement.",
        },
        "data_correction": {
            "kind": "data_correction",
            "reason": "The listed identifier contains a transposed character.",
            "source_url": "https://example.com/correction-notice",
        },
    }
    claim_types = {
        "installation_result": "installation_outcome",
        "documentation_citation": "document_assertion",
        "data_correction": "correction",
    }
    return {
        "intent": intent,
        "summary": "Verified evidence submitted for independent review.",
        "target_component_id": "component-a",
        "target_edge": {
            "type": "replacement",
            "from_component_id": "component-a",
            "to_component_id": "component-b",
        },
        "target_namespace": "manufacturer",
        "target_identifier": "PART-100",
        "priority": "normal",
        "context": contexts[intent],
        "claims": [_claim(claim_types[intent])],
        "terms_version": "2026-08-21",
        "evidence_license_version": "CC0-1.0",
        "consented": True,
        "turnstile_token": "turnstile-browser-token",
    }


def _image_bytes(image_format="PNG", *, size=(7, 5), color=(17, 34, 51)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=image_format)
    return output.getvalue()


def _multipart_body(metadata, artifacts, boundary="guard-boundary") -> bytes:
    parts = [
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="metadata"\r\n'
            "Content-Type: application/json\r\n\r\n"
        ).encode()
        + json.dumps(metadata).encode()
        + b"\r\n"
    ]
    for filename, content, media_type in artifacts:
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="artifacts"; filename="{filename}"\r\n'
                f"Content-Type: {media_type}\r\n\r\n"
            ).encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)


def _invoke_asgi(app, chunks, headers):
    receive_calls = 0
    messages = []

    async def run():
        nonlocal receive_calls
        index = 0

        async def receive():
            nonlocal receive_calls, index
            receive_calls += 1
            chunk = chunks[index]
            index += 1
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(chunks),
            }

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/submission/v1/submissions",
            "raw_path": b"/submission/v1/submissions",
            "query_string": b"",
            "headers": headers,
            "client": ("2001:db8::1", 50000),
            "server": ("testserver", 443),
        }
        await app(scope, receive, send)

    asyncio.run(run())
    response_start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    return response_start["status"], receive_calls


def test_submission_guard_authenticates_before_consuming_multipart_body(settings):
    db.migrate(settings.database_path)
    app = create_app(settings, turnstile_verifier=RecordingTurnstile())
    image = _image_bytes()
    body = _multipart_body(
        _metadata(),
        [(f"evidence-{index}.png", image, "image/png") for index in range(6)],
    )

    response_status, receive_calls = _invoke_asgi(
        app,
        [body],
        [(b"content-type", b"multipart/form-data; boundary=guard-boundary")],
    )

    assert response_status == 401
    assert receive_calls == 0


def test_submission_guard_stops_authenticated_oversize_file_stream_early(harness):
    boundary = "stream-boundary"
    header = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="artifacts"; filename="large.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode()
    chunks = [header] + [b"x" * (1024 * 1024)] * 10 + [b"x"]
    chunks.append(f"\r\n--{boundary}--\r\n".encode())
    signed_session = harness.client.cookies.get(SESSION_COOKIE)

    response_status, receive_calls = _invoke_asgi(
        harness.client.app,
        chunks,
        [
            (b"content-type", f"multipart/form-data; boundary={boundary}".encode()),
            (b"cookie", f"{SESSION_COOKIE}={signed_session}".encode()),
            (b"x-csrf-token", CSRF_TOKEN.encode()),
        ],
    )

    assert response_status == 413
    assert receive_calls < len(chunks)


@pytest.mark.parametrize(
    "intent",
    ["installation_result", "documentation_citation", "data_correction"],
)
def test_submission_accepts_each_discriminated_intent(harness, intent):
    response = harness.post(_metadata(intent))

    assert response.status_code == 201
    assert response.json()["status"] == "received"
    with db.connect(harness.settings.database_path) as conn:
        row = conn.execute("SELECT intent, context_json FROM submissions").fetchone()
    assert row["intent"] == intent
    assert json.loads(row["context_json"])["kind"] == intent


def test_success_is_atomic_and_returns_only_one_time_owner_capabilities(harness):
    image = _image_bytes()
    response = harness.post(
        _metadata(), artifacts=[("evidence.png", image, "image/png")]
    )

    assert response.status_code == 201
    receipt = response.json()
    assert set(receipt) == {"submission_id", "status", "capabilities"}
    assert receipt["status"] == "received"
    assert set(receipt["capabilities"]) == {"status", "follow_up", "withdrawal"}
    assert list(receipt["capabilities"].values()) == harness.secrets.issued

    token_codec = TokenCodec(harness.settings.read_key("token"))
    with db.connect(harness.settings.database_path) as conn:
        submission = conn.execute("SELECT * FROM submissions").fetchone()
        claims = conn.execute("SELECT * FROM submission_claims").fetchall()
        artifact = conn.execute("SELECT * FROM submission_artifacts").fetchone()
        capabilities = conn.execute(
            "SELECT purpose, token_digest FROM submission_capabilities ORDER BY purpose"
        ).fetchall()
        outbox = conn.execute("SELECT * FROM email_outbox").fetchone()
        session_count = conn.execute(
            "SELECT submission_count FROM submission_sessions WHERE id = ?",
            (harness.session_id,),
        ).fetchone()[0]
        rate_events = conn.execute(
            "SELECT scope, subject_digest FROM rate_limit_events"
        ).fetchall()

    assert submission["id"] == receipt["submission_id"]
    assert submission["contributor_id"] == harness.contributor_id
    assert json.loads(submission["target_edge_key_json"]) == {
        "from_component_id": "component-a",
        "to_component_id": "component-b",
        "type": "replacement",
    }
    assert len(claims) == 1
    assert claims[0]["claim_type"] == "installation_outcome"
    assert artifact["scan_status"] == "clean"
    assert artifact["retention_class"] == "unverified"
    assert artifact["raw_sha256"] != ""
    assert harness.settings.artifact_root.joinpath(artifact["storage_key"]).is_file()
    assert {row["purpose"] for row in capabilities} == {
        "status",
        "follow_up",
        "withdrawal",
    }
    for row in capabilities:
        raw = receipt["capabilities"][row["purpose"]]
        assert row["token_digest"] == token_codec.digest(raw)
        assert row["token_digest"] != raw
    assert outbox["template"] == "submission_received"
    assert outbox["recipient_ciphertext"] is not None
    persisted_outbox = outbox["template_data_json"]
    assert all(raw not in persisted_outbox for raw in receipt["capabilities"].values())
    assert session_count == 1
    assert [(row["scope"], row["subject_digest"]) for row in rate_events] == [
        ("submission_email", harness.email_digest)
    ]
    assert harness.verifier.calls == [("turnstile-browser-token", "2001:db8::1")]


@pytest.mark.parametrize(
    "field,value",
    [
        ("summary", "x" * 19),
        ("summary", "x" * 4001),
        ("claims", []),
        ("claims", [_claim()] * 51),
        ("consented", False),
        ("terms_version", "x" * 65),
        ("evidence_license_version", "x" * 65),
        ("priority", "critical"),
    ],
)
def test_submission_enforces_public_metadata_bounds(harness, field, value):
    metadata = _metadata()
    metadata[field] = value

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


def test_intent_must_match_discriminated_context(harness):
    metadata = _metadata()
    metadata["context"] = _metadata("data_correction")["context"]

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


def test_https_url_accepts_exact_2048_byte_boundary_without_fetching(harness):
    metadata = _metadata("documentation_citation")
    prefix = "https://example.com/"
    metadata["context"]["source_url"] = prefix + "x" * (2048 - len(prefix))

    response = harness.post(metadata)

    assert response.status_code == 201
    assert harness.verifier.calls == [("turnstile-browser-token", "2001:db8::1")]


@pytest.mark.parametrize(
    "source_url",
    [
        "http://example.com/manual.pdf",
        "https://person@example.com/manual.pdf",
        "https://example.com/" + "x" * (2049 - len("https://example.com/")),
    ],
    ids=["non-https", "userinfo", "over-2048-bytes"],
)
def test_submission_rejects_unsafe_source_urls(harness, source_url):
    metadata = _metadata("documentation_citation")
    metadata["context"]["source_url"] = source_url

    response = harness.post(metadata)

    assert response.status_code == 422
    assert harness.verifier.calls == []
    _assert_no_submission_writes(harness)


@pytest.mark.parametrize(
    "target_edge",
    [
        {
            "id": 123,
            "type": "replacement",
            "from_component_id": "component-a",
            "to_component_id": "component-b",
        },
        {"type": "replacement", "from_component_id": "component-a"},
        {
            "type": "replacement",
            "from_component_id": "component-a",
            "to_component_id": "component-b",
            "group_key": "replacement-group",
        },
    ],
    ids=["row-id", "missing-destination", "ambiguous-destination"],
)
def test_target_edge_requires_a_stable_logical_locator(harness, target_edge):
    metadata = _metadata()
    metadata["target_edge"] = target_edge

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "canonical_observation_id",
        "observation_id",
        "source_tier",
        "tier",
        "confidence",
        "graph_mutation",
        "edge_id",
    ],
)
def test_claims_cannot_request_canonical_or_graph_mutations(harness, forbidden_key):
    metadata = _metadata()
    metadata["claims"][0]["proposed"][forbidden_key] = "attacker-controlled"

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "confidence_effect",
        "source_tiers",
        "canonicalObservationId",
        "graphOperations",
        "Ｃａｎｏｎｉｃａｌ＿ObservationId",
        "confidenceeffect",
        "sourcetiers",
        "canonicalobservationid",
        "graphoperations",
        "proposedgraphoperations",
    ],
)
def test_claim_validation_rejects_nested_semantic_key_variants(harness, forbidden_key):
    metadata = _metadata()
    metadata["claims"][0]["proposed"] = {
        "outer": {"inner": {forbidden_key: "attacker-controlled"}}
    }

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


@pytest.mark.parametrize("url_key", ["sourceUrl", "sourceurl"])
def test_claim_validation_checks_nested_source_url_variants(harness, url_key):
    metadata = _metadata()
    metadata["claims"][0]["proposed"] = {
        "outer": {url_key: "http://example.com/untrusted"}
    }

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


@pytest.mark.parametrize(
    "proposed",
    [
        {"sourceHref": "http://example.com/untrusted"},
        {"evidenceLink": "https://person@example.com/untrusted"},
        {"website": "ftp://example.com/untrusted"},
        {"outer": {"items": ["ordinary evidence", "javascript:alert(1)"]}},
        {"outer": [{"reference": "//example.com/untrusted"}]},
    ],
    ids=[
        "source-href-http",
        "evidence-link-userinfo",
        "website-ftp",
        "nested-list-scheme",
        "nested-list-scheme-relative",
    ],
)
def test_claim_validation_rejects_insecure_url_values_regardless_of_key(
    harness, proposed
):
    metadata = _metadata()
    metadata["claims"][0]["proposed"] = proposed

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


def test_claim_validation_accepts_https_aliases_nested_lists_and_plain_text(harness):
    metadata = _metadata()
    metadata["claims"][0]["proposed"] = {
        "sourceHref": "https://example.com/source",
        "outer": {
            "evidenceLink": [
                "https://example.com/evidence/one",
                "https://example.com/evidence/two",
            ],
            "website": "https://example.com/project",
            "references": [
                "ordinary evidence text",
                {"unconventionalKey": "https://example.com/reference"},
            ],
        },
    }

    response = harness.post(metadata)

    assert response.status_code == 201


def test_caller_cannot_supply_submission_or_canonical_ids(harness):
    metadata = _metadata()
    metadata["id"] = "4cf3371c-80f4-40cd-b07d-c085280cfa80"
    metadata["canonical_observation_id"] = "canonical-1"

    response = harness.post(metadata)

    assert response.status_code == 422
    _assert_no_submission_writes(harness)


def test_submission_requires_an_active_signed_session(harness):
    harness.client.cookies.clear()

    response = harness.post(_metadata())

    assert response.status_code == 401
    assert harness.verifier.calls == []
    _assert_no_submission_writes(harness)


def test_submission_rejects_session_at_expiry_boundary(harness):
    harness.clock.value = NOW + timedelta(hours=24)

    response = harness.post(_metadata())

    assert response.status_code == 401
    assert harness.verifier.calls == []
    _assert_no_submission_writes(harness)


def test_submission_requires_matching_csrf(harness):
    response = harness.post(_metadata(), csrf="wrong")

    assert response.status_code == 403
    assert harness.verifier.calls == []
    _assert_no_submission_writes(harness)


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (TurnstileRejected("rejected"), 400),
        (TurnstileUnavailable("unavailable"), 503),
    ],
)
def test_submission_maps_turnstile_failures(harness, error, expected_status):
    harness.verifier.error = error

    response = harness.post(_metadata())

    assert response.status_code == expected_status
    _assert_no_submission_writes(harness)


def test_session_allows_only_five_submissions(harness):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submission_sessions SET submission_count = 5 WHERE id = ?",
            (harness.session_id,),
        )

    response = harness.post(_metadata())

    assert response.status_code == 429
    _assert_no_submission_writes(harness, expected_session_count=5)


def test_email_allows_only_twenty_submissions_per_day(harness):
    with db.connect(harness.settings.database_path) as conn:
        with db.transaction(conn):
            conn.executemany(
                """
                INSERT INTO rate_limit_events (id, scope, subject_digest, occurred_at)
                VALUES (?, 'submission_email', ?, ?)
                """,
                [
                    (f"event-{index}", harness.email_digest, NOW.isoformat())
                    for index in range(20)
                ],
            )

    response = harness.post(_metadata())

    assert response.status_code == 429
    _assert_no_submission_writes(harness)
    with db.connect(harness.settings.database_path) as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM rate_limit_events").fetchone()[0] == 20
        )


def test_exhausted_session_preflight_does_not_invoke_sanitation(harness, monkeypatch):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            "UPDATE submission_sessions SET submission_count = 5 WHERE id = ?",
            (harness.session_id,),
        )

    def fail_if_sanitized(*args, **kwargs):
        raise AssertionError("sanitation must not run for an exhausted session")

    monkeypatch.setattr(ArtifactStore, "sanitize", fail_if_sanitized)

    response = harness.post(
        _metadata(), artifacts=[("evidence.png", _image_bytes(), "image/png")]
    )

    assert response.status_code == 429
    _assert_no_submission_writes(harness, expected_session_count=5)


def test_exhausted_email_preflight_does_not_invoke_sanitation(harness, monkeypatch):
    with db.connect(harness.settings.database_path) as conn:
        with db.transaction(conn):
            conn.executemany(
                """
                INSERT INTO rate_limit_events (id, scope, subject_digest, occurred_at)
                VALUES (?, 'submission_email', ?, ?)
                """,
                [
                    (f"preflight-event-{index}", harness.email_digest, NOW.isoformat())
                    for index in range(20)
                ],
            )

    def fail_if_sanitized(*args, **kwargs):
        raise AssertionError("sanitation must not run for an exhausted email")

    monkeypatch.setattr(ArtifactStore, "sanitize", fail_if_sanitized)

    response = harness.post(
        _metadata(), artifacts=[("evidence.png", _image_bytes(), "image/png")]
    )

    assert response.status_code == 429
    _assert_no_submission_writes(harness)


def test_submission_rejects_more_than_five_artifacts(harness):
    image = _image_bytes()
    artifacts = [(f"evidence-{index}.png", image, "image/png") for index in range(6)]

    response = harness.post(_metadata(), artifacts=artifacts)

    assert response.status_code == 413
    _assert_no_submission_writes(harness)


def test_submission_rejects_artifact_over_ten_mib(harness):
    artifact = ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")

    response = harness.post(_metadata(), artifacts=[artifact])

    assert response.status_code == 413
    _assert_no_submission_writes(harness)


def test_submission_rejects_artifacts_over_twenty_five_mib_total(harness):
    artifacts = [
        (f"large-{index}.png", b"x" * (9 * 1024 * 1024), "image/png")
        for index in range(3)
    ]

    response = harness.post(_metadata(), artifacts=artifacts)

    assert response.status_code == 413
    _assert_no_submission_writes(harness)


def test_submission_rejects_decoded_dimension_limit(harness):
    artifact = (
        "wide.png",
        _image_bytes(size=(12_001, 1)),
        "image/png",
    )

    response = harness.post(_metadata(), artifacts=[artifact])

    assert response.status_code == 400
    _assert_no_submission_writes(harness)
    assert not any(harness.settings.artifact_root.rglob("*"))


def test_artifact_rejection_discards_prior_sanitized_derivatives(harness):
    artifacts = [
        ("good.png", _image_bytes(), "image/png"),
        ("bad.png", b"not an image", "image/png"),
    ]

    response = harness.post(_metadata(), artifacts=artifacts)

    assert response.status_code == 400
    _assert_no_submission_writes(harness)
    assert not any(path.is_file() for path in harness.settings.artifact_root.rglob("*"))


def test_sql_failure_rolls_back_all_rows_and_discards_derivatives(harness):
    with db.connect(harness.settings.database_path) as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_submission_outbox
            BEFORE INSERT ON email_outbox
            WHEN NEW.template = 'submission_received'
            BEGIN
                SELECT RAISE(ABORT, 'simulated submission outbox failure');
            END
            """
        )

    with pytest.raises(
        sqlite3.IntegrityError, match="simulated submission outbox failure"
    ):
        harness.post(
            _metadata(),
            artifacts=[("evidence.png", _image_bytes(), "image/png")],
        )

    _assert_no_submission_writes(harness)
    assert not any(path.is_file() for path in harness.settings.artifact_root.rglob("*"))
    with db.connect(harness.settings.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM rate_limit_events").fetchone()[0] == 0


def test_secret_factory_failure_discards_sanitized_derivatives(harness):
    def fail_secret_generation():
        raise RuntimeError("simulated secret generation failure")

    harness.client.app.state.secret_factory = fail_secret_generation

    with pytest.raises(RuntimeError, match="simulated secret generation failure"):
        harness.post(
            _metadata(),
            artifacts=[("evidence.png", _image_bytes(), "image/png")],
        )

    _assert_no_submission_writes(harness)
    assert not any(path.is_file() for path in harness.settings.artifact_root.rglob("*"))


def test_token_key_read_failure_discards_sanitized_derivatives(harness, monkeypatch):
    original_read_key = Settings.read_key

    def fail_token_key(settings, purpose):
        if purpose == "token":
            raise RuntimeError("simulated token key failure")
        return original_read_key(settings, purpose)

    monkeypatch.setattr(Settings, "read_key", fail_token_key)

    with pytest.raises(RuntimeError, match="simulated token key failure"):
        harness.post(
            _metadata(),
            artifacts=[("evidence.png", _image_bytes(), "image/png")],
        )

    _assert_no_submission_writes(harness)
    assert not any(path.is_file() for path in harness.settings.artifact_root.rglob("*"))


def _assert_no_submission_writes(
    harness: SubmissionHarness, *, expected_session_count=0
):
    with db.connect(harness.settings.database_path) as conn:
        for table in (
            "submissions",
            "submission_claims",
            "submission_artifacts",
            "submission_capabilities",
            "email_outbox",
        ):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT submission_count FROM submission_sessions WHERE id = ?",
                (harness.session_id,),
            ).fetchone()[0]
            == expected_session_count
        )
