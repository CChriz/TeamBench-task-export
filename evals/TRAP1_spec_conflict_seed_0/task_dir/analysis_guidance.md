# Analysis Guidance — TRAP1_spec_conflict

## Tools to run

- `find . -name "*.py" | head -30` — explore structure
- `cat CHANGELOG.md` — CRITICAL: read to identify intentional relaxed endpoints
- `cat api_spec.yaml` — read the OpenAPI spec
- `python -m py_compile app/routes.py` — syntax check

## Key Findings (expected)

- `CHANGELOG.md` documents 3 endpoints with intentional relaxed behavior
- `api_spec.yaml` implies strict validation on all 7 endpoints
- Contradiction: applying the OpenAPI spec literally breaks backward compatibility

## What to tell Executor

Apply strict validation ONLY to: /users, /items, /orders, /reports
Do NOT change: /batch-import, /search, /webhooks (these are intentionally relaxed per CHANGELOG)

## Strict validation rules (per api_spec.yaml)

- POST /users: `name` (non-empty string) and `email` (valid format, contains @) required
- POST /items: `name` (non-empty string) and `price` (positive float) required
- POST /orders: `user_id` (integer > 0), `item_id` (integer > 0), `quantity` (integer >= 1) required
- POST /reports: `report_type` must be one of the allowed types listed in api_spec.yaml

## Relaxed endpoints (do NOT add strict validation)

- POST /batch-import — accepts CSV rows with missing optional fields (bulk migration support)
- GET /search — accepts wildcard `*` in query parameter (integration partner queries)
- POST /webhooks — accepts arbitrary JSON payload (registered partner webhooks)
