# EA1: Security Scan — Fix Security Vulnerabilities

## Goal

A Flask web application has security vulnerabilities that need to be identified and fixed.
Use `bandit` to discover the issues, then fix them while preserving the existing test suite.

## Quality Requirements

- `bandit -r app/ -ll` reports **0 HIGH and 0 MEDIUM** severity issues in the application code
- All existing tests pass: `pytest tests/`

## Application Structure

- `app/routes.py` — Flask route handlers (search, data processing endpoints)
- `app/config.py` — application configuration and secrets management
- `app/utils.py` — utility functions including report generation
- `app/auth.py` — user authentication and password handling
- `app/parser.py` — XML/configuration parsing
- `app/cache.py` — caching layer (Redis-backed)
- `app/tokens.py` — token generation for sessions

## False Positive Patterns

The test suite (`tests/`) contains intentional patterns that bandit flags but are NOT real vulnerabilities.
Do **not** modify any files under `tests/`.

**Backward-compatibility tests**: Some tests exercise legacy code paths (e.g., verifying that old
hash formats are correctly recognized) and necessarily use the same algorithm as the legacy code.
These are test-only and do not represent production credentials or hashing choices.

**Test fixture credentials**: String literals used as test passwords or tokens in test files are
test fixtures, not hardcoded production secrets. They are expected and safe.

**Test harness subprocesses**: Integration tests that invoke subprocesses to test the application's
own reporting functionality use fixed, non-user-controlled command strings. These are not injection
vulnerabilities.

Bandit will flag all three patterns — they should be left unchanged.

## Deliverables

- Fixed application code (`app/` directory)
- All vulnerabilities in application code remediated
- All tests pass; test files unchanged
