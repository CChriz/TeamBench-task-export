"""
Parameterized generator for O9: Logging Configuration Fix.

Each seed produces:
  - Different auth module name (auth / authentication / security)
  - Different log file path
  - Different PII email / name in app.py
  - Buggy logging_config.py with 6 issues + buggy app.py with 2 PII leaks
  - Inline spec.md and brief.md (no disk reads)
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

AUTH_MODULES = ["auth", "authentication", "security"]
LOG_FILES = ["logs/app.log", "logs/service.log", "logs/output.log"]
PII_EMAILS = [
    "alice@company.com",
    "bob.smith@corp.org",
    "carol@startup.io",
]
PII_NAMES = ["Alice Johnson", "Bob Smith", "Carol White"]


class Generator(TaskGenerator):
    task_id = "O9_logging_config"
    domain = "operations"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        idx = seed % 3
        auth_module = AUTH_MODULES[idx]
        log_file = LOG_FILES[idx]
        pii_email = PII_EMAILS[idx]
        pii_name = PII_NAMES[idx]

        # Masked email for reference in expected (first char + ***@domain)
        local, domain = pii_email.split("@")
        masked_email = local[0] + "***@" + domain

        workspace_files = {
            "logging_config.py": self._buggy_logging_config(auth_module, log_file),
            "app.py": self._buggy_app(auth_module, pii_email, pii_name),
            "tests/test_logging.py": self._test_logging(auth_module, log_file, masked_email),
        }

        expected = {
            "auth_module": auth_module,
            "log_file": log_file,
            "pii_email": pii_email,
            "masked_email": masked_email,
            "bugs": [
                "root_level_debug_should_be_info",
                "missing_auth_module_warning_level",
                "formatter_missing_structured_fields",
                "wrong_timestamp_format",
                "rotation_maxbytes_zero",
                "missing_backup_count",
                "process_user_logs_raw_email",
                "authenticate_logs_password_hash",
            ],
            "bug_count": 8,
            "required_log_fields": ["timestamp", "level", "module", "message"],
            "correct_timestamp_fmt": "%Y-%m-%dT%H:%M:%S",
            "max_bytes": 10485760,
            "backup_count": 5,
            "root_level": "INFO",
            "auth_level": "WARNING",
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._spec(auth_module, log_file),
            brief_md=self._brief(auth_module),
            expected=expected,
            workspace_files=workspace_files,
        )

    def _buggy_logging_config(self, auth_module: str, log_file: str) -> str:
        return f'''\
"""Logging configuration for the application.

Bugs to fix:
  BUG1: Root logger set to DEBUG — should be INFO in production
  BUG2: No module-level override for '{auth_module}' — should be WARNING
  BUG3: Formatter only logs %(message)s — must include timestamp, level, module as JSON
  BUG4: datefmt wrong format — should be ISO-8601 (%Y-%m-%dT%H:%M:%S)
  BUG5: RotatingFileHandler has maxBytes=0 (never rotates) — should be 10485760 (10MB)
  BUG6: backupCount not set — should be 5
"""
import logging
import logging.handlers
import os


def setup_logging() -> None:
    """Configure application logging."""
    log_dir = os.path.dirname("{log_file}")
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # BUG1: Should be INFO, not DEBUG
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # BUG2: Missing module-level override — {auth_module} logger should be WARNING
    # (no override set here)

    # BUG3: Missing structured fields — format must include timestamp, level, module, message as JSON
    # BUG4: datefmt must be ISO-8601 (%Y-%m-%dT%H:%M:%S), not 12-hour US format
    formatter = logging.Formatter("%(message)s")
    formatter.datefmt = "%m/%d/%Y %I:%M %p"   # BUG4: wrong format

    # BUG5: maxBytes=0 means never rotates
    # BUG6: backupCount not specified
    file_handler = logging.handlers.RotatingFileHandler(
        "{log_file}",
        maxBytes=0,          # BUG5: should be 10485760
                             # BUG6: backupCount missing (should be 5)
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
'''

    def _buggy_app(self, auth_module: str, pii_email: str, pii_name: str) -> str:
        return f'''\
"""Main application entry point.

Bugs to fix:
  BUG7: process_user() logs raw email — must mask it (first char + ***@domain)
  BUG8: authenticate() logs password_hash — must remove that line entirely
