from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from intake.app import app_factory, create_app
from intake.config import Settings


def test_intake_health_uses_coarse_shape(tmp_path):
    settings = Settings.for_tests(tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_factory_loads_validated_environment(tmp_path, monkeypatch):
    settings = Settings.for_tests(tmp_path)
    _set_settings_environment(monkeypatch, settings)

    with TestClient(app_factory()) as client:
        response = client.get("/health/")

    assert response.status_code == 200


def test_settings_from_env_rejects_non_32_byte_key(tmp_path, monkeypatch):
    settings = Settings.for_tests(tmp_path)
    short_contact_key = tmp_path / "short-contact"
    short_contact_key.write_bytes(b"c" * 31)
    _set_settings_environment(monkeypatch, settings, contact_key_path=short_contact_key)

    with pytest.raises(RuntimeError, match="RVI_CONTACT_KEY_FILE must contain exactly 32 bytes"):
        Settings.from_env()


def test_settings_from_env_accepts_non_32_byte_turnstile_secret(tmp_path, monkeypatch):
    settings = Settings.for_tests(tmp_path)
    _set_settings_environment(monkeypatch, settings)

    configured = Settings.from_env()

    assert configured.turnstile_secret_path.read_bytes() == b"test-secret"


def test_settings_from_env_rejects_empty_turnstile_secret(tmp_path, monkeypatch):
    settings = Settings.for_tests(tmp_path)
    empty_turnstile_secret = tmp_path / "empty-turnstile"
    empty_turnstile_secret.write_bytes(b"")
    _set_settings_environment(
        monkeypatch, settings, turnstile_secret_path=empty_turnstile_secret
    )

    with pytest.raises(
        RuntimeError, match="RVI_TURNSTILE_SECRET_FILE must not be empty"
    ):
        Settings.from_env()


def test_settings_from_env_requires_absolute_secret_paths(tmp_path, monkeypatch):
    settings = Settings.for_tests(tmp_path)
    _set_settings_environment(monkeypatch, settings)
    monkeypatch.setenv("RVI_TOKEN_KEY_FILE", "relative-token")

    with pytest.raises(
        RuntimeError, match="RVI_TOKEN_KEY_FILE must name an existing absolute file"
    ):
        Settings.from_env()


def _set_settings_environment(
    monkeypatch,
    settings: Settings,
    *,
    contact_key_path: Path | None = None,
    turnstile_secret_path: Path | None = None,
) -> None:
    monkeypatch.setenv("RVI_INTAKE_DB_PATH", str(settings.database_path))
    monkeypatch.setenv("RVI_ARTIFACT_ROOT", str(settings.artifact_root))
    monkeypatch.setenv(
        "RVI_CONTACT_KEY_FILE", str(contact_key_path or settings.contact_key_path)
    )
    monkeypatch.setenv("RVI_TOKEN_KEY_FILE", str(settings.token_key_path))
    monkeypatch.setenv("RVI_SESSION_KEY_FILE", str(settings.session_key_path))
    monkeypatch.setenv("RVI_IP_KEY_FILE", str(settings.ip_key_path))
    monkeypatch.setenv(
        "RVI_TURNSTILE_SECRET_FILE",
        str(turnstile_secret_path or settings.turnstile_secret_path),
    )
