"""
Parameterized generator for CRYPTO6: JWT Token Validation.

Each seed produces a JWT auth system with 4 validation bugs in auth.py
and 2 race conditions in refresh.py.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed pools ────────────────────────────────────────────────────────────

SECRET_KEYS = [
    "super-secret-key-2024-prod",
    "jwt-signing-key-alpha-9x3",
    "hmac-secret-v3-production",
    "token-sign-key-8f2a1b",
    "auth-secret-2024-rev2",
    "signing-key-prod-7d9e",
    "jwt-hmac-secret-v5",
    "platform-auth-key-2024",
]

ISSUER_SETS = [
    ["auth.myapp.com", "sso.myapp.com"],
    ["identity.platform.io", "login.platform.io"],
    ["auth.service.internal", "sso.service.internal"],
    ["id.company.com", "auth.company.com"],
    ["token.api.dev", "oauth.api.dev"],
    ["accounts.example.org", "auth.example.org"],
]

TOKEN_LIFETIMES = [300, 600, 900, 1800, 3600, 7200]

GRACE_WINDOWS = [60, 120, 180, 300, 600]

APP_NAMES = [
    "auth_service", "identity_provider", "token_gateway",
    "sso_platform", "oauth_server", "session_manager",
    "credential_service", "access_controller",
]


class Generator(TaskGenerator):
    task_id = "CRYPTO6_token_validation"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 8

        secret_key = SECRET_KEYS[idx]
        issuers = ISSUER_SETS[seed % len(ISSUER_SETS)]
        lifetime = TOKEN_LIFETIMES[seed % len(TOKEN_LIFETIMES)]
        grace_window = GRACE_WINDOWS[seed % len(GRACE_WINDOWS)]
        app_name = APP_NAMES[idx]

        workspace_files = self._make_workspace(
            secret_key=secret_key,
            issuers=issuers,
            lifetime=lifetime,
            grace_window=grace_window,
            app_name=app_name,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CRYPTO6_token_validation")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CRYPTO6_token_validation",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "validation_bugs": [
                    "alg_none_accepted",
                    "exp_off_by_one",
                    "grace_window_nonzero",
                    "missing_iss_check",
                ],
                "race_conditions": [
                    "no_token_blacklist",
                    "concurrent_refresh_duplicate",
                ],
                "secret_key": secret_key,
                "issuers": issuers,
                "lifetime": lifetime,
                "grace_window": grace_window,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(
        self,
        secret_key: str,
        issuers: list[str],
        lifetime: int,
        grace_window: int,
        app_name: str,
    ) -> dict:
        files = {}

        issuers_repr = repr(issuers)

        # ── config.py ────────────────────────────────────────────────────
        files["config.py"] = f"""\
\"\"\"Configuration for {app_name}.\"\"\"

SECRET_KEY = "{secret_key}"
ALGORITHM = "HS256"
TOKEN_LIFETIME = {lifetime}  # seconds
GRACE_WINDOW = {grace_window}  # seconds — BUG: should be 0 for production
ALLOWED_ISSUERS = {issuers_repr}
REFRESH_TOKEN_LIFETIME = {lifetime * 4}  # seconds
"""

        # ── auth.py (4 validation bugs) ──────────────────────────────────
        files["auth.py"] = f"""\
\"\"\"
JWT token creation and validation for {app_name}.

Contains 4 security bugs that must be fixed.
\"\"\"
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
    msg = f"{{header_b64}}.{{payload_b64}}".encode()
    sig = hmac.new(key.encode(), msg, hashlib.sha256).digest()
    return _b64_encode(sig)


def create_token(claims: dict, expires_in: int = TOKEN_LIFETIME) -> str:
    \"\"\"Create a signed JWT token.\"\"\"
    header = {{"alg": ALGORITHM, "typ": "JWT"}}
    payload = dict(claims)
    payload["iat"] = int(time.time())
    payload["exp"] = int(time.time()) + expires_in

    header_b64 = _b64_encode(json.dumps(header).encode())
    payload_b64 = _b64_encode(json.dumps(payload).encode())
    signature = _sign(header_b64, payload_b64, SECRET_KEY)

    return f"{{header_b64}}.{{payload_b64}}.{{signature}}"


def decode_token(token: str) -> dict | None:
    \"\"\"
    Decode and verify a JWT token.

    BUG 1: Does not reject algorithm 'none'.
    \"\"\"
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
    \"\"\"
    Check if a token is expired.

    BUG 2: Uses strict less-than instead of less-than-or-equal.
    A token expiring at exactly current time is incorrectly accepted.
    \"\"\"
    exp = payload.get("exp", 0)
    now = int(time.time())
    # Bug: should be now >= exp (reject at exact expiration)
    return now > exp


