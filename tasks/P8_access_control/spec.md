# P8: Access Control Policy Fix — Full Specification

## Overview

The RBAC policy in `rbac_policy.yaml` has been flagged by a compliance scan.
The `compliance_report.md` lists **6 findings** — but only **4 are real violations**.
The other **2 are intentional exceptions** documented in `exceptions.md`.

You must fix exactly the 4 real violations **without removing** the 2 approved exceptions.
Removing an exception breaks a legitimate operational requirement.

## Roles

`admin`, `developer`, `analyst`, `auditor`, `service_account`

## Resources

`user_data`, `billing_records`, `logs`, `config`, `api_keys`, `reports`, `deployments`, `secrets`, `backups`, `metrics`

## The 4 Real Violations (must be fixed)

| # | Role | Resource | Permission | Why It's Wrong |
|---|------|----------|-----------|----------------|
| 1 | `developer` | `billing_records` | `write` | Developers must not write billing records |
| 2 | `analyst` | `secrets` | `read` | Analysts must not read secrets |
| 3 | `analyst` | `config` | `write` | Analysts must not modify config |
| 4 | `service_account` | `user_data` | `delete` | Service accounts must not delete user data |

**Fix**: Remove the offending permission from that role's entry in `rbac_policy.yaml`.

## The 2 Intentional Exceptions (must be preserved)

| # | Role | Resource | Permission | Why It's Correct |
|---|------|----------|-----------|-----------------|
| 1 | `auditor` | `api_keys` | `read` | Auditors need read access to api_keys for compliance audit trails |
| 2 | `service_account` | `logs` | `write` | Service accounts write logs as part of their operational function |

These entries appear in `compliance_report.md` as findings, but `exceptions.md`
documents that they are **approved by the Security Committee** and must not be removed.

## Hidden Constraint

The compliance report intentionally lists all 6 findings without distinguishing violations
from exceptions. An agent that removes all 6 findings will break the 2 approved exceptions
and fail the test. You must cross-reference `exceptions.md` before removing any access.

## Validation

```bash
python3 validator.py        # structural check
python3 test_rbac.py        # full test suite
```

## Deliverable

Modified `rbac_policy.yaml` with:
- All 4 real violations removed
- Both approved exceptions preserved
- All role entries still present (no roles removed)
