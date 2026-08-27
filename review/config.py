import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    access_issuer: str
    access_audience: str
    access_jwks_url: str
    reviewer_digest_key: bytes

    @classmethod
    def from_env(cls):
        key_path = Path(os.environ["RVI_REVIEW_DIGEST_KEY_FILE"])
        return cls(Path(os.environ["RVI_INTAKE_DB_PATH"]), os.environ["RVI_ACCESS_ISSUER"], os.environ["RVI_ACCESS_AUDIENCE"], os.environ["RVI_ACCESS_JWKS_URL"], key_path.read_bytes())

    @classmethod
    def for_tests(cls, database_path: Path, key: bytes = b"k" * 32):
        return cls(database_path, "https://access.example", "aud", "https://access.example/certs", key)
