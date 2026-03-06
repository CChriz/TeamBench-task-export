"""
Parameterized generator for INC10: Rollback Plan (Ordered Dependencies).

Each seed produces:
  - Different service names (3 services with deployment failures)
  - Different dependency graph (service A depends on B, B depends on C)
  - Different rollback procedures per service
  - deployment_log.json, service_deps.yaml, rollback_procedures.md, health_endpoints.json
  - Agent must produce rollback_plan.json with correct ordering and health checks

TNI driver: The spec tells the Planner the exact dependency graph and that rollbacks
must proceed leaf-first (reverse dependency order). The brief only says "3 services
failed — create a rollback plan". Without the Planner the Executor may roll back
in deployment order (wrong) or skip health checks between steps.

Grader checks (8):
  1. rollback_plan.json exists
  2. All 3 services are present in the plan
  3. Rollback order respects dependency graph (leaf first)
  4. Each step includes a health_check field
  5. Health check URLs match the expected endpoints
  6. No circular dependencies in the plan
  7. Pre-rollback snapshot step is present
  8. Post-rollback verification step is present
  9. Correct target versions specified for each service
  10. Plan is valid JSON with required schema fields
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Pools ────────────────────────────────────────────────────────────────────

SERVICE_TRIPLETS = [
    ("api_gateway", "user_service", "auth_service"),
    ("frontend", "order_service", "inventory_service"),
    ("load_balancer", "payment_service", "ledger_service"),
    ("edge_router", "catalog_service", "search_service"),
    ("web_server", "session_service", "cache_service"),
    ("ingress", "notification_service", "template_service"),
    ("proxy", "billing_service", "subscription_service"),
    ("gateway", "analytics_service", "metrics_service"),
    ("router", "recommendation_service", "feature_service"),
    ("dispatcher", "workflow_service", "queue_service"),
]

# (major, minor, patch) for "current broken" version
BROKEN_VERSIONS = [
    ("2", "4", "0"),
    ("3", "1", "0"),
    ("1", "8", "0"),
    ("4", "0", "0"),
    ("2", "2", "0"),
    ("5", "3", "0"),
    ("1", "5", "0"),
    ("3", "3", "0"),
    ("2", "6", "0"),
    ("4", "2", "0"),
]

ROLLBACK_REASONS = [
    "memory leak introduced in new connection pool implementation",
    "database migration script applied incorrect schema changes",
    "configuration change broke JWT token validation",
    "new caching layer introduced race condition under load",
    "updated dependency caused incompatible serialization format",
    "feature flag misconfiguration disabled critical auth checks",
    "new rate limiter implementation caused cascading timeouts",
    "refactored retry logic introduced exponential backoff storm",
    "updated TLS certificate path caused connection failures",
    "new logging middleware caused excessive disk I/O under load",
]

PORT_TRIPLETS = [
    (8080, 8081, 8082),
    (9000, 9001, 9002),
    (7000, 7001, 7002),
    (5000, 5001, 5002),
    (3000, 3001, 3002),
    (8800, 8801, 8802),
    (9900, 9901, 9902),
    (6060, 6061, 6062),
    (4040, 4041, 4042),
    (8100, 8101, 8102),
]


class Generator(TaskGenerator):
    task_id = "INC10_rollback_plan"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        svc_a, svc_b, svc_c = SERVICE_TRIPLETS[seed % len(SERVICE_TRIPLETS)]
        port_a, port_b, port_c = PORT_TRIPLETS[(seed * 3 + 1) % len(PORT_TRIPLETS)]
        broken_major, broken_minor, broken_patch = BROKEN_VERSIONS[(seed * 7 + 2) % len(BROKEN_VERSIONS)]
        reason = ROLLBACK_REASONS[(seed * 5 + 3) % len(ROLLBACK_REASONS)]

        # Stable (rollback target) versions are one minor behind
        stable_minor = str(int(broken_minor) - 1) if int(broken_minor) > 0 else "0"
        broken_ver = f"{broken_major}.{broken_minor}.{broken_patch}"
        stable_ver_a = f"{broken_major}.{stable_minor}.5"
        stable_ver_b = f"{broken_major}.{stable_minor}.3"
        stable_ver_c = f"{broken_major}.{stable_minor}.1"

        # Correct rollback order: leaf first (C -> B -> A)
        correct_order = [svc_c, svc_b, svc_a]

        expected = {
            "svc_a": svc_a,
            "svc_b": svc_b,
            "svc_c": svc_c,
            "port_a": port_a,
            "port_b": port_b,
            "port_c": port_c,
            "broken_version": broken_ver,
            "stable_ver_a": stable_ver_a,
            "stable_ver_b": stable_ver_b,
            "stable_ver_c": stable_ver_c,
            "correct_rollback_order": correct_order,
            "rollback_reason": reason,
            "health_url_a": f"http://127.0.0.1:{port_a}/health",
            "health_url_b": f"http://127.0.0.1:{port_b}/health",
            "health_url_c": f"http://127.0.0.1:{port_c}/health",
        }

        workspace_files = {
            "deployment_log.json": _deployment_log(svc_a, svc_b, svc_c, broken_ver, reason),
            "service_deps.yaml": _service_deps(svc_a, svc_b, svc_c, port_a, port_b, port_c),
            "rollback_procedures.md": _rollback_procedures(svc_a, svc_b, svc_c, broken_ver, stable_ver_a, stable_ver_b, stable_ver_c),
            "health_endpoints.json": _health_endpoints(svc_a, svc_b, svc_c, port_a, port_b, port_c),
            "incident_summary.md": _incident_summary(svc_a, svc_b, svc_c, broken_ver, reason),
            "current_state.json": _current_state(svc_a, svc_b, svc_c, broken_ver, port_a, port_b, port_c),
            "change_history.log": _change_history(svc_a, svc_b, svc_c, broken_ver, stable_ver_a, reason),
            "runbook.md": _runbook(svc_a, svc_b, svc_c),
        }

        spec_md = self._generate_spec(svc_a, svc_b, svc_c, port_a, port_b, port_c,
                                       broken_ver, stable_ver_a, stable_ver_b, stable_ver_c,
                                       reason, correct_order)
        brief_md = self._generate_brief(svc_a, svc_b, svc_c)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_spec(self, svc_a, svc_b, svc_c, port_a, port_b, port_c,
                       broken_ver, stable_ver_a, stable_ver_b, stable_ver_c,
                       reason, correct_order):
        return f"""# INC10: Rollback Plan — Ordered Dependencies