def validate_token(token: str) -> dict | None:
    \"\"\"
    Fully validate a JWT token: decode, check expiration, check issuer.

    BUG 3: Grace window is nonzero (accepts recently expired tokens).
    BUG 4: Does not validate the issuer claim.
    \"\"\"
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
"""

        # ── refresh.py (2 race conditions) ───────────────────────────────
        files["refresh.py"] = f"""\
\"\"\"
Token refresh logic for {app_name}.

Contains 2 race conditions that must be fixed.
\"\"\"
import time
import threading
from auth import create_token, validate_token, decode_token
from config import ALLOWED_ISSUERS, TOKEN_LIFETIME

# Token blacklist (should be used but currently isn't)
_blacklist: set = set()

# Lock for concurrent refresh (should be used but currently isn't)
_refresh_lock = threading.Lock()

# Track active refreshes to prevent duplicates
_active_refreshes: dict = {{}}


def refresh_token(old_token: str) -> str | None:
    \"\"\"
    Refresh an expired or about-to-expire token.

    RACE CONDITION 1: Old token is NOT added to blacklist after refresh.
    An attacker with the old token can use it until natural expiration.

    RACE CONDITION 2: No lock/atomic check prevents concurrent refresh.
    Two simultaneous requests can both succeed, creating duplicate tokens.
    \"\"\"
    # Decode the old token (allow expired tokens for refresh)
    payload = decode_token(old_token)
    if payload is None:
        return None

    # Check that the token has required claims
    sub = payload.get("sub")
    iss = payload.get("iss")
    if not sub:
        return None

    # BUG: No blacklisting — old token remains valid
    # Should add: _blacklist.add(old_token)

    # BUG: No lock — concurrent refresh creates duplicates
    # Should use: with _refresh_lock: ...

    # Create new token with same claims
    new_claims = {{
        "sub": sub,
        "iss": iss or (ALLOWED_ISSUERS[0] if ALLOWED_ISSUERS else "unknown"),
    }}
    new_token = create_token(new_claims, expires_in=TOKEN_LIFETIME)

    return new_token


def is_blacklisted(token: str) -> bool:
    \"\"\"Check if a token has been blacklisted (revoked).\"\"\"
    return token in _blacklist
"""

        # ── middleware.py ────────────────────────────────────────────────
        files["middleware.py"] = f"""\
\"\"\"
Request authentication middleware for {app_name}.
\"\"\"
from auth import validate_token
from refresh import is_blacklisted


def authenticate_request(auth_header: str) -> dict | None:
    \"\"\"
    Authenticate an incoming request using the Authorization header.

    Returns the token payload if valid, None otherwise.
    \"\"\"
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Strip "Bearer " prefix

    # Check blacklist
    if is_blacklisted(token):
        return None

    return validate_token(token)
"""

        # ── tests/__init__.py ────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_auth.py ───────────────────────────────────────────
        files["tests/test_auth.py"] = f"""\
\"\"\"
Tests for JWT auth system.

These tests verify basic functionality. They currently pass but miss
the security edge cases that the bugs exploit.
\"\"\"
import time
import pytest
from auth import create_token, decode_token, validate_token, is_expired
from config import SECRET_KEY, ALLOWED_ISSUERS


def test_create_and_decode_token():
    token = create_token({{"sub": "user1", "iss": ALLOWED_ISSUERS[0]}})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user1"


def test_token_has_exp_claim():
    token = create_token({{"sub": "user2", "iss": ALLOWED_ISSUERS[0]}})
    payload = decode_token(token)
    assert "exp" in payload
    assert "iat" in payload


def test_valid_token_not_expired():
    token = create_token({{"sub": "user3", "iss": ALLOWED_ISSUERS[0]}}, expires_in=3600)
    payload = decode_token(token)
    assert not is_expired(payload)


def test_validate_returns_payload():
    token = create_token({{"sub": "user4", "iss": ALLOWED_ISSUERS[0]}}, expires_in=3600)
    result = validate_token(token)
    assert result is not None
    assert result["sub"] == "user4"


def test_invalid_signature_rejected():
    token = create_token({{"sub": "user5", "iss": ALLOWED_ISSUERS[0]}})
    # Tamper with the token
    parts = token.split(".")
    parts[2] = "tampered_signature_value"
    bad_token = ".".join(parts)
    assert decode_token(bad_token) is None


def test_malformed_token_rejected():
    assert decode_token("not.a.valid.jwt.token.at.all") is None
    assert decode_token("") is None
    assert decode_token("single_part") is None
"""

        files["requirements.txt"] = "pyjwt\npytest\n"

        return files
