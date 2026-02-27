# EA5: Dependency Audit — Fix Vulnerable Dependencies

## Goal

The project's Python dependencies contain known CVEs. Run a dependency audit, fix all
vulnerabilities, and ensure the application still works correctly.

## Audit Command

```
pip-audit -r requirements.txt 2>&1
```

Target: `pip-audit` reports **0 vulnerabilities**.

## Project Structure

- `requirements.txt` — package version pins
- `app/image_processor.py` — image processing (uses Pillow)
- `app/crypto_utils.py` — cryptographic operations (uses cryptography library)
- `app/routes.py` — Flask routes (uses Werkzeug)
- `app/api_client.py` — HTTP client (uses requests)
- `app/config_loader.py` — YAML configuration loading (uses PyYAML)

## API Compatibility Notes

When upgrading to secure versions, some packages had breaking API changes. Simply pinning
to a newer version is not sufficient for all packages — the application code may need updates.

**Pillow** (image processing library): A commonly used resampling filter constant was
**removed** in Pillow 10.0. Code using the removed constant will raise `AttributeError`
at runtime after the version upgrade. You must update the affected call site.

**cryptography** (Fernet/RSA library): A `backend` parameter accepted by cryptographic
primitives in older versions was **deprecated and subsequently removed** in newer versions.
Any call passing `backend=default_backend()` will fail after the version upgrade. These
arguments must be removed from all affected call sites in `app/crypto_utils.py`.

For the other dependencies in `requirements.txt`, pinning to the safe version is sufficient
— no API changes are needed.

## Deliverables

- `requirements.txt` with all CVEs patched (safe versions pinned)
- Application code updated at affected call sites for breaking API changes
- All tests pass: `pytest tests/`
- `pip-audit -r requirements.txt` reports 0 vulnerabilities
