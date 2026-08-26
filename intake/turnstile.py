"""Cloudflare Turnstile verification boundary."""

from typing import Any

import httpx


SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileRejected(RuntimeError):
    """The provider rejected a browser challenge response."""


class TurnstileUnavailable(RuntimeError):
    """The provider did not return a usable verification decision."""


class TurnstileVerifier:
    """Verify browser tokens without retaining or logging provider payloads."""

    def __init__(self, secret: str, *, client: httpx.Client | None = None):
        if not isinstance(secret, str) or not secret:
            raise ValueError("turnstile secret must not be empty")
        self._secret = secret
        self._client = client or httpx.Client(trust_env=False)
        self._owns_client = client is None

    def verify(self, token: str, remote_ip: str) -> None:
        try:
            response = self._client.post(
                SITEVERIFY_URL,
                data={
                    "secret": self._secret,
                    "response": token,
                    "remoteip": remote_ip,
                },
                timeout=5.0,
            )
            response.raise_for_status()
            payload: Any = response.json()
        except (httpx.HTTPError, ValueError):
            raise TurnstileUnavailable("turnstile unavailable") from None

        if not isinstance(payload, dict) or not isinstance(
            payload.get("success"), bool
        ):
            raise TurnstileUnavailable("turnstile unavailable")
        if not payload["success"]:
            raise TurnstileRejected("turnstile verification failed")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