## Incident Summary

**Incident ID**: INC-ROLLBACK-001
**Severity**: P1
**Root Cause**: {reason}

All three services were deployed together at version `{broken_ver}`. The deployment
introduced a regression that is causing cascading failures. Immediate rollback required.

---

## Service Dependency Graph

```
{svc_a} (entry-point)
  └── depends on: {svc_b}
        └── depends on: {svc_c} (leaf / data layer)
```

**Dependency rule**: `{svc_a}` calls `{svc_b}` for all business logic.
`{svc_b}` calls `{svc_c}` for persistence and state management.

---

## Critical Rollback Ordering Constraint

**MUST rollback in leaf-first order** to prevent data corruption:

1. **Step 1: Rollback `{svc_c}` first** (leaf / data layer)
   - Target version: `{stable_ver_c}`
   - Reason: rolling back the data layer first ensures the schema is compatible
     before business logic services reconnect.

2. **Step 2: Rollback `{svc_b}` second** (business logic)
   - Target version: `{stable_ver_b}`
   - Reason: `{svc_b}` must use the old API only after `{svc_c}` is stable.

3. **Step 3: Rollback `{svc_a}` last** (entry-point)
   - Target version: `{stable_ver_a}`
   - Reason: `{svc_a}` is the traffic entry-point; rolling it back last minimises
     window where users see inconsistent responses.

**WARNING**: Rolling back `{svc_a}` before `{svc_c}` will cause `{svc_a}` to
send requests to an incompatible `{svc_c}` version, causing data corruption.

---

## Required Output: rollback_plan.json

Produce `rollback_plan.json` with this schema:

