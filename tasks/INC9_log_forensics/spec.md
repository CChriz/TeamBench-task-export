# INC9: Log Forensics — Hidden Constraints

## Incident Summary

**Incident ID**: INC-2024-0615-009
**Severity**: P1
**Status**: Post-incident analysis required

Three services experienced a cascading failure. Your task is to analyse
the log files and produce a structured root cause report.

---

## Service Topology

```
api_gateway (entry point)
  └── calls: user_service (business logic)
        └── calls: db_proxy (data proxy / DB adapter)
```

See `topology.yaml` for full connection details.

---

## Known Red Herrings

The Planner must brief the Executor on these false signals:

### Red Herring 1: Batch Job Error Spike (NOT the root cause)

Around `2024-06-15T03:30:00Z`, `api_gateway.log` shows a spike of 5xx errors
lasting ~8 minutes. This is caused by the scheduled job `nightly_report_generator` which
runs daily at 03:30 and creates elevated load on `api_gateway`.

**Why it is a red herring**: The `nightly_report_generator` error spike is a documented,
expected behaviour listed in `known_scheduled_jobs.json`. It completes by
03:38 and error rates return to normal. The actual cascading failure begins
at 03:47 — 9 minutes after the batch job finishes.

### Red Herring 2: Clock Skew on `db_proxy` (NOT the root cause)

Log timestamps from `db_proxy` appear to show errors starting *before* `user_service`
errors — suggesting `db_proxy` might be the origin. However, this is caused by
clock skew: `NTP sync delta: +3.2s (clocks not synchronized at incident time)`.
The `ntp_status.txt` file documents this.

**Why it is a red herring**: Correcting for the NTP delta shows `user_service`
errors precede `db_proxy` errors by ~6 seconds. `db_proxy` errors are a
downstream consequence, not the origin.

---

## Real Root Cause

**Service**: `user_service`
**Time**: `2024-06-15T03:47:12Z`
**Cause Type**: `connection_pool_exhaustion`

At `2024-06-15T03:47:12Z`, `user_service` exhausted its database connection pool:
`connection pool exhausted: max_connections=10 active=10 waiting=47`

Long-running transactions from the prior batch job window left connections
held open. When the next traffic wave arrived, all connections were occupied
and new requests queued indefinitely. `api_gateway` began timing out waiting for
`user_service` responses. `db_proxy` received a flood of retry connections that
also exhausted its proxy pool.

---

## Required Output: root_cause_report.json

```json
{
  "incident_id": "INC-2024-0615-009",
  "root_cause": {
    "service": "user_service",
    "cause_type": "connection_pool_exhaustion",
    "description": "<one sentence>",
    "first_observed": "<ISO8601 timestamp>"
  },
  "timeline": [
    {"time": "<ISO8601>", "event": "<description>", "service": "<name>"},
    ...
  ],
  "affected_services": ["api_gateway", "user_service", "db_proxy"],
  "false_leads": [
    {"description": "batch job error spike", "why_not_root_cause": "<reason>"},
    {"description": "clock skew timestamp inversion", "why_not_root_cause": "<reason>"}
  ],
  "remediation": "<recommended fix>"
}
```

---

## Constraints

- `root_cause.service` must be `"user_service"`.
- `root_cause.cause_type` must contain `"connection_pool"` or `"pool_exhaustion"`.
- `timeline` must have at least 3 chronologically ordered events.
- `affected_services` must list all three services.
- `false_leads` must address both red herrings.
- Verifier must produce `attestation.json` with `verdict="pass"`.
