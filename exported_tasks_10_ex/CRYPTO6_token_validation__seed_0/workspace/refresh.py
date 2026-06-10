"""
Token refresh logic for auth_service.

Contains 2 race conditions that must be fixed.
"""
import time
import threading
from auth import create_token, validate_token, decode_token
from config import ALLOWED_ISSUERS, TOKEN_LIFETIME

# Token blacklist (should be used but currently isn't)
_blacklist: set = set()

# Lock for concurrent refresh (should be used but currently isn't)
_refresh_lock = threading.Lock()

# Track active refreshes to prevent duplicates
_active_refreshes: dict = {}


def refresh_token(old_token: str) -> str | None:
    """
    Refresh an expired or about-to-expire token.

    RACE CONDITION 1: Old token is NOT added to blacklist after refresh.
    An attacker with the old token can use it until natural expiration.

    RACE CONDITION 2: No lock/atomic check prevents concurrent refresh.
    Two simultaneous requests can both succeed, creating duplicate tokens.
    """
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
    new_claims = {
        "sub": sub,
        "iss": iss or (ALLOWED_ISSUERS[0] if ALLOWED_ISSUERS else "unknown"),
    }
    new_token = create_token(new_claims, expires_in=TOKEN_LIFETIME)

    return new_token


def is_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted (revoked)."""
    return token in _blacklist