```json
{{
  "incident_id": "INC-ROLLBACK-001",
  "pre_rollback_snapshot": {{
    "timestamp": "<ISO8601>",
    "services": {{
      "{svc_a}": "{broken_ver}",
      "{svc_b}": "{broken_ver}",
      "{svc_c}": "{broken_ver}"
    }}
  }},
  "steps": [
    {{
      "order": 1,
      "service": "{svc_c}",
      "action": "rollback",
      "from_version": "{broken_ver}",
      "to_version": "{stable_ver_c}",
      "health_check": "http://127.0.0.1:{port_c}/health",
      "wait_for_healthy": true
    }},
    {{
      "order": 2,
      "service": "{svc_b}",
      "action": "rollback",
      "from_version": "{broken_ver}",
      "to_version": "{stable_ver_b}",
      "health_check": "http://127.0.0.1:{port_b}/health",
      "wait_for_healthy": true
    }},
    {{
      "order": 3,
      "service": "{svc_a}",
      "action": "rollback",
      "from_version": "{broken_ver}",
      "to_version": "{stable_ver_a}",
      "health_check": "http://127.0.0.1:{port_a}/health",
      "wait_for_healthy": true
    }}
  ],
  "post_rollback_verification": {{
    "check_all_healthy": true,
    "verify_versions": true,
    "run_smoke_tests": true
  }}
}}
```

---

## Constraints

- Plan must list all 3 services; omitting any service is a grader failure.
- Steps must be ordered leaf-first (`{svc_c}` → `{svc_b}` → `{svc_a}`).
- Each step must include `health_check` URL and `wait_for_healthy: true`.
- `pre_rollback_snapshot` and `post_rollback_verification` are required.
- Target versions must exactly match: `{svc_a}`→`{stable_ver_a}`, `{svc_b}`→`{stable_ver_b}`, `{svc_c}`→`{stable_ver_c}`.
- Verifier must produce `attestation.json` with `verdict="pass"`.
"""

    def _generate_brief(self, svc_a, svc_b, svc_c):
        return f"""# INC10: Rollback Plan (Brief)

Three services failed after a coordinated deployment:
- `{svc_a}` — entry-point service
- `{svc_b}` — business logic service
- `{svc_c}` — data layer service

Review `deployment_log.json`, `service_deps.yaml`, and `rollback_procedures.md`
to understand what happened and how to roll back.

**Goal**: Produce `rollback_plan.json` that describes the rollback steps in the
correct order, includes health checks between steps, and captures both a
pre-rollback snapshot and a post-rollback verification step.

The Planner has the full incident report including dependency graph and required
rollback ordering. Coordinate with the Planner before writing the plan.
"""


# ── Workspace file generators ────────────────────────────────────────────────

def _deployment_log(svc_a, svc_b, svc_c, broken_ver, reason):
    return json.dumps({
        "deployment_id": "deploy-20240615-001",
        "timestamp": "2024-06-15T14:30:00Z",
        "services_deployed": [
            {"service": svc_c, "version": broken_ver, "deployed_at": "2024-06-15T14:30:05Z", "status": "unhealthy"},
            {"service": svc_b, "version": broken_ver, "deployed_at": "2024-06-15T14:31:10Z", "status": "unhealthy"},
            {"service": svc_a, "version": broken_ver, "deployed_at": "2024-06-15T14:32:15Z", "status": "unhealthy"},
        ],
        "failure_detected_at": "2024-06-15T14:35:00Z",
        "failure_summary": reason,
        "alerts_fired": [
            "error_rate_exceeded_threshold",
            "p99_latency_breached",
            "health_check_failures",
        ],
        "incident_opened": "2024-06-15T14:36:00Z",
        "on_call_paged": True,
    }, indent=2) + "\n"


def _service_deps(svc_a, svc_b, svc_c, port_a, port_b, port_c):
    return f"""services:
  {svc_a}:
    port: {port_a}
    role: entry_point
    depends_on:
      - {svc_b}
    description: >
      Traffic entry point. Routes all incoming requests to {svc_b}
      for processing. Must be rolled back LAST.

  {svc_b}:
    port: {port_b}
    role: business_logic
    depends_on:
      - {svc_c}
    description: >
      Core business logic layer. Depends on {svc_c} for persistence.
      Must be rolled back AFTER {svc_c} and BEFORE {svc_a}.

  {svc_c}:
    port: {port_c}
    role: data_layer
    depends_on: []
    description: >
      Persistent data and state layer. No upstream dependencies.
      Must be rolled back FIRST to ensure schema compatibility.

