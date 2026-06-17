"""
Configuration system for the web service application.

Implements typed config keys with validation, type coercion, and a 4-source
priority cascade: CLI arguments > environment variables > config file > defaults.
"""
import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ConfigValidationError(ValueError):
    """Raised when a configuration value fails type coercion or validation."""


# ---------------------------------------------------------------------------
# Schema — single source of truth for all 10 config keys
# ---------------------------------------------------------------------------

_SCHEMA: dict[str, dict] = {
    "host": {
        "type": "string",
        "default": "0.0.0.0",
        "env_var": "WEB_HOST",
        "validation": {"non_empty": True},
    },
    "port": {
        "type": "int",
        "default": 6155,
        "env_var": "WEB_PORT",
        "validation": {"min": 2048, "max": 49151},
    },
    "log_level": {
        "type": "enum",
        "default": "WARN",
        "env_var": "WEB_LOG_LEVEL",
        "validation": {"allowed": ["INFO", "WARN", "ERROR"]},
    },
    "request_timeout": {
        "type": "int",
        "default": 120,
        "env_var": "WEB_REQUEST_TIMEOUT",
        "validation": {"min": 1, "max": 3600},
    },
    "max_connections": {
        "type": "int",
        "default": 348,
        "env_var": "WEB_MAX_CONNECTIONS",
        "validation": {"min": 1, "max": 1000},
    },
    "debug_mode": {
        "type": "bool",
        "default": False,
        "env_var": "WEB_DEBUG",
        "validation": {},
    },
    "static_dir": {
        "type": "string",
        "default": "./static",
        "env_var": "WEB_STATIC_DIR",
        "validation": {"non_empty": True},
    },
    "cors_origins": {
        "type": "string",
        "default": "*",
        "env_var": "WEB_CORS_ORIGINS",
        "validation": {},
    },
    "keep_alive_timeout": {
        "type": "int",
        "default": 10,
        "env_var": "WEB_KEEP_ALIVE_TIMEOUT",
        "validation": {"min": 1, "max": 300},
    },
    "ssl_enabled": {
        "type": "bool",
        "default": False,
        "env_var": "WEB_SSL_ENABLED",
        "validation": {},
    },
}


# ---------------------------------------------------------------------------
# Bool coercion lookup tables (case-insensitive)
# ---------------------------------------------------------------------------

