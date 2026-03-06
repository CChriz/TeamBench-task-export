# P7: Data Retention Policy Compliance

## Goal
Fix a Python user data management application to comply with GDPR-style data
retention policies. The app has 3 policy violations that must be resolved.

## Hard Requirements

### Policy Violations
1. **No auto-deletion**: User records older than the retention period (configurable, default 90 days) must be automatically deleted when `enforce_retention()` is called. Currently, `enforce_retention()` is a no-op stub.
2. **Anonymization broken**: The `anonymize_user(user_id)` function should replace PII fields (`name`, `email`, `phone`) with `"[REDACTED]"` but currently only clears `email`. Fix to anonymize all 3 fields.
3. **Missing audit log**: All deletion and anonymization operations must be logged to `audit_log.json` with `timestamp`, `action`, `user_id`, and `reason`. Currently no audit logging exists.

### Data Model
- User records stored in `data/users.json` (array of objects with `id`, `name`, `email`, `phone`, `created_at`, `last_active`)
- Retention period: records where `last_active` is older than 90 days from the reference date
- Config in `config.json`: `retention_days`, `reference_date`

### Commands
- `python manage.py enforce` — delete expired records
- `python manage.py anonymize USER_ID` — anonymize a specific user
- `python manage.py report` — generate retention compliance report

## Deliverables
- Fixed `manage.py`
- Working `audit_log.json` after operations
- Verifier confirms all 3 violations fixed.