dependency_notes:
  - rollback_order: [{svc_c}, {svc_b}, {svc_a}]
  - reason: leaf-first ensures data compatibility before reconnecting consumers
  - violation_risk: rolling back {svc_a} before {svc_c} risks data corruption
"""


def _rollback_procedures(svc_a, svc_b, svc_c, broken_ver, stable_ver_a, stable_ver_b, stable_ver_c):
    return f"""# Rollback Procedures

## Overview

This document describes per-service rollback procedures.
Always follow the dependency-ordered sequence defined in `service_deps.yaml`.

---

## {svc_c} — Data Layer

**Broken version**: `{broken_ver}`
**Rollback target**: `{stable_ver_c}`

### Steps
1. Confirm no in-flight writes: `curl -s http://localhost/internal/drain`
2. Execute rollback: `kubectl rollout undo deployment/{svc_c} --to-revision=<prev>`
3. Verify target version: `kubectl get deployment/{svc_c} -o jsonpath='{{.spec.template.spec.containers[0].image}}'`
4. Wait for pods to be Running: `kubectl rollout status deployment/{svc_c}`
5. Confirm health check passes: `curl -f http://localhost/health`
6. Run schema compatibility check: `python3 scripts/check_schema_compat.py`

### Rollback Success Criteria
- All pods Running and Ready
- Health endpoint returns `{{"status": "ok"}}`
- Schema version matches `{stable_ver_c}`

---

## {svc_b} — Business Logic

**Broken version**: `{broken_ver}`
**Rollback target**: `{stable_ver_b}`

### Prerequisites
- `{svc_c}` must be healthy and at version `{stable_ver_c}` before proceeding.

### Steps
1. Drain connections gracefully: wait 30s after {svc_c} rollback
2. Execute rollback: `kubectl rollout undo deployment/{svc_b} --to-revision=<prev>`
3. Wait for pods: `kubectl rollout status deployment/{svc_b}`
4. Confirm health: `curl -f http://localhost/health`
5. Run integration smoke test: `python3 scripts/smoke_test.py --service={svc_b}`

### Rollback Success Criteria
- Health endpoint returns `{{"status": "ok"}}`
- Can successfully call `{svc_c}` API

---

## {svc_a} — Entry Point

**Broken version**: `{broken_ver}`
**Rollback target**: `{stable_ver_a}`

### Prerequisites
- `{svc_b}` must be healthy and at version `{stable_ver_b}` before proceeding.
- `{svc_c}` must be healthy and at version `{stable_ver_c}` before proceeding.

### Steps
1. Shift 5% traffic to canary (old version) to validate
2. Execute rollback: `kubectl rollout undo deployment/{svc_a} --to-revision=<prev>`
3. Wait for pods: `kubectl rollout status deployment/{svc_a}`
4. Confirm health: `curl -f http://localhost/health`
5. Shift 100% traffic back
6. Monitor error rates for 5 minutes

### Rollback Success Criteria
- Health endpoint returns `{{"status": "ok"}}`
- Error rate drops below 0.1%
- All downstream services healthy

---

## Post-Rollback Verification

After all three services are rolled back:
1. Run full integration test suite: `pytest tests/integration/ -v`
2. Verify all health checks pass simultaneously
3. Confirm versions match rollback targets
4. Monitor dashboards for 15 minutes
5. Update incident ticket with rollback completion time
"""


def _health_endpoints(svc_a, svc_b, svc_c, port_a, port_b, port_c):
    return json.dumps({
        "services": {
            svc_a: {
                "health_url": f"http://127.0.0.1:{port_a}/health",
                "port": port_a,
                "expected_response": {"status": "ok", "service": svc_a},
            },
            svc_b: {
                "health_url": f"http://127.0.0.1:{port_b}/health",
                "port": port_b,
                "expected_response": {"status": "ok", "service": svc_b},
            },
            svc_c: {
                "health_url": f"http://127.0.0.1:{port_c}/health",
                "port": port_c,
                "expected_response": {"status": "ok", "service": svc_c},
            },
        },
        "current_status": {
            svc_a: "unhealthy",
            svc_b: "unhealthy",
            svc_c: "unhealthy",
        },
    }, indent=2) + "\n"


def _incident_summary(svc_a, svc_b, svc_c, broken_ver, reason):
    return f"""# Incident Summary

**Incident ID**: INC-ROLLBACK-001
**Severity**: P1
**Status**: Active

