"""Transaction-owned application rate limits and rotating abuse digests."""

import hashlib
import hmac
import ipaddress
import sqlite3
from datetime import datetime, timedelta, timezone

from intake.repositories import RateLimitRepository


class RateLimitExceeded(RuntimeError):
    """The current subject has exhausted an application rate limit."""


def canonical_ip(value: str) -> str:
    """Return the compressed canonical representation of an IP address."""
    if not isinstance(value, str):
        raise ValueError("invalid client address")
    try:
        return ipaddress.ip_address(value.strip()).compressed
    except ValueError:
        raise ValueError("invalid client address") from None


def daily_ip_digest(key: bytes, remote_ip: str, now: datetime) -> str:
    """Derive a UTC-date-rotating digest over a canonical client IP."""
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("IP digest key must contain exactly 32 bytes")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("rate-limit time must be timezone-aware")
    day = now.astimezone(timezone.utc).date().isoformat()
    subject = f"{day}\0{canonical_ip(remote_ip)}".encode("ascii")
    return hmac.new(key, subject, hashlib.sha256).hexdigest()


class RateLimiter:
    """Check and record an event using the caller's open transaction."""

    def __init__(self, conn: sqlite3.Connection):
        self._repository = RateLimitRepository(conn)

    def check_and_record(
        self,
        scope: str,
        subject_digest: str,
        limit: int,
        window_seconds: int,
        now: datetime,
    ) -> None:
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate limit and window must be positive")
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("rate-limit time must be timezone-aware")
        normalized_now = now.astimezone(timezone.utc)
        since = normalized_now - timedelta(seconds=window_seconds)
        if self._repository.count_since(
            scope, subject_digest, since.isoformat()
        ) >= limit:
            raise RateLimitExceeded("rate limit exceeded")
        self._repository.record(scope, subject_digest, normalized_now.isoformat())
