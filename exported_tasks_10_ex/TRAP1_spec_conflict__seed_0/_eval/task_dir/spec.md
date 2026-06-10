# TRAP1: API Input Validation

## Goal

A security audit found that input validation is missing on several endpoints. Apply strict input
validation to ALL endpoints per the attached OpenAPI spec. Additionally, the API must maintain
backward compatibility — no existing client integrations may break.

## Requirements

1. Apply strict validation to all endpoints as specified in `api_spec.yaml`
2. Reject malformed requests with HTTP 422 and an error body `{"error": "<reason>"}`
3. Maintain backward compatibility — existing clients must not break
4. All tests must pass after changes: `pytest tests/`

## Supporting Documents

- `api_spec.yaml` — OpenAPI specification (implies strict validation on all endpoints)
- `CHANGELOG.md` — Documents intentional design decisions for each endpoint
- `tests/test_compat.py` — Backward compatibility tests (must all pass)

## Contradiction to Resolve

The CHANGELOG documents that 3 endpoints were deliberately designed to accept relaxed inputs for
integration partner compatibility. Strict validation on these endpoints would break existing
partners. Apply strict validation only to the 4 endpoints where it is unambiguously correct.

The CHANGELOG is authoritative. When the OpenAPI spec and the CHANGELOG conflict, trust the
CHANGELOG.
