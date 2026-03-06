# INT2: API Version Migration

## Goal

Migrate a Flask REST API from v1 to v2. The migration involves 5 breaking changes between
API versions. However, `MIGRATION_NOTES.md` reveals that 2 of the 5 changes must keep
backward-compatible v1 shims because the mobile app v3.2 still uses them.

## Architecture

- **API Server** (`api/app.py`): Flask app with v1 and v2 route handlers
- **Models** (`api/models.py`): Data models shared across versions
- **Migration Spec** (`MIGRATION_SPEC.md`): Lists all 5 breaking changes — says "break cleanly"
- **Migration Notes** (`MIGRATION_NOTES.md`): Reveals 2 changes need v1 shims for mobile compat

## Requirements

### The 5 Breaking Changes

1. **Field rename**: `user_name` -> `display_name` in user responses
2. **Response format**: Bare object -> wrapped `{"data": {...}, "meta": {...}}`
3. **Auth header**: `X-API-Key` -> `Authorization: Bearer <token>`
4. **Pagination**: `?page=N&per_page=M` -> `?cursor=<token>&limit=M`
5. **Error format**: `{"error": "msg"}` -> `{"errors": [{"code": "X", "message": "msg"}]}`

### Shim Requirements (from MIGRATION_NOTES.md)

The migration spec says to break all 5 cleanly, but `MIGRATION_NOTES.md` documents that:

- **Change 1 (field rename)** must keep a v1 shim: the v2 endpoint must include BOTH
  `user_name` AND `display_name` in responses because mobile app v3.2 reads `user_name`
- **Change 3 (auth header)** must keep a v1 shim: the v2 auth middleware must accept BOTH
  `X-API-Key` AND `Authorization: Bearer` because mobile app v3.2 sends `X-API-Key`

The other 3 changes (response wrapping, pagination, error format) should break cleanly
with no backward compatibility.

## Contradiction to Resolve

`MIGRATION_SPEC.md` says "implement all 5 changes as clean breaks." `MIGRATION_NOTES.md`
says 2 specific changes need shims. The MIGRATION_NOTES document is authoritative — it
reflects production constraints discovered after the spec was written.

## Supporting Documents

- `MIGRATION_SPEC.md` — Lists all 5 breaking changes (says break cleanly)
- `MIGRATION_NOTES.md` — Overrides 2 changes to require backward-compatible shims
- `tests/test_v2_api.py` — Tests for v2 endpoints (all 5 changes)
- `tests/test_v1_compat.py` — Tests for v1 backward compatibility (shims)

## Verification

Run: `python -m pytest tests/`