_BOOL_TRUTHY = frozenset({"true", "1", "yes", "on"})
_BOOL_FALSY = frozenset({"false", "0", "no", "off"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_schema() -> dict:
    """Return the full config schema with all 10 keys.

    The returned dict maps each config key name to a specification dict
    containing ``type``, ``default``, ``env_var``, and ``validation``.
    """
    return _SCHEMA


def validate_value(key: str, value: Any) -> Any:
    """Coerce and validate a single value for *key*.

    Args:
        key: Config key name (must exist in ``_SCHEMA``).
        value: Raw value — may be a native Python type or a string from an
            environment variable / JSON config file.

    Returns:
        The coerced, validated value.

    Raises:
        ConfigValidationError: If the value cannot be coerced to the key's
            declared type or fails its validation rules.
    """
    if key not in _SCHEMA:
        raise ConfigValidationError(
            f"Unknown config key '{key}': {value!r}"
        )

    spec = _SCHEMA[key]
    target_type = spec["type"]
    validation = spec["validation"]

    # --- coercion ---
    coerced = _coerce_value(key, value, target_type)

    # --- validation ---
    _validate_coerced(key, coerced, target_type, validation)

    return coerced


def load_config(
    config_file: str | None = None,
    env_vars: dict | None = None,
    cli_args: dict | None = None,
) -> dict:
    """Load and validate configuration from all sources.

    Priority cascade (highest first): **cli_args > env_vars > config_file > defaults**

    Args:
        config_file: Path to a JSON config file, or ``None`` to skip the file
            source.
        env_vars: Dict of environment variables (keyed by env-var name).
            Defaults to ``os.environ`` when ``None``. An explicit empty dict
            means *no* environment variables are consulted.
        cli_args: Dict of CLI-supplied overrides keyed by config key name.
            ``None`` is treated as an empty dict.

    Returns:
        ``dict`` with all 10 config keys populated, coerced, and validated.

    Raises:
        FileNotFoundError: If *config_file* is specified but does not exist.
        ConfigValidationError: If any value fails coercion or validation.
    """
    # --- normalise inputs ---
    if env_vars is None:
        env_vars = os.environ
    if cli_args is None:
        cli_args = {}

    # --- 1. start with defaults (lowest priority) ---
    result: dict[str, Any] = {
        key: spec["default"] for key, spec in _SCHEMA.items()
    }

    # --- 2. overlay config file (priority 3) ---
    if config_file is not None:
        try:
            with open(config_file, "r", encoding="utf-8") as fh:
                file_data = json.load(fh)
        except FileNotFoundError:
            raise
        # Only extract known schema keys; silently ignore unknown keys.
        if isinstance(file_data, dict):
            for key in _SCHEMA:
                if key in file_data and file_data[key] is not None:
                    result[key] = file_data[key]

    # --- 3. overlay environment variables (priority 2) ---
    for key, spec in _SCHEMA.items():
        env_name = spec["env_var"]
        if env_name in env_vars and env_vars[env_name] is not None:
            result[key] = env_vars[env_name]

    # --- 4. overlay CLI args (priority 1, highest) ---
    for key in _SCHEMA:
        if key in cli_args and cli_args[key] is not None:
            result[key] = cli_args[key]

    # --- 5. coerce and validate every key ---
    for key in list(result.keys()):
        result[key] = validate_value(key, result[key])

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coerce_value(key: str, value: Any, target_type: str) -> Any:
    """Coerce *value* to *target_type*.

    Strings are coerced according to the type rules; native types that already
    match the target type pass through unchanged.
    """
    if target_type == "string":
        # No coercion needed — any string is accepted as-is.
        # (Native non-string values also pass through — validated later.)
        return value

    if target_type == "int":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                raise ConfigValidationError(
                    f"Invalid value for '{key}': {value!r} - "
                    f"cannot be parsed as an integer"
                )
        raise ConfigValidationError(
            f"Invalid value for '{key}': {value!r} - "
            f"expected an integer or integer-parseable string"
        )

    if target_type == "float":
        if isinstance(value, float):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise ConfigValidationError(
                    f"Invalid value for '{key}': {value!r} - "
                    f"cannot be parsed as a float"
                )
        raise ConfigValidationError(
            f"Invalid value for '{key}': {value!r} - "
            f"expected a float or float-parseable string"
        )

    if target_type == "bool":
        # Native Python bool — pass through.
        if isinstance(value, bool):
            return value
        # Integer 1 / 0 — coerce to bool (per analyst recommendation).
        if isinstance(value, int) and value in (1, 0):
            return bool(value)
        # String — apply 8-form coercion (case-insensitive).
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in _BOOL_TRUTHY:
                return True
            if lowered in _BOOL_FALSY:
                return False
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"not one of the 8 accepted bool forms "
                f"(true/false/1/0/yes/no/on/off, case-insensitive)"
            )
        raise ConfigValidationError(
            f"Invalid value for '{key}': {value!r} - "
            f"expected a bool, int 1/0, or a valid bool-form string"
        )

    if target_type == "enum":
        if not isinstance(value, str):
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"expected a string for enum type"
            )
        return value  # validation happens in _validate_coerced

    # Unknown type — should never happen with a valid schema.
    raise ConfigValidationError(
        f"Invalid schema type '{target_type}' for key '{key}'"
    )


def _validate_coerced(
    key: str,
    value: Any,
    target_type: str,
    validation: dict,
) -> None:
    """Validate a value that has already been coerced to *target_type*."""
    if target_type == "string":
        if validation.get("non_empty") and (not isinstance(value, str) or value == ""):
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"must be a non-empty string"
            )

    elif target_type == "int":
        min_val = validation.get("min")
        max_val = validation.get("max")
        if min_val is not None and value < min_val:
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"must be >= {min_val}"
            )
        if max_val is not None and value > max_val:
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"must be <= {max_val}"
            )

    elif target_type == "float":
        # No float keys defined in this seed, but infra exists.
        min_val = validation.get("min")
        max_val = validation.get("max")
        if min_val is not None and value < min_val:
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"must be >= {min_val}"
            )
        if max_val is not None and value > max_val:
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"must be <= {max_val}"
            )

    elif target_type == "bool":
        # Already coerced — no further validation needed.
        pass

    elif target_type == "enum":
        allowed = validation.get("allowed", [])
        if value not in allowed:
            raise ConfigValidationError(
                f"Invalid value for '{key}': {value!r} - "
                f"must be one of {allowed} (case-sensitive)"
            )
