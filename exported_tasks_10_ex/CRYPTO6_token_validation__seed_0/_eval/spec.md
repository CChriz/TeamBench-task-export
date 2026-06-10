# CRYPTO6: JWT Token Validation

## Goal

A Python JWT authentication system has security vulnerabilities in token
validation and race conditions in token refresh. Fix all bugs while keeping
existing passing tests green.

## Requirements

1. Fix all 4 token validation bugs in `auth.py`
2. Fix both race conditions in `refresh.py`
3. All existing tests must continue to pass: `pytest tests/`
4. No tokens with algorithm "none" may be accepted
5. Expired tokens must be rejected immediately (zero grace window)

## Validation Bugs (4 total in `auth.py`)

1. **Algorithm "none" accepted**: The `decode_token()` function does not reject
   tokens with `alg: "none"`. An attacker can forge tokens without a secret key.
   Fix: explicitly reject `alg="none"` or restrict to allowed algorithms only.

2. **Expiration off-by-one**: The `is_expired()` check uses strict less-than
   (`current_time < exp`) instead of less-than-or-equal (`current_time <= exp`).
   A token expiring at exactly the current timestamp is incorrectly accepted.
   Fix: use `<=` comparison so tokens are rejected at their exact expiration time.

3. **Grace window should be zero**: The `validate_token()` function accepts
   expired tokens within a configurable grace window (default 300 seconds).
   This was a development convenience that must be removed for production.
   Fix: set grace window to 0 (or remove the grace window logic entirely).

4. **Missing issuer validation**: The `validate_token()` function does not check
   the `iss` (issuer) claim against the list of allowed issuers. Any issuer is
   accepted. Fix: validate that `iss` is in `ALLOWED_ISSUERS`.

## Refresh Race Conditions (2 total in `refresh.py`)

1. **No token blacklisting**: After a token is refreshed, the old token remains
   valid until its natural expiration. An attacker who captures the old token
   can use it concurrently with the new one.
   Fix: add the old token to a blacklist when issuing a new token.

2. **Duplicate token on concurrent refresh**: Two simultaneous refresh requests
   for the same token can both succeed, issuing two different new tokens.
   Fix: use a lock or atomic check-and-set to prevent concurrent refresh.

## Supporting Files

- `auth.py` — token creation and validation (4 bugs)
- `refresh.py` — token refresh logic (2 race conditions)
- `middleware.py` — request authentication middleware
- `tests/test_auth.py` — existing tests (must all pass)
- `config.py` — configuration (allowed issuers, secret key, etc.)
