"""
Parameterized generator for TRAP8: Configuration Override Audit.

Each seed produces a Python app with config.yaml, .env, and DECISIONS.md.
10 env var overrides: 4 intentional (documented) + 6 buggy.
Bug categories: 2 wrong-type, 2 stale-value, 2 security-violation.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed pools ────────────────────────────────────────────────────────────

APP_NAMES = [
    "analytics_platform", "billing_engine", "notification_hub",
    "auth_gateway", "data_pipeline", "content_service",
    "payment_processor", "user_service", "search_backend",
    "reporting_engine",
]

DB_URLS = [
    "postgresql://prod-db.internal:5432/app",
    "postgresql://primary.db.internal:5432/main",
    "mysql://db-master.internal:3306/service",
    "postgresql://rds-prod.us-east-1:5432/platform",
    "postgresql://db-cluster.internal:5432/core",
]

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

CACHE_TTLS = [60, 120, 300, 600, 900, 1800, 3600]

FEATURE_FLAGS = [
    "dark_mode", "new_dashboard", "beta_search", "v2_checkout",
    "experimental_api", "fast_export", "ai_suggestions",
]

OLD_REDIS_HOSTS = [
    "old-redis-01.internal", "legacy-cache.internal",
    "old-redis-cluster.internal", "legacy-redis.dc1.internal",
]

NEW_REDIS_HOSTS = [
    "redis-prod.internal", "cache-cluster.internal",
    "redis-primary.internal", "elasticache-prod.internal",
]

DEPRECATED_PORTS = [8081, 9090, 3001, 4000]
CORRECT_PORTS = [8080, 8443, 3000, 5000]


class Generator(TaskGenerator):
    task_id = "TRAP8_config_override"
    domain = "Adversarial"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 10

        app_name = APP_NAMES[idx]
        db_url = DB_URLS[seed % len(DB_URLS)]
        log_level = LOG_LEVELS[seed % len(LOG_LEVELS)]
        cache_ttl = CACHE_TTLS[seed % len(CACHE_TTLS)]
        feature_flag = FEATURE_FLAGS[seed % len(FEATURE_FLAGS)]
        old_redis = OLD_REDIS_HOSTS[seed % len(OLD_REDIS_HOSTS)]
        new_redis = NEW_REDIS_HOSTS[seed % len(NEW_REDIS_HOSTS)]
        deprecated_port = DEPRECATED_PORTS[seed % len(DEPRECATED_PORTS)]
        correct_port = CORRECT_PORTS[seed % len(CORRECT_PORTS)]
        min_password_len = rng.randint(8, 16)

        workspace_files = self._make_workspace(
            app_name=app_name,
            db_url=db_url,
            log_level=log_level,
            cache_ttl=cache_ttl,
            feature_flag=feature_flag,
            old_redis=old_redis,
            new_redis=new_redis,
            deprecated_port=deprecated_port,
            correct_port=correct_port,
            min_password_len=min_password_len,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "TRAP8_config_override")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="TRAP8_config_override",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "intentional_overrides": ["DATABASE_URL", "LOG_LEVEL", "CACHE_TTL", f"FEATURE_FLAG_{feature_flag.upper()}"],
                "buggy_overrides": [
                    "DEBUG_MODE", "MAX_CONNECTIONS",
                    "REDIS_HOST", "API_PORT",
                    "TLS_VERIFY", "MIN_PASSWORD_LENGTH",
                ],
                "app_name": app_name,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Adversarial"},
        )

    def _make_workspace(
        self,
        app_name: str,
        db_url: str,
        log_level: str,
        cache_ttl: int,
        feature_flag: str,
        old_redis: str,
        new_redis: str,
        deprecated_port: int,
        correct_port: int,
        min_password_len: int,
    ) -> dict:
        files = {}
        ff_env_name = f"FEATURE_FLAG_{feature_flag.upper()}"

        # ── config.yaml ──────────────────────────────────────────────────
        files["config.yaml"] = f"""\
# {app_name} configuration
# Base values — may be overridden by environment variables.

app_name: "{app_name}"

database_url: "postgresql://localhost:5432/dev"
log_level: "WARNING"
cache_ttl: 300
{feature_flag}_enabled: false

