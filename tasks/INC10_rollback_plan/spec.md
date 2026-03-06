# INC10: Rollback Plan — Ordered Dependencies

## Incident Summary

**Incident ID**: INC-ROLLBACK-001
**Severity**: P1
**Root Cause**: memory leak introduced in new connection pool implementation

All three services were deployed together at version `2.4.0`. The deployment
introduced a regression that is causing cascading failures. Immediate rollback required.

---

## Service Dependency Graph

```
api_gateway (entry-point)
  └── depends on: user_service
        └── depends on: auth_service (leaf / data layer)
```

**Dependency rule**: `api_gateway` calls `user_service` for all business logic.
`user_service` calls `auth_service` for persistence and state management.

---

## Critical Rollback Ordering Constraint

**MUST rollback in leaf-first order** to prevent data corruption:

1. **Step 1: Rollback `auth_service` first** (leaf / data layer)
   - Target version: `2.3.1`
   - Reason: rolling back the data layer first ensures the schema is compatible
     before business logic services reconnect.

2. **Step 2: Rollback `user_service` second** (business logic)
   - Target version: `2.3.3`
   - Reason: `user_service` must use the old API only after `auth_service` is stable.

3. **Step 3: Rollback `api_gateway` last** (entry-point)
   - Target version: `2.3.5`
   - Reason: `api_gateway` is the traffic entry-point; rolling it back last minimises
     window where users see inconsistent responses.

**WARNING**: Rolling back `api_gateway` before `auth_service` will cause `api_gateway` to
send requests to an incompatible `auth_service` version, causing data corruption.

---

## Required Output: rollback_plan.json

Produce `rollback_plan.json` with this schema:

```json
{
  "incident_id": "INC-ROLLBACK-001",
  "pre_rollback_snapshot": {
    "timestamp": "<ISO8601>",
    "services": {
      "api_gateway": "2.4.0",
      "user_service": "2.4.0",
      "auth_service": "2.4.0"
    }
  },
  "steps": [
    {
      "order": 1,
      "service": "auth_service",
      "action": "rollback",
      "from_version": "2.4.0",
      "to_version": "2.3.1",
      "health_check": "http://127.0.0.1:8082/health",
      "wait_for_healthy": true
    },
    {
      "order": 2,
      "service": "user_service",
      "action": "rollback",
      "from_version": "2.4.0",
      "to_version": "2.3.3",
      "health_check": "http://127.0.0.1:8081/health",
      "wait_for_healthy": true
    },
    {
      "order": 3,
      "service": "api_gateway",
      "action": "rollback",
      "from_version": "2.4.0",
      "to_version": "2.3.5",
      "health_check": "http://127.0.0.1:8080/health",
      "wait_for_healthy": true
    }
  ],
  "post_rollback_verification": {
    "check_all_healthy": true,
    "verify_versions": true,
    "run_smoke_tests": true
  }
}
```

---

## Constraints

- Plan must list all 3 services; omitting any service is a grader failure.
- Steps must be ordered leaf-first (`auth_service` → `user_service` → `api_gateway`).
- Each step must include `health_check` URL and `wait_for_healthy: true`.
- `pre_rollback_snapshot` and `post_rollback_verification` are required.
- Target versions must exactly match: `api_gateway`→`2.3.5`, `user_service`→`2.3.3`, `auth_service`→`2.3.1`.
- Verifier must produce `attestation.json` with `verdict="pass"`.
