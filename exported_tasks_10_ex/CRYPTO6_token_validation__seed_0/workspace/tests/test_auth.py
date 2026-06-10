"""
Tests for JWT auth system.

These tests verify basic functionality. They currently pass but miss
the security edge cases that the bugs exploit.
"""
import time
import pytest
from auth import create_token, decode_token, validate_token, is_expired
from config import SECRET_KEY, ALLOWED_ISSUERS


def test_create_and_decode_token():
    token = create_token({"sub": "user1", "iss": ALLOWED_ISSUERS[0]})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user1"


def test_token_has_exp_claim():
    token = create_token({"sub": "user2", "iss": ALLOWED_ISSUERS[0]})
    payload = decode_token(token)
    assert "exp" in payload
    assert "iat" in payload


def test_valid_token_not_expired():
    token = create_token({"sub": "user3", "iss": ALLOWED_ISSUERS[0]}, expires_in=3600)
    payload = decode_token(token)
    assert not is_expired(payload)


def test_validate_returns_payload():
    token = create_token({"sub": "user4", "iss": ALLOWED_ISSUERS[0]}, expires_in=3600)
    result = validate_token(token)
    assert result is not None
    assert result["sub"] == "user4"


def test_invalid_signature_rejected():
    token = create_token({"sub": "user5", "iss": ALLOWED_ISSUERS[0]})
    # Tamper with the token
    parts = token.split(".")
    parts[2] = "tampered_signature_value"
    bad_token = ".".join(parts)
    assert decode_token(bad_token) is None


def test_malformed_token_rejected():
    assert decode_token("not.a.valid.jwt.token.at.all") is None
    assert decode_token("") is None
    assert decode_token("single_part") is None
