# CROSS7: Configuration Drift Reconciliation

## Goal
Reconcile configuration files across 3 microservices that have drifted from a shared
canonical configuration. Each service has made independent changes that must be merged
according to specific override rules without breaking any service.

## Requirements
1. All 3 service configs must include every key from `canonical_config.yaml`.
2. Service-specific overrides documented in `overrides.md` must be preserved (not overwritten by canonical values).
3. Fields that were intentionally added by a service (documented in `overrides.md`) must remain.
4. Fields where a service changed the default (not documented as an override) must be reverted to the canonical value.
5. Deprecated fields that were removed by a service must remain removed (they should NOT be re-added from canonical).
6. Each service's `config.yaml` must be valid YAML after reconciliation.
7. The `reconcile.py` script must produce correct merged configs.
8. All tests in `tests/test_reconcile.py` must pass.

## Supporting Documents
- `canonical_config.yaml` — The shared source-of-truth configuration
- `auth_service/config.yaml` — Auth service config (drifted: 2 added fields, 1 changed default)
- `billing_service/config.yaml` — Billing service config (drifted: 3 changed defaults)
- `notification_service/config.yaml` — Notification service config (drifted: 2 removed deprecated fields, 1 changed default)
- `overrides.md` — Documents which deviations are intentional service-specific overrides
- `reconcile.py` — Reconciliation script (contains 4 bugs)
- `tests/test_reconcile.py` — Validation tests

## Background

### Configuration Drift in Microservices

When multiple services share a base configuration, they inevitably drift:
- Service A adds fields for new features
- Service B changes defaults for performance tuning
- Service C removes deprecated fields

Reconciliation must distinguish **intentional overrides** (keep) from
**unintentional drift** (revert to canonical). This requires cross-referencing
the override documentation.

### The 4 Bugs in reconcile.py

1. **Override detection**: The script checks if a key exists in overrides but doesn't check if the override applies to the CURRENT service. It preserves all overrides for all services.
2. **Added field handling**: When a service adds a field not in canonical, the script deletes it even if it's listed as a service-specific addition in overrides.md.
3. **Deprecated field re-addition**: The script re-adds deprecated fields from canonical to services that intentionally removed them (should skip fields listed as deprecated in overrides.md).
4. **Type coercion**: The script compares values with `==` but some configs have string `"true"` vs boolean `true` drift. It should normalize types before comparison.

## Hidden Complexity
- The overrides.md file uses a per-service section format. The script must parse
  which overrides apply to which service.
- Some "drifted" values are actually correct per overrides.md. Blindly reverting
  to canonical would break those services.
- Deprecated fields are listed in a separate section of overrides.md. The reconciler
  must know not to re-add them.
