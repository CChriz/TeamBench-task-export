# SCALE1: Large Codebase Library Migration (requests → httpx)

## Goal
Migrate a 20-file Python codebase from the `requests` library to `httpx`.

## 8 Breaking Changes to Address

1. **Import style**: The top-level import and function calls must use the `httpx` namespace instead of `requests`
2. **Session / client**: The session object type has changed; the new client must be used with a context manager pattern
3. **Empty response body**: When a response has no body, the JSON parsing behavior differs between libraries — the new library returns a different sentinel value that callers must handle
4. **Timeout type**: The timeout argument accepts a different type in the new library; passing a plain integer is no longer valid
5. **Basic authentication**: The authentication helper class has a different name and import path in the new library
6. **Streaming line iteration**: The streaming iterator no longer accepts an `encoding` keyword argument; any such argument must be removed
7. **Exception types**: Network error exceptions have been renamed; catch clauses must reference the new exception class names
8. **Test mocking**: The HTTP mocking library used in tests is incompatible with the new HTTP client; tests must use the compatible mock library (`respx` instead of `requests_mock`)

## 3 False-Positive Patterns (DO NOT CHANGE)

1. `app/services/notification.py` — uses `aiohttp`, not `requests`; must not be modified
2. `app/config/constants.py` — contains a variable named `TIMEOUT` used for rate limiting, unrelated to HTTP configuration; must not be modified
3. `app/config/settings.py` — contains a config key `"requests_per_minute"` referring to a rate limit, not the library; must not be modified

## Deliverables
- All files migrated from `requests` to `httpx`
- `requirements.txt` updated (`requests` → `httpx`, `requests_mock` → `respx`)
- False-positive files left untouched
- All 10 tests pass