"""
import logging
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("{auth_module}")


def process_user(email: str, name: str) -> None:
    """Process a user request."""
    # BUG7: logs raw email — should mask: email[0] + "***@" + email.split("@")[1]
    logger.info(f"Processing user {{email}}")
    logger.info(f"User {{name}} request started")
    logger.info("User processing complete")


def authenticate(username: str, password_hash: str) -> bool:
    """Authenticate a user."""
    # BUG8: must not log password_hash — remove this line entirely
    auth_logger.info(
        f"Auth attempt for {{username}} with password_hash={{password_hash}}"
    )
    auth_logger.info(f"Auth successful for {{username}}")
    return True


def main() -> None:
    process_user("{pii_email}", "{pii_name}")
    authenticate("admin", "5f4dcc3b5aa765d61d8327deb882cf99")
    logger.info("Application finished")


if __name__ == "__main__":
    main()
'''

    def _test_logging(self, auth_module: str, log_file: str, masked_email: str) -> str:
        return f'''\
"""Tests for logging configuration correctness."""
import json
import logging
import logging.handlers
import os
import re
import sys


def _reload_modules():
    """Reload logging config and app after edits."""
    import importlib
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("logging_config", "app"):
            del sys.modules[mod_name]
    # Reset root logger handlers
    root = logging.getLogger()
    root.handlers.clear()


def test_root_level_is_info():
    _reload_modules()
    import logging_config
    logging_config.setup_logging()
    assert logging.getLogger().level == logging.INFO, (
        f"Root logger level should be INFO, got {{logging.getLevelName(logging.getLogger().level)}}"
    )


def test_auth_module_level_is_warning():
    _reload_modules()
    import logging_config
    logging_config.setup_logging()
    auth_log = logging.getLogger("{auth_module}")
    assert auth_log.level == logging.WARNING, (
        f"'{auth_module}' logger should be WARNING, got {{logging.getLevelName(auth_log.level)}}"
    )


def test_rotating_handler_configured():
    _reload_modules()
    import logging_config
    logging_config.setup_logging()
    root = logging.getLogger()
    rotating = [h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
    assert len(rotating) >= 1, "No RotatingFileHandler configured"
    h = rotating[0]
    assert h.maxBytes == 10485760, f"maxBytes should be 10485760, got {{h.maxBytes}}"
    assert h.backupCount == 5, f"backupCount should be 5, got {{h.backupCount}}"


def test_email_masking_in_process_user():
    """process_user must not log the raw email."""
    import io
    _reload_modules()
    import logging_config
    logging_config.setup_logging()

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logging.getLogger().addHandler(handler)

    import app
    app.process_user("testuser@example.com", "Test User")

    output = stream.getvalue()
    assert "testuser@example.com" not in output, (
        "Raw email must not appear in logs — apply masking"
    )
    # Masked form should appear
    assert "t***@example.com" in output or "***" in output, (
        "Masked email must appear in logs"
    )


def test_password_not_logged():
    """authenticate must not log password_hash."""
    import io
    _reload_modules()
    import logging_config
    logging_config.setup_logging()

    stream = io.StringIO()
    logging.getLogger().addHandler(logging.StreamHandler(stream))

    import app
    app.authenticate("admin", "secret_hash_value")

    output = stream.getvalue()
    assert "secret_hash_value" not in output, (
        "password_hash must not appear in logs"
    )
    assert "password_hash" not in output, (
        "The string 'password_hash' must not appear in auth log output"
    )


if __name__ == "__main__":
    test_root_level_is_info()
    test_auth_module_level_is_warning()
    test_rotating_handler_configured()
    test_email_masking_in_process_user()
    test_password_not_logged()
    print("All tests passed.")
'''

    def _spec(self, auth_module: str, log_file: str) -> str:
        return f"""\
# O9: Logging Configuration Fix

## Goal
Fix logging misconfiguration in a Python application. The app has 4 categories
of logging problems that need to be resolved (8 total issues).

## Hard Requirements

### Log Level Issues
1. **Wrong root log level**: The root logger is set to `DEBUG` in production config. Set it to `INFO`.
2. **Missing module-level override**: The `{auth_module}` module should log at `WARNING` level (security events only) but inherits root level.

### Structured Logging
3. **Missing structured fields**: Log entries must include `timestamp`, `level`, `module`, and `message` as JSON fields. Currently only `message` is present.
4. **Wrong timestamp format**: Timestamps must be ISO-8601 format (`%Y-%m-%dT%H:%M:%S`). Currently using `%m/%d/%Y %I:%M %p`.

### Log Rotation
5. **Rotation broken**: `RotatingFileHandler` has `maxBytes=0` (never rotates). Set to `maxBytes=10485760` (10MB).
6. **Missing backup count**: `backupCount` is not set. Set to `5`.

### PII Protection
7. **Email in logs**: The `process_user` function logs `f"Processing user {{email}}"`. Mask the email: show only first char + `***@domain`.
8. **Password in logs**: The `authenticate` function logs the password hash. Remove that log line entirely.

## Config
- Config file: `logging_config.py`
- App file: `app.py`
- Log output: `{log_file}`
- Run: `python app.py`

## Deliverables
- Fixed `logging_config.py`
- Fixed `app.py` (PII masking)
- Verifier confirms all 8 issues resolved.
"""

    def _brief(self, auth_module: str) -> str:
        return f"""\
# O9: Logging Configuration Fix (Brief)

Fix `logging_config.py` and `app.py`. There are 8 logging issues:
2 log levels, 2 structured-logging problems, 2 rotation settings, 2 PII leaks.
Run: `python app.py`
Test: `pytest tests/test_logging.py`
"""
