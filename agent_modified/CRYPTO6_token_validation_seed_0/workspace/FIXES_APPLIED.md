## Role: Fix Developer

### Fixes Applied

- **Bug 1: Algorithm "none" Accepted** — APPLIED
  - File: `auth.py:61-64` → `auth.py:62-65`
  - Before:
    ```python
        # BUG: accepts alg="none" — should reject tokens with no signature
        alg = header.get("alg", "none")
        if alg == "none":
            return payload  # Bug: should return None / raise

        # Verify signature for HS256
    ```
  - After:
    ```python
        # Reject alg="none" and missing/unknown algorithms
        alg = header.get("alg", "")
        if alg.lower() == "none" or alg != ALGORITHM:
            return None

        # Verify signature for HS256
    ```

- **Bug 3: Grace Window Nonzero** — APPLIED
  - File: `config.py:6` → `config.py:8`
  - Before:
    ```python
    GRACE_WINDOW = 60  # seconds — BUG: should be 0 for production
    ```
  - After:
    ```python
    GRACE_WINDOW = 0  # seconds — zero grace for production
    ```
  - Also: `auth.py:104` condition changed from `now > exp + GRACE_WINDOW` to `now >= exp + GRACE_WINDOW`
  - Before:
    ```python
        if now > exp + GRACE_WINDOW:
            return None
    ```
  - After:
    ```python
        if now >= exp + GRACE_WINDOW:
            return None
    ```

- **Bug 4: Missing Issuer Validation** — APPLIED
  - File: `auth.py:107-111` → `auth.py:108-110`
  - Before:
    ```python
        # BUG 4: Missing issuer validation — any issuer accepted
        # Should check: payload.get("iss") in ALLOWED_ISSUERS

        return payload
    ```
  - After:
    ```python
        # Validate issuer
        if payload.get("iss") not in ALLOWED_ISSUERS:
            return None

        return payload
    ```

- **Bug 5: No Token Blacklisting on Refresh** — APPLIED
  - File: `refresh.py:42-43` → `refresh.py:44-45`
  - Before:
    ```python
        # BUG: No blacklisting — old token remains valid
        # Should add: _blacklist.add(old_token)
    ```
  - After:
    ```python
            # Blacklist the old token atomically with creating the new one
            _blacklist.add(old_token)
    ```

- **Bug 6: Duplicate Token on Concurrent Refresh** — APPLIED
  - File: `refresh.py:45-55` → `refresh.py:42-54`
  - Before:
    ```python
        # BUG: No lock — concurrent refresh creates duplicates
        # Should use: with _refresh_lock: ...

        # Create new token with same claims
        new_claims = {
            "sub": sub,
            "iss": iss or (ALLOWED_ISSUERS[0] if ALLOWED_ISSUERS else "unknown"),
        }
        new_token = create_token(new_claims, expires_in=TOKEN_LIFETIME)

        return new_token
    ```
  - After:
    ```python
        # Acquire lock to prevent concurrent duplicate refreshes
        with _refresh_lock:
            # Blacklist the old token atomically with creating the new one
            _blacklist.add(old_token)

            # Create new token with same claims
            new_claims = {
                "sub": sub,
                "iss": iss or (ALLOWED_ISSUERS[0] if ALLOWED_ISSUERS else "unknown"),
            }
            new_token = create_token(new_claims, expires_in=TOKEN_LIFETIME)

        return new_token
    ```

- **Finding 1: Weak / Hardcoded SECRET_KEY** — APPLIED
  - File: `config.py:1-3` → `config.py:1-5`
  - Before:
    ```python
    """Configuration for auth_service."""

    SECRET_KEY = "super-secret-key-2024-prod"
    ```
  - After:
    ```python
    """Configuration for auth_service."""
    import os
    import secrets

    SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
    ```

- **Bug 2: Expiration Off-by-One** — APPLIED
  - File: `auth.py:83-86` → `auth.py:84-86`
  - Before:
    ```python
        exp = payload.get("exp", 0)
        now = int(time.time())
        # Bug: should be now >= exp (reject at exact expiration)
        return now > exp
    ```
  - After:
    ```python
        exp = payload.get("exp", 0)
        now = int(time.time())
        return now >= exp
    ```

- **Finding 2: No Subject (`sub`) Validation in `validate_token()`** — APPLIED
  - File: `auth.py:115` → `auth.py:112-113`
  - Before:
    ```python
        return payload
    ```
  - After (with Bug 4 fix already applied):
    ```python
        # Validate subject is present
        if not payload.get("sub"):
            return None

        return payload
    ```

- **Finding 3: Broad Exception Handling in `decode_token()`** — APPLIED
  - File: `auth.py:72-73` → `auth.py:73-74`
  - Before:
    ```python
        except Exception:
            return None
    ```
  - After:
    ```python
        except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
            return None
    ```
  - Also added `import binascii` at `auth.py:11`

### Test Results
```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.0, pluggy-1.6.0 -- /home/cz776/miniconda3/envs/jiuwenswarm6/bin/python3
cachedir: .pytest_cache
rootdir: /home/cz776/.jiuwenswarm-instances/jiuwenswarm6/.agent_teams/jiuwen_team_sess_19ed460bb06_4e15b1/team-workspace
plugins: anyio-4.13.0
collecting ... collected 6 items

tests/test_auth.py::test_create_and_decode_token PASSED                  [ 16%]
tests/test_auth.py::test_token_has_exp_claim PASSED                      [ 33%]
tests/test_auth.py::test_valid_token_not_expired PASSED                  [ 50%]
tests/test_auth.py::test_validate_returns_payload PASSED                 [ 66%]
tests/test_auth.py::test_invalid_signature_rejected PASSED               [ 83%]
tests/test_auth.py::test_malformed_token_rejected PASSED                 [100%]

============================== 6 passed in 0.01s ===============================
```

### Verdict
- READY-FOR-VERIFICATION — All 9 fixes applied (6 confirmed bugs + 3 additional findings). All 6 tests pass. Pipeline can proceed to Stage 3 (Adversarial Verification).