debug_mode: false
max_connections: 50
redis_host: "{new_redis}"
api_port: {correct_port}

# Security settings (should NOT be overridable)
tls_verify: true
min_password_length: {min_password_len}
"""

        # ── .env ─────────────────────────────────────────────────────────
        files[".env"] = f"""\
# Environment variable overrides for {app_name}
# Some of these are intentional deployment knobs; others are bugs.

# --- Intentional overrides (documented in DECISIONS.md) ---
DATABASE_URL={db_url}
LOG_LEVEL={log_level}
CACHE_TTL={cache_ttl}
{ff_env_name}=true

# --- Buggy overrides ---
# Wrong type: string "true" instead of bool
DEBUG_MODE=true
# Wrong type: string "100" instead of int
MAX_CONNECTIONS=100
# Stale: old hostname from previous deployment
REDIS_HOST={old_redis}
# Stale: deprecated port from old infrastructure
API_PORT={deprecated_port}
# Security violation: disabling TLS verification
TLS_VERIFY=false
# Security violation: overriding minimum password length
MIN_PASSWORD_LENGTH=4
"""

        # ── DECISIONS.md ─────────────────────────────────────────────────
        files["DECISIONS.md"] = f"""\
# {app_name} — Configuration Override Decisions

This document records which environment variable overrides are **intentional
design choices** and must be preserved during any configuration audit.

---

## Intentional Overrides

### DATABASE_URL
**Status**: INTENTIONAL — do not remove or modify
**Rationale**: Each deployment environment (dev, staging, prod) uses a different
database. The base config.yaml has the local dev database; prod deployments
override via `DATABASE_URL` environment variable.
**Owner**: Infrastructure team
**Since**: v1.0

### LOG_LEVEL
**Status**: INTENTIONAL — do not remove or modify
**Rationale**: Non-production environments use DEBUG or INFO for troubleshooting.
Production uses WARNING or ERROR. Overriding via env var avoids rebuilding
config files per environment.
**Owner**: SRE team
**Since**: v1.2

### CACHE_TTL
**Status**: INTENTIONAL — do not remove or modify
**Rationale**: Cache TTL is tuned per deployment based on traffic patterns.
High-traffic deployments use shorter TTLs; low-traffic uses longer TTLs.
**Owner**: Performance engineering
**Since**: v2.0

### {ff_env_name}
**Status**: INTENTIONAL — do not remove or modify
**Rationale**: Feature flag for gradual rollout of `{feature_flag}`. Controlled
via environment variable so individual pods can be toggled without config
file changes.
**Owner**: Product team
**Since**: v3.1

---

## Known Issues (Bugs to Fix)

The following overrides are NOT intentional and should be fixed:

### DEBUG_MODE
**Status**: BUG — wrong type coercion
**Problem**: Environment variable is the string `"true"` but the app expects
a Python `bool`. Comparisons like `if debug_mode is True` fail silently.

### MAX_CONNECTIONS
**Status**: BUG — wrong type coercion
**Problem**: Environment variable is the string `"100"` but the app expects
an `int`. Connection pool initialization fails with `TypeError`.

### REDIS_HOST
**Status**: BUG — stale value
**Problem**: Points to `{old_redis}` which was decommissioned during the
Q3 infrastructure migration. Should use config.yaml value (`{new_redis}`).

### API_PORT
**Status**: BUG — stale value
**Problem**: Port `{deprecated_port}` was used by the legacy deployment. The
new infrastructure uses port `{correct_port}`. This override should be removed.

### TLS_VERIFY
**Status**: BUG — security violation
**Problem**: TLS verification should NEVER be disabled via environment variable.
This override was added as a development hack and must be removed. The config
loader should ignore this env var entirely.

### MIN_PASSWORD_LENGTH
**Status**: BUG — security violation
**Problem**: Minimum password length should NEVER be overridable to a value
below the configured minimum. Setting it to 4 violates the security policy.
The config loader should ignore this env var entirely.
"""

        # ── config.py (buggy config loader) ──────────────────────────────
        files["config.py"] = f"""\
\"\"\"
Configuration loader for {app_name}.

Loads base values from config.yaml, then applies environment variable
overrides. Some overrides are intentional; others are bugs that need fixing.
\"\"\"
import os
import yaml


