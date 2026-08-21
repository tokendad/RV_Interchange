import base64

import pytest

from intake.config import Settings
from intake.security import (
    ContactCipher,
    TokenCodec,
    new_secret,
    normalize_email,
    verify_csrf,
)


def test_normalize_email_applies_nfkc_trim_and_ascii_lowercase():
    assert (
        normalize_email("  ＰＥＲＳＯＮ＠ＥＸＡＭＰＬＥ．ＣＯＭ  ")
        == "person@example.com"
    )


@pytest.mark.parametrize(
    "email",
    [
        "missing-at.example.com",
        "two@@example.com",
        "person@",
        "@example.com",
        "person name@example.com",
        "person@exam_ple.com",
        "person\x00@example.com",
        "person\n@example.com",
        f"{'a' * 243}@example.com",
        "pérson@example.com",
    ],
)
def test_normalize_email_rejects_invalid_addresses_without_disclosure(email):
    with pytest.raises(ValueError) as caught:
        normalize_email(email)

    assert email not in str(caught.value)


def test_contact_cipher_round_trip_uses_random_nonce():
    cipher = ContactCipher(b"c" * 32)

    first = cipher.encrypt("person@example.com")
    second = cipher.encrypt("person@example.com")

    assert first != second
    assert cipher.decrypt(first) == "person@example.com"
    assert cipher.decrypt(second) == "person@example.com"


def test_contact_cipher_rejects_tampering_without_disclosure():
    cipher = ContactCipher(b"c" * 32)
    ciphertext = bytearray(cipher.encrypt("person@example.com"))
    ciphertext[-1] ^= 1
    encoded_ciphertext = base64.urlsafe_b64encode(ciphertext).decode("ascii")

    with pytest.raises(ValueError) as caught:
        cipher.decrypt(bytes(ciphertext))

    assert "person@example.com" not in str(caught.value)
    assert encoded_ciphertext not in str(caught.value)


def test_contact_cipher_requires_exactly_32_key_bytes():
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        ContactCipher(b"short")


def test_new_secret_is_random_urlsafe_32_byte_material():
    first = new_secret()
    second = new_secret()

    assert first != second
    assert len(base64.urlsafe_b64decode(first + "=")) == 32
    assert len(base64.urlsafe_b64decode(second + "=")) == 32


def test_token_digest_comparison_accepts_only_matching_secret():
    codec = TokenCodec(b"t" * 32)
    digest = codec.digest("raw-token")

    assert codec.matches("raw-token", digest)
    assert not codec.matches("wrong-token", digest)
    assert not codec.matches("raw-token", "not-a-valid-digest")


def test_signed_session_uses_required_format_and_round_trips():
    codec = TokenCodec(b"s" * 32)
    raw = "session-secret"

    signed = codec.sign_session(raw, expires=1_800_000_000)

    assert signed.split(".")[:3] == ["v1", "1800000000", raw]
    assert len(signed.split(".")) == 4
    assert codec.verify_session(signed, now=1_700_000_000) == raw


@pytest.mark.parametrize("mutation", ["signature", "raw", "version", "expires"])
def test_signed_session_rejects_tampering_without_disclosure(mutation):
    codec = TokenCodec(b"s" * 32)
    raw = "session-secret"
    parts = codec.sign_session(raw, expires=1_800_000_000).split(".")
    index = {"version": 0, "expires": 1, "raw": 2, "signature": 3}[mutation]
    parts[index] = f"{parts[index]}x"
    tampered = ".".join(parts)

    with pytest.raises(ValueError) as caught:
        codec.verify_session(tampered, now=1_700_000_000)

    assert raw not in str(caught.value)
    assert tampered not in str(caught.value)


def test_signed_session_rejects_non_ascii_signature_as_invalid_token():
    codec = TokenCodec(b"s" * 32)
    parts = codec.sign_session("session-secret", expires=1_800_000_000).split(".")
    parts[3] = "non-ascii-é"

    with pytest.raises(ValueError, match="^invalid session token$"):
        codec.verify_session(".".join(parts), now=1_700_000_000)


def test_signed_session_rejects_expiry_without_token_disclosure():
    codec = TokenCodec(b"s" * 32)
    raw = "session-secret"
    signed = codec.sign_session(raw, expires=1_800_000_000)

    with pytest.raises(ValueError) as caught:
        codec.verify_session(signed, now=1_800_000_000)

    assert raw not in str(caught.value)
    assert signed not in str(caught.value)


def test_csrf_verification_fails_closed_on_missing_mismatch_or_bad_digest():
    codec = TokenCodec(b"s" * 32)
    expected_digest = codec.digest("csrf-secret")

    assert verify_csrf(codec, "csrf-secret", expected_digest)
    assert not verify_csrf(codec, None, expected_digest)
    assert not verify_csrf(codec, "wrong", expected_digest)
    assert not verify_csrf(codec, "csrf-secret", None)
    assert not verify_csrf(codec, "csrf-secret", "not-a-valid-digest")


def test_settings_reads_only_revalidated_exact_length_keys(tmp_path):
    settings = Settings.for_tests(tmp_path)

    assert settings.read_key("contact") == b"c" * 32
    settings.contact_key_path.write_bytes(b"sensitive-but-short")

    with pytest.raises(RuntimeError) as caught:
        settings.read_key("contact")

    assert "sensitive-but-short" not in str(caught.value)
