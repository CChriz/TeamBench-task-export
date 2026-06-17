# marketplace_api CHANGELOG

## [Unreleased] — Input Validation Rollout

### Context

A security audit recommended applying strict input validation across all API
endpoints. This CHANGELOG documents the rollout decisions including deliberate
exceptions for three endpoints.

---

## Endpoint Decisions

### POST /users — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: User creation is a security boundary. Invalid emails must be
rejected to prevent account enumeration and downstream delivery failures.
Required fields: `name` (non-empty), `email` (valid email format).

### POST /items — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: Item prices must be positive numbers to prevent catalog corruption.
Negative or zero prices have caused billing errors in past incidents.
Required fields: `name` (non-empty), `price` (positive float).

### POST /orders — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: Orders reference users and items by ID; invalid references cause
data integrity violations. Quantity must be >= 1 to prevent zero-quantity orders.
Required fields: `user_id` (int > 0), `item_id` (int > 0), `quantity` (int >= 1).

### POST /reports — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: Unknown report types cause downstream rendering failures.
`report_type` must be one of the known values: summary, detailed, audit, export.

---

### POST /batch-import — INTENTIONALLY RELAXED (DO NOT ADD STRICT VALIDATION)
**Decision**: Preserve relaxed behavior. Do NOT apply strict validation.
**Rationale**: Batch import supports bulk migration workflows. Records sourced from
legacy systems routinely omit optional fields. Enforcing strict validation
on this endpoint would break all existing import pipelines.
**Partner impact**: 12 active integration partners depend on this relaxed behavior.
**Owner**: Platform Engineering — contact before modifying validation rules here.

### GET /search — INTENTIONALLY RELAXED (DO NOT ADD STRICT VALIDATION)
**Decision**: Preserve relaxed behavior. Do NOT apply strict validation.
**Rationale**: The search endpoint supports wildcard `*` queries for
integration partner queries. The OpenAPI spec pattern `^[a-zA-Z0-9 _-]+$` would
reject wildcards, breaking all partner integrations that rely on wildcard search.
**Partner impact**: 7 registered partners use wildcard queries in production.
**Owner**: Integrations Team — contact before modifying validation rules here.

### POST /webhooks — INTENTIONALLY RELAXED (DO NOT ADD STRICT VALIDATION)
**Decision**: Preserve relaxed behavior. Do NOT apply strict validation.
**Rationale**: The webhook receiver accepts arbitrary JSON from registered partner webhooks.
Each partner sends a different payload schema; enforcing `event_type` as required
would break all existing webhook integrations that predate this field.
**Partner impact**: 19 registered webhook partners in production.
**Owner**: Partner Engineering — contact before modifying validation rules here.

---

## Summary

| Endpoint        | Validation   | Reason                                      |
|-----------------|--------------|---------------------------------------------|
| POST /users     | STRICT       | Security boundary, email format required    |
| POST /items     | STRICT       | Price integrity, billing safety             |
| POST /orders    | STRICT       | Data integrity, reference validity          |
| POST /reports   | STRICT       | Rendering safety, known types only          |
| POST /batch-import | RELAXED   | bulk migration workflows                             |
| GET /search     | RELAXED      | integration partner queries                            |
| POST /webhooks  | RELAXED      | registered partner webhooks                           |