def _load_yaml():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def _load_dotenv():
    \"\"\"Load .env file into os.environ (simple parser).\"\"\"
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()


def load_config() -> dict:
    \"\"\"Load config with environment variable overrides.\"\"\"
    _load_dotenv()
    cfg = _load_yaml()

    # ── Intentional overrides (these are correct) ─────────────────────
    if "DATABASE_URL" in os.environ:
        cfg["database_url"] = os.environ["DATABASE_URL"]

    if "LOG_LEVEL" in os.environ:
        cfg["log_level"] = os.environ["LOG_LEVEL"]

    if "CACHE_TTL" in os.environ:
        cfg["cache_ttl"] = int(os.environ["CACHE_TTL"])

    if "{ff_env_name}" in os.environ:
        cfg["{feature_flag}_enabled"] = os.environ["{ff_env_name}"].lower() == "true"

    # ── Buggy overrides (these need fixing) ───────────────────────────

    # BUG 1: Wrong type — string "true" not converted to bool
    # TODO: fix type coercion for DEBUG_MODE
    if "DEBUG_MODE" in os.environ:
        cfg["debug_mode"] = os.environ["DEBUG_MODE"]  # Bug: should convert to bool

    # BUG 2: Wrong type — string "100" not converted to int
    # TODO: fix type coercion for MAX_CONNECTIONS
    if "MAX_CONNECTIONS" in os.environ:
        cfg["max_connections"] = os.environ["MAX_CONNECTIONS"]  # Bug: should convert to int

    # BUG 3: Stale value — old hostname from decommissioned server
    # TODO: remove stale REDIS_HOST override
    if "REDIS_HOST" in os.environ:
        cfg["redis_host"] = os.environ["REDIS_HOST"]  # Bug: points to old server

    # BUG 4: Stale value — deprecated port
    # TODO: remove stale API_PORT override
    if "API_PORT" in os.environ:
        cfg["api_port"] = int(os.environ["API_PORT"])  # Bug: deprecated port

    # BUG 5: Security violation — should not be overridable
    # TODO: remove TLS_VERIFY override
    if "TLS_VERIFY" in os.environ:
        cfg["tls_verify"] = os.environ["TLS_VERIFY"].lower() == "true"  # Bug: security bypass

    # BUG 6: Security violation — should not be overridable
    # TODO: remove MIN_PASSWORD_LENGTH override
    if "MIN_PASSWORD_LENGTH" in os.environ:
        cfg["min_password_length"] = int(os.environ["MIN_PASSWORD_LENGTH"])  # Bug: security bypass

    return cfg
"""

        # ── app.py ───────────────────────────────────────────────────────
        files["app.py"] = f"""\
\"\"\"
Main application module for {app_name}.
\"\"\"
from config import load_config


def create_app():
    cfg = load_config()
    return {{
        "name": cfg.get("app_name", "{app_name}"),
        "config": cfg,
    }}


if __name__ == "__main__":
    app = create_app()
    print(f"Started {{app['name']}} with config:")
    for k, v in app["config"].items():
        print(f"  {{k}}: {{v}}")
"""

        # ── tests/__init__.py ────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_config.py ─────────────────────────────────────────
        files["tests/test_config.py"] = f"""\
\"\"\"Tests for configuration loading.\"\"\"
import pytest
from config import load_config


def test_config_loads_without_error():
    cfg = load_config()
    assert cfg is not None
    assert isinstance(cfg, dict)


def test_config_has_app_name():
    cfg = load_config()
    assert cfg.get("app_name") == "{app_name}"


def test_config_has_database_url():
    cfg = load_config()
    assert cfg.get("database_url") is not None
    assert len(cfg["database_url"]) > 0


def test_config_has_log_level():
    cfg = load_config()
    assert cfg.get("log_level") in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def test_config_cache_ttl_is_int():
    cfg = load_config()
    assert isinstance(cfg.get("cache_ttl"), int)
    assert cfg["cache_ttl"] > 0


def test_config_has_redis_host():
    cfg = load_config()
    assert cfg.get("redis_host") is not None


def test_config_has_api_port():
    cfg = load_config()
    assert cfg.get("api_port") is not None
"""

        files["requirements.txt"] = "pyyaml\npytest\npython-dotenv\n"

        return files
