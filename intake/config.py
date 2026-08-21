"""Configuration for the isolated submission intake service."""

import os
from dataclasses import dataclass
from pathlib import Path


def _required_file(name: str) -> Path:
    """Return a readable, absolute secret-file path from the environment."""
    path = Path(os.environ[name])
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError(f"{name} must name an existing absolute file")
    try:
        path.read_bytes()
    except OSError as error:
        raise RuntimeError(f"{name} must name a readable file") from error
    return path


def _required_key_file(name: str) -> Path:
    path = _required_file(name)
    if len(path.read_bytes()) != 32:
        raise RuntimeError(f"{name} must contain exactly 32 bytes")
    return path


def _required_nonempty_file(name: str) -> Path:
    path = _required_file(name)
    if not path.read_bytes():
        raise RuntimeError(f"{name} must not be empty")
    return path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    artifact_root: Path
    contact_key_path: Path
    token_key_path: Path
    session_key_path: Path
    ip_key_path: Path
    turnstile_secret_path: Path
    trust_cf_connecting_ip: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=Path(os.environ["RVI_INTAKE_DB_PATH"]),
            artifact_root=Path(os.environ["RVI_ARTIFACT_ROOT"]),
            contact_key_path=_required_key_file("RVI_CONTACT_KEY_FILE"),
            token_key_path=_required_key_file("RVI_TOKEN_KEY_FILE"),
            session_key_path=_required_key_file("RVI_SESSION_KEY_FILE"),
            ip_key_path=_required_key_file("RVI_IP_KEY_FILE"),
            turnstile_secret_path=_required_nonempty_file(
                "RVI_TURNSTILE_SECRET_FILE"
            ),
            trust_cf_connecting_ip=os.environ.get("RVI_TRUST_CF_CONNECTING_IP") == "true",
        )

    @classmethod
    def for_tests(cls, root: Path) -> "Settings":
        root.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, value in {
            "contact": b"c" * 32,
            "token": b"t" * 32,
            "session": b"s" * 32,
            "ip": b"i" * 32,
            "turnstile": b"test-secret",
        }.items():
            paths[name] = root / name
            paths[name].write_bytes(value)
        return cls(
            root / "submissions.db",
            root / "artifacts",
            paths["contact"],
            paths["token"],
            paths["session"],
            paths["ip"],
            paths["turnstile"],
        )
