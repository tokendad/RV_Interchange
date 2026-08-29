import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    observations_database_path: Path
    access_issuer: str
    access_audience: str
    access_jwks_url: str
    reviewer_digest_key: bytes

    @classmethod
    def from_env(cls):
        key_path = Path(os.environ["RVI_REVIEW_DIGEST_KEY_FILE"])
        return cls(
            database_path=Path(os.environ["RVI_INTAKE_DB_PATH"]),
            observations_database_path=Path(os.environ["RVI_OBSERVATIONS_DB_PATH"]),
            access_issuer=os.environ["RVI_ACCESS_ISSUER"],
            access_audience=os.environ["RVI_ACCESS_AUDIENCE"],
            access_jwks_url=os.environ["RVI_ACCESS_JWKS_URL"],
            reviewer_digest_key=key_path.read_bytes(),
        )

    @classmethod
    def for_tests(cls, database_path: Path, key: bytes = b"k" * 32):
        return cls(
            database_path=database_path,
            observations_database_path=database_path.with_name("observations.db"),
            access_issuer="https://access.example",
            access_audience="aud",
            access_jwks_url="https://access.example/certs",
            reviewer_digest_key=key,
        )
