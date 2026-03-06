# S7: Environment Variable Configuration Fix

## Goal
Fix a Python application (`config.py`) that reads environment variables incorrectly.
The app has 3 configuration bugs that cause crashes or wrong behavior.

## Hard Requirements

1. **Missing default value**: `os.environ["DB_HOST"]` crashes with KeyError when the var is unset. Fix to use `os.environ.get("DB_HOST", "localhost")`.
2. **Wrong type cast**: `int(os.environ.get("CACHE_TTL", "300"))` works, but `MAX_RETRIES` is read as a string and compared with `>` against an integer, causing a TypeError. Cast it to `int`.
3. **Case sensitivity**: The app reads `os.environ.get("api_key")` but the `.env.example` and docs specify `API_KEY` (uppercase). Fix to read the correct case.

## Additional Rules
- `app.py` imports from `config.py` — both must be checked.
- After fixes, running `python app.py` with no environment variables set must not crash (should use defaults).
- The `.env.example` file documents the expected variable names and defaults.

## Deliverables
- Fixed `config.py`
- Fixed `app.py` if needed
- Verifier confirms app runs with defaults and all 3 bugs are fixed.
