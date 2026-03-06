# TRAP8: Configuration Override Audit

## Goal

A Python application loads configuration from `config.yaml` and then applies
environment variable overrides from a `.env` file. An audit has found that 10
environment variables override config values. Some of these overrides are
intentional design choices; others are bugs that must be fixed.

## Requirements

1. Read `DECISIONS.md` to understand which overrides are intentional
2. Fix the 6 buggy overrides in `config.py` (the override-loading logic)
3. Preserve the 4 intentional overrides exactly as they are
4. All tests must pass after changes: `pytest tests/`

## Buggy Overrides (6 total)

The 6 bugs fall into three categories:

- **Wrong type coercion** (2 bugs): Environment variables are strings, but the
  code uses them directly without converting to the correct type (e.g., `"true"`
  string instead of `bool True`, `"3600"` string instead of `int 3600`)
- **Stale values** (2 bugs): Overrides reference old deployment values that no
  longer match the current infrastructure (e.g., old hostnames, deprecated ports)
- **Security violations** (2 bugs): Overrides that bypass security settings
  which should never be overridable from environment variables (e.g., disabling
  TLS verification, overriding minimum password length)

## Intentional Overrides (4 total — DO NOT modify)

`DECISIONS.md` documents exactly which overrides are intentional and why. These
are legitimate deployment-time configuration knobs:

- **DATABASE_URL**: overridden per environment (dev/staging/prod)
- **LOG_LEVEL**: overridden for debugging in non-production environments
- **CACHE_TTL**: overridden for performance tuning per deployment
- **FEATURE_FLAG_X**: overridden for gradual rollout control

## Supporting Documents

- `config.yaml` — base configuration values
- `.env` — environment variable overrides (all 10)
- `DECISIONS.md` — documents intentional overrides with rationale
- `config.py` — configuration loader (where bugs must be fixed)
- `tests/test_config.py` — configuration tests (must all pass)

## Key Insight

The spec says to audit ALL overrides, but `DECISIONS.md` is authoritative.
When an override is documented as intentional in `DECISIONS.md`, it must be
preserved. Only the 6 undocumented or flagged-as-buggy overrides should be fixed.