## What Happened

At 14:30 UTC, a coordinated deployment of version `{broken_ver}` was pushed
to all three services ({svc_a}, {svc_b}, {svc_c}). Within 5 minutes,
alerts began firing across all services.

**Root cause**: {reason}

## Impact

- All user-facing requests failing with 500 errors
- Data writes may have been partially applied
- Estimated affected users: ~100% of active sessions

## Decision

Immediate rollback to last stable version required.
The Planner must produce a dependency-ordered rollback plan.

## Timeline

- 14:30:05 {svc_c} deployed at {broken_ver}
- 14:31:10 {svc_b} deployed at {broken_ver}
- 14:32:15 {svc_a} deployed at {broken_ver}
- 14:35:00 Failure detected — error rate >95%
- 14:36:00 On-call paged, incident opened
- 14:40:00 Decision: rollback all three services
"""


def _current_state(svc_a, svc_b, svc_c, broken_ver, port_a, port_b, port_c):
    return json.dumps({
        "timestamp": "2024-06-15T14:40:00Z",
        "services": {
            svc_a: {
                "version": broken_ver,
                "status": "unhealthy",
                "port": port_a,
                "error_rate_pct": 97.3,
                "last_healthy_version": f"{broken_ver.split('.')[0]}.{int(broken_ver.split('.')[1]) - 1}.5",
            },
            svc_b: {
                "version": broken_ver,
                "status": "unhealthy",
                "port": port_b,
                "error_rate_pct": 98.1,
                "last_healthy_version": f"{broken_ver.split('.')[0]}.{int(broken_ver.split('.')[1]) - 1}.3",
            },
            svc_c: {
                "version": broken_ver,
                "status": "unhealthy",
                "port": port_c,
                "error_rate_pct": 99.4,
                "last_healthy_version": f"{broken_ver.split('.')[0]}.{int(broken_ver.split('.')[1]) - 1}.1",
            },
        },
        "rollback_approved": True,
        "approved_by": "incident_commander",
    }, indent=2) + "\n"


def _change_history(svc_a, svc_b, svc_c, broken_ver, stable_ver_a, reason):
    return (
        f"2024-06-15T14:30:05Z  DEPLOY  {svc_c}  {stable_ver_a.rsplit('.', 1)[0]}.1 -> {broken_ver}  operator=ci_pipeline\n"
        f"2024-06-15T14:31:10Z  DEPLOY  {svc_b}  {stable_ver_a.rsplit('.', 1)[0]}.3 -> {broken_ver}  operator=ci_pipeline\n"
        f"2024-06-15T14:32:15Z  DEPLOY  {svc_a}  {stable_ver_a} -> {broken_ver}  operator=ci_pipeline\n"
        f"2024-06-15T14:35:00Z  ALERT   all_services  error_rate_threshold_breached\n"
        f"2024-06-15T14:36:00Z  INCIDENT  INC-ROLLBACK-001  opened  severity=P1\n"
        f"2024-06-15T14:36:30Z  NOTE    root_cause='{reason}'\n"
        f"2024-06-15T14:40:00Z  DECISION  rollback_approved  all_three_services\n"
    )


def _runbook(svc_a, svc_b, svc_c):
    return f"""# Rollback Runbook

## When to Rollback

Initiate a rollback when:
- Error rate exceeds 5% for more than 2 minutes
- P99 latency exceeds 5x baseline
- Health checks failing on 2+ services simultaneously

## Pre-Rollback Checklist

- [ ] Snapshot current state (versions, config, running pod count)
- [ ] Confirm rollback target versions are available in artifact registry
- [ ] Notify stakeholders via #incidents channel
- [ ] Ensure at least 2 engineers are available to monitor

## Rollback Execution

Follow the dependency-ordered procedure from `rollback_procedures.md`.
**Never skip the health check between steps.**

Service dependency order (rollback: leaf first):
  {svc_c} → {svc_b} → {svc_a}

## Post-Rollback Checklist

- [ ] All services report healthy
- [ ] Error rate back below 0.1%
- [ ] Versions confirmed in production registry
- [ ] Smoke tests passing
- [ ] Incident ticket updated with rollback completion

## Escalation

If rollback fails after 3 attempts, escalate to:
- Engineering VP (primary)
- On-call architect (secondary)
"""
