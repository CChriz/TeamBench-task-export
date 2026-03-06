# O9: Logging Configuration Fix

## Goal
Fix logging misconfiguration in a Python application. The app has 4 categories
of logging problems that need to be resolved.

## Hard Requirements

### Log Level Issues
1. **Wrong root log level**: The root logger is set to `DEBUG` in production config. Set it to `INFO`.
2. **Missing module-level override**: The `auth` module should log at `WARNING` level (security events only) but inherits root level.

### Structured Logging
3. **Missing structured fields**: Log entries must include `timestamp`, `level`, `module`, and `message` as JSON fields. Currently only `message` is present.
4. **Wrong timestamp format**: Timestamps must be ISO-8601 format (`%Y-%m-%dT%H:%M:%S`). Currently using `%m/%d/%Y %I:%M %p`.

### Log Rotation
5. **Rotation broken**: `RotatingFileHandler` has `maxBytes=0` (never rotates). Set to `maxBytes=10485760` (10MB).
6. **Missing backup count**: `backupCount` is not set. Set to `5`.

### PII Protection
7. **Email in logs**: The `process_user` function logs `f"Processing user {email}"`. Mask the email: show only first char + `***@domain`.
8. **Password in logs**: The `authenticate` function logs the password hash. Remove it entirely.

## Config
- Config file: `logging_config.py`
- App file: `app.py`
- Run: `python app.py` and check `logs/app.log`

## Deliverables
- Fixed `logging_config.py`
- Fixed `app.py` (PII masking)
- Verifier confirms all 8 issues resolved.
