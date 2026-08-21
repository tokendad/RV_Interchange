import json

import httpx
import pytest

from intake.turnstile import (
    TurnstileRejected,
    TurnstileUnavailable,
    TurnstileVerifier,
)


SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def test_turnstile_posts_only_approved_fields_with_five_second_timeout():
    observed = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["method"] = request.method
        observed["url"] = str(request.url)
        observed["body"] = request.content.decode("ascii")
        observed["timeout"] = request.extensions["timeout"]
        return httpx.Response(200, json={"success": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    TurnstileVerifier("provider-secret", client=client).verify(
        "browser-token", "2001:db8::1"
    )

    assert observed["method"] == "POST"
    assert observed["url"] == SITEVERIFY
    assert observed["body"] == (
        "secret=provider-secret&response=browser-token&remoteip=2001%3Adb8%3A%3A1"
    )
    assert observed["timeout"] == {
        "connect": 5.0,
        "read": 5.0,
        "write": 5.0,
        "pool": 5.0,
    }


def test_turnstile_rejects_provider_denial():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"success": False, "error-codes": ["invalid-input-response"]},
            )
        )
    )

    with pytest.raises(TurnstileRejected, match="turnstile verification failed"):
        TurnstileVerifier("provider-secret", client=client).verify(
            "browser-token", "192.0.2.10"
        )


def test_turnstile_timeout_is_unavailable():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret provider detail", request=request)

    client = httpx.Client(transport=httpx.MockTransport(timeout))

    with pytest.raises(TurnstileUnavailable, match="turnstile unavailable") as error:
        TurnstileVerifier("provider-secret", client=client).verify(
            "browser-token", "192.0.2.10"
        )

    assert "secret provider detail" not in str(error.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, content=json.dumps({"success": "yes"}).encode()),
        httpx.Response(503, json={"success": False}),
    ],
    ids=["malformed-json", "malformed-shape", "provider-error"],
)
def test_turnstile_malformed_or_failed_provider_response_is_unavailable(response):
    client = httpx.Client(transport=httpx.MockTransport(lambda _: response))

    with pytest.raises(TurnstileUnavailable, match="turnstile unavailable"):
        TurnstileVerifier("provider-secret", client=client).verify(
            "browser-token", "192.0.2.10"
        )
