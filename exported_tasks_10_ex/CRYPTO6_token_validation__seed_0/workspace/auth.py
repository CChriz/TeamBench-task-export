"""
JWT token creation and validation for auth_service.

Contains 4 security bugs that must be fixed.
"""
import json
import time
import hmac
import hashlib
import base64
from config import SECRET_KEY, ALGORITHM, TOKEN_LIFETIME, GRACE_WINDOW, ALLOWED_ISSUERS


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(header_b64: str, payload_b64: str, key: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(key.encode(), msg, hashlib.sha256).digest()
    return _b64_encode(sig)


def create_token(claims: dict, expires_in: int = TOKEN_LIFETIME) -> str:
    """Create a signed JWT token."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = dict(claims)
    payload["iat"] = int(time.time())
    payload["exp"] = int(time.time()) + expires_in

    header_b64 = _b64_encode(json.dumps(header).encode())
    payload_b64 = _b64_encode(json.dumps(payload).encode())
    signature = _sign(header_b64, payload_b64, SECRET_KEY)

    return f"{header_b64}.{payload_b64}.{signature}"


def decode_token(token: str) -> dict | None:
    """
    Decode and verify a JWT token.

    BUG 1: Does not reject algorithm 'none'.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        header = json.loads(_b64_decode(header_b64))
        payload = json.loads(_b64_decode(payload_b64))

        # BUG: accepts alg="none" — should reject tokens with no signature
        alg = header.get("alg", "none")
        if alg == "none":
            return payload  # Bug: should return None / raise

        # Verify signature for HS256
        expected_sig = _sign(header_b64, payload_b64, SECRET_KEY)
        if not hmac.compare_digest(signature_b64, expected_sig):
            return None

        return payload
    except Exception:
        return None


def is_expired(payload: dict) -> bool:
    """
    Check if a token is expired.

    BUG 2: Uses strict less-than instead of less-than-or-equal.
    A token expiring at exactly current time is incorrectly accepted.
    """
    exp = payload.get("exp", 0)
    now = int(time.time())
    # Bug: should be now >= exp (reject at exact expiration)
    return now > exp


def validate_token(token: str) -> dict | None:
    """
    Fully validate a JWT token: decode, check expiration, check issuer.

    BUG 3: Grace window is nonzero (accepts recently expired tokens).
    BUG 4: Does not validate the issuer claim.
    """
    payload = decode_token(token)
    if payload is None:
        return None

    # Check expiration with grace window
    exp = payload.get("exp", 0)
    now = int(time.time())

    # BUG 3: Grace window should be 0 for production
    if now > exp + GRACE_WINDOW:
        return None

    # BUG 4: Missing issuer validation — any issuer accepted
    # Should check: payload.get("iss") in ALLOWED_ISSUERS

    return payload
