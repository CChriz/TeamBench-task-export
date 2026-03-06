"""
Parameterized generator for INC9: Log Forensics (Hidden Constraints / Red Herrings).

Each seed produces:
  - 3 service logs (service_a.log, service_b.log, service_c.log) with 500+ total lines
  - topology.yaml describing service relationships
  - 2 red herrings: a high-error-rate event that is actually normal (e.g. batch job),
    and a timestamp cluster from clock skew that looks causal but isn't
  - Correct root cause: a specific service's DB connection pool exhaustion cascades

TNI driver: The spec tells the Planner the topology, the two red herrings and why
they are false, and the real root cause signal. The brief only says "cascading
failure in 3 services — find root cause". Without the Planner the Executor
will likely misattribute the root cause to one of the red herrings.

Grader checks (9):
  1. root_cause_report.json exists
  2. root_cause.service matches expected service
  3. root_cause.cause_type is "connection_pool_exhaustion" (or contains expected keyword)
  4. timeline array has at least 3 events
  5. affected_services lists all 3 services
  6. Report does NOT name the red-herring batch job as root cause
  7. Report does NOT name clock skew as root cause
  8. first_event timestamp is within the correct time window
  9. Attestation verdict=pass
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Pools ────────────────────────────────────────────────────────────────────

SERVICE_TRIPLETS = [
    ("api_gateway", "user_service", "db_proxy"),
    ("frontend", "order_service", "postgres_proxy"),
    ("web_server", "payment_service", "mysql_proxy"),
    ("ingress", "catalog_service", "cache_proxy"),
    ("load_balancer", "session_service", "redis_proxy"),
    ("edge_router", "auth_service", "mongo_proxy"),
    ("proxy", "billing_service", "clickhouse_proxy"),
    ("gateway", "search_service", "elastic_proxy"),
    ("dispatcher", "recommendation_service", "cassandra_proxy"),
    ("router", "analytics_service", "pg_proxy"),
]

# Red herring 1: batch job that causes high error rate — but it's expected
BATCH_JOB_NAMES = [
    "nightly_report_generator",
    "daily_data_archiver",
    "weekly_audit_scanner",
    "hourly_cache_warmer",
    "scheduled_index_rebuilder",
    "periodic_cleanup_job",
    "cron_stats_aggregator",
    "automated_backup_runner",
    "batch_email_sender",
    "daily_reconciliation_job",
]

# Root cause: DB connection pool exhaustion on service B
DB_POOL_ERRORS = [
    "connection pool exhausted: max_connections=10 active=10 waiting=47",
    "too many clients: pool_size=20 overflow=0 all connections in use",
    "connection acquire timeout after 5000ms: pool_size=15 queue_depth=32",
    "FATAL: remaining connection slots are reserved for replication",
    "connection pool timeout: 25 waiters, 0 available connections",
    "max_pool_size reached: 30/30 connections active, request queued",
    "HikariPool: connection is not available after 3000ms",
    "pg: sorry, too many clients already (limit=25)",
    "connection pool deadlock: all 12 connections held by blocked transactions",
    "WARN pool_exhausted: acquired=40 limit=40 avg_hold_ms=12450",
]

# Cascade error on service C (downstream of B)
CASCADE_ERRORS = [
    "upstream connection refused: service_b:8081 — retrying (1/3)",
    "circuit breaker OPEN: downstream failure rate=100% for 30s",
    "dependency timeout: service_b did not respond within 2000ms",
    "upstream unavailable: received 503 from service_b after 3 retries",
    "health dependency check failed: service_b returned 500",
]

# Red herring 2: clock skew — logs from svc_c show earlier timestamps than svc_b
CLOCK_SKEW_NOTES = [
    "NTP sync delta: +3.2s (clocks not synchronized at incident time)",
    "host clock skew detected: node_b ahead of node_c by 4.1 seconds",
    "timestamp discrepancy: service_c logs appear 5s before service_b but clock drift explains this",
    "node time offset: service_a NTP delta=-2.8s vs service_b NTP delta=+1.3s",
    "WARNING: log aggregator detected out-of-order events due to 3.5s clock skew on node_c",
]


class Generator(TaskGenerator):
    task_id = "INC9_log_forensics"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        svc_a, svc_b, svc_c = SERVICE_TRIPLETS[seed % len(SERVICE_TRIPLETS)]
        batch_job = BATCH_JOB_NAMES[(seed * 3 + 1) % len(BATCH_JOB_NAMES)]
        db_pool_error = DB_POOL_ERRORS[(seed * 7 + 2) % len(DB_POOL_ERRORS)]
        cascade_error = CASCADE_ERRORS[(seed * 5 + 3) % len(CASCADE_ERRORS)]
        clock_skew_note = CLOCK_SKEW_NOTES[(seed * 11 + 4) % len(CLOCK_SKEW_NOTES)]

        # Port numbers
        port_a = 8080 + (seed % 5) * 100
        port_b = 8081 + (seed % 5) * 100
        port_c = 8082 + (seed % 5) * 100

        # The real root cause is DB connection pool exhaustion on svc_b
        # triggered at 03:47:12Z
        root_cause_time = "2024-06-15T03:47:12Z"
        first_cascade_time = "2024-06-15T03:47:18Z"  # svc_a sees errors 6s later
        batch_job_time_start = "2024-06-15T03:30:00Z"  # red herring: 17 min earlier

        expected = {
            "svc_a": svc_a,
            "svc_b": svc_b,
            "svc_c": svc_c,
            "root_cause_service": svc_b,
            "root_cause_type": "connection_pool_exhaustion",
            "root_cause_time": root_cause_time,
            "red_herring_batch_job": batch_job,
            "red_herring_clock_skew": True,
            "affected_services": [svc_a, svc_b, svc_c],
            "first_event_window_start": "2024-06-15T03:47:00Z",
            "first_event_window_end": "2024-06-15T03:47:30Z",
        }

        workspace_files = {
            f"{svc_a}.log": _log_svc_a(svc_a, svc_b, svc_c, port_a, port_b, batch_job, cascade_error),
            f"{svc_b}.log": _log_svc_b(svc_a, svc_b, svc_c, port_b, db_pool_error, clock_skew_note),
            f"{svc_c}.log": _log_svc_c(svc_a, svc_b, svc_c, port_c, cascade_error),
            "topology.yaml": _topology(svc_a, svc_b, svc_c, port_a, port_b, port_c),
            "known_scheduled_jobs.json": _scheduled_jobs(batch_job),
            "ntp_status.txt": _ntp_status(clock_skew_note),
            "alert_history.json": _alert_history(svc_a, svc_b, svc_c, batch_job),
        }

        spec_md = self._generate_spec(svc_a, svc_b, svc_c, batch_job, db_pool_error,
                                       clock_skew_note, root_cause_time)
        brief_md = self._generate_brief(svc_a, svc_b, svc_c)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_spec(self, svc_a, svc_b, svc_c, batch_job, db_pool_error,
                       clock_skew_note, root_cause_time):
        return f"""# INC9: Log Forensics — Hidden Constraints

## Incident Summary

**Incident ID**: INC-2024-0615-009
**Severity**: P1
**Status**: Post-incident analysis required

Three services experienced a cascading failure. Your task is to analyse
the log files and produce a structured root cause report.

---

## Service Topology

```
{svc_a} (entry point)
  └── calls: {svc_b} (business logic)
        └── calls: {svc_c} (data proxy / DB adapter)
```

See `topology.yaml` for full connection details.

---

## Known Red Herrings

The Planner must brief the Executor on these false signals:

### Red Herring 1: Batch Job Error Spike (NOT the root cause)

Around `2024-06-15T03:30:00Z`, `{svc_a}.log` shows a spike of 5xx errors
lasting ~8 minutes. This is caused by the scheduled job `{batch_job}` which
runs daily at 03:30 and creates elevated load on `{svc_a}`.

**Why it is a red herring**: The `{batch_job}` error spike is a documented,
expected behaviour listed in `known_scheduled_jobs.json`. It completes by
03:38 and error rates return to normal. The actual cascading failure begins
at 03:47 — 9 minutes after the batch job finishes.

### Red Herring 2: Clock Skew on `{svc_c}` (NOT the root cause)

Log timestamps from `{svc_c}` appear to show errors starting *before* `{svc_b}`
errors — suggesting `{svc_c}` might be the origin. However, this is caused by
clock skew: `{clock_skew_note}`. The `ntp_status.txt` file documents this.

**Why it is a red herring**: Correcting for the NTP delta shows `{svc_b}`
errors precede `{svc_c}` errors by ~6 seconds. `{svc_c}` errors are a
downstream consequence, not the origin.

---

## Real Root Cause

**Service**: `{svc_b}`
**Time**: `{root_cause_time}`
**Cause Type**: `connection_pool_exhaustion`

At `{root_cause_time}`, `{svc_b}` exhausted its database connection pool:
`{db_pool_error}`

Long-running transactions from the prior batch job window left connections
held open. When the next traffic wave arrived, all connections were occupied
and new requests queued indefinitely. `{svc_a}` began timing out waiting for
`{svc_b}` responses. `{svc_c}` received a flood of retry connections that
also exhausted its proxy pool.

---

## Required Output: root_cause_report.json

```json
{{
  "incident_id": "INC-2024-0615-009",
  "root_cause": {{
    "service": "{svc_b}",
    "cause_type": "connection_pool_exhaustion",
    "description": "<one sentence>",
    "first_observed": "<ISO8601 timestamp>"
  }},
  "timeline": [
    {{"time": "<ISO8601>", "event": "<description>", "service": "<name>"}},
    ...
  ],
  "affected_services": ["{svc_a}", "{svc_b}", "{svc_c}"],
  "false_leads": [
    {{"description": "batch job error spike", "why_not_root_cause": "<reason>"}},
    {{"description": "clock skew timestamp inversion", "why_not_root_cause": "<reason>"}}
  ],
  "remediation": "<recommended fix>"
}}
```

---

## Constraints

- `root_cause.service` must be `"{svc_b}"`.
- `root_cause.cause_type` must contain `"connection_pool"` or `"pool_exhaustion"`.
- `timeline` must have at least 3 chronologically ordered events.
- `affected_services` must list all three services.
- `false_leads` must address both red herrings.
- Verifier must produce `attestation.json` with `verdict="pass"`.
"""

    def _generate_brief(self, svc_a, svc_b, svc_c):
        return f"""# INC9: Log Forensics (Brief)

Three services experienced a cascading failure. Analyse the logs to find the root cause.

**Logs available**:
- `{svc_a}.log` — entry-point service
- `{svc_b}.log` — business logic service
- `{svc_c}.log` — data proxy service

**Supporting files**:
- `topology.yaml` — service topology
- `known_scheduled_jobs.json` — scheduled batch job registry
- `ntp_status.txt` — NTP clock synchronisation status
- `alert_history.json` — alert timeline

**Goal**: Produce `root_cause_report.json` identifying the root cause service,
cause type, a timeline of events, and all affected services.

The Planner has the full incident analysis including identification of red
herrings. Coordinate with the Planner before writing your report.
"""


# ── Log generators ────────────────────────────────────────────────────────────

def _log_svc_a(svc_a, svc_b, svc_c, port_a, port_b, batch_job, cascade_error):
    """Entry-point service log — includes red herring batch job spike + real cascade errors."""
    lines = []
    # Normal startup
    lines.append("2024-06-15T02:00:00Z  INFO  startup complete port={} workers=8".format(port_a))
    lines.append("2024-06-15T02:00:01Z  INFO  health check OK")
    # Normal traffic
    for i in range(30):
        t_min = 2 + i // 10
        t_sec = (i * 2) % 60
        lines.append(f"2024-06-15T0{t_min}:{t_sec:02d}:00Z  INFO  GET /api/v1/data 200 12ms")
    # RED HERRING: batch job error spike starting at 03:30
    lines.append("2024-06-15T03:29:58Z  INFO  scheduled job trigger received: {}".format(batch_job))
    lines.append("2024-06-15T03:30:00Z  INFO  {} started".format(batch_job))
    for i in range(40):
        t_sec = i * 10 % 60
        t_min = 30 + (i * 10) // 60
        lines.append(f"2024-06-15T03:{t_min:02d}:{t_sec:02d}Z  ERROR GET /batch/run 503 {batch_job} overloading upstream")
    lines.append("2024-06-15T03:38:00Z  INFO  {} completed successfully".format(batch_job))
    lines.append("2024-06-15T03:38:01Z  INFO  error rate returned to normal 0.01%")
    # Normal traffic resumes
    for i in range(20):
        t_sec = (i * 3) % 60
        lines.append(f"2024-06-15T03:4{i // 10}:{t_sec:02d}Z  INFO  GET /api/v1/resource 200 15ms")
    # REAL CASCADE: at 03:47:18 svc_a starts seeing timeouts from svc_b
    lines.append("2024-06-15T03:47:18Z  ERROR upstream timeout: {}:{} did not respond in 2000ms".format(svc_b, port_b))
    lines.append("2024-06-15T03:47:19Z  ERROR upstream timeout: {}:{} did not respond in 2000ms".format(svc_b, port_b))
    lines.append("2024-06-15T03:47:20Z  ERROR {}".format(cascade_error))
    lines.append("2024-06-15T03:47:21Z  ERROR upstream timeout: {}:{} did not respond in 2000ms".format(svc_b, port_b))
    lines.append("2024-06-15T03:47:22Z  WARN  error_rate=87.3% threshold=5%")
    lines.append("2024-06-15T03:47:23Z  ERROR {}".format(cascade_error))
    lines.append("2024-06-15T03:47:25Z  ALERT error_rate_threshold_breached alerting on-call")
    lines.append("2024-06-15T03:47:30Z  ERROR all requests to {} failing".format(svc_b))
    lines.append("2024-06-15T03:47:35Z  ERROR health_check FAIL: dependency {} unreachable".format(svc_b))
    lines.append("2024-06-15T03:47:40Z  ALERT P1 incident triggered")
    # More cascade errors
    for i in range(20):
        lines.append(f"2024-06-15T03:4{7 + i // 10}:{(i * 3) % 60:02d}Z  ERROR GET /api/v1/data 503 upstream_unavailable")
    return "\n".join(lines) + "\n"


def _log_svc_b(svc_a, svc_b, svc_c, port_b, db_pool_error, clock_skew_note):
    """Business logic service log — shows the real root cause: DB pool exhaustion."""
    lines = []
    lines.append("2024-06-15T02:00:00Z  INFO  {} started port={}".format(svc_b, port_b))
    lines.append("2024-06-15T02:00:01Z  INFO  db connection pool initialized size=10 max_overflow=0")
    # Normal ops
    for i in range(40):
        t_min = 2 + i // 15
        t_sec = (i * 4) % 60
        lines.append(f"2024-06-15T0{t_min}:{t_sec:02d}:00Z  INFO  process_request acquired_conn=1 pool_available=9 duration=45ms")
    # Batch job window: pool gets stressed but recovers
    lines.append("2024-06-15T03:30:05Z  WARN  connection pool pressure: acquired=8 available=2")
    lines.append("2024-06-15T03:31:10Z  WARN  connection pool pressure: acquired=9 available=1")
    lines.append("2024-06-15T03:33:00Z  WARN  long-running transaction detected: conn_id=7 held=45s")
    lines.append("2024-06-15T03:36:00Z  WARN  long-running transaction detected: conn_id=3 held=180s — likely from {} batch".format(svc_a))
    lines.append("2024-06-15T03:38:30Z  INFO  batch window ended: connections returning to pool")
    lines.append("2024-06-15T03:38:35Z  WARN  conn_id=3 still held: 210s — possible leak")
    lines.append("2024-06-15T03:40:00Z  WARN  leaked connections: 2 connections not returned to pool")
    # Root cause event at 03:47:12
    lines.append("2024-06-15T03:46:55Z  WARN  connection pool pressure: acquired=10 available=0 waiting=3")
    lines.append("2024-06-15T03:47:05Z  WARN  connection pool pressure: acquired=10 available=0 waiting=12")
    lines.append("2024-06-15T03:47:12Z  ERROR {}".format(db_pool_error))
    lines.append("2024-06-15T03:47:12Z  ERROR all incoming requests queued: no connections available")
    lines.append("2024-06-15T03:47:13Z  ERROR request queue depth=47 all requests timing out")
    lines.append("2024-06-15T03:47:14Z  ERROR returning 503 to all callers: pool_exhausted")
    lines.append("2024-06-15T03:47:15Z  ERROR health_check degraded: cannot acquire db connection")
    # Note: clock_skew_note mentions the skew — this is meta-context in the logs
    lines.append("2024-06-15T03:47:16Z  INFO  [ntp-monitor] {}".format(clock_skew_note))
    lines.append("2024-06-15T03:47:18Z  ERROR 503 responses to {}: queue_depth=52".format(svc_a))
    for i in range(25):
        lines.append(f"2024-06-15T03:{47 + i // 10}:{(i * 2) % 60:02d}Z  ERROR process_request FAILED pool_exhausted waiting={47 + i * 3}")
    return "\n".join(lines) + "\n"


def _log_svc_c(svc_a, svc_b, svc_c, port_c, cascade_error):
    """Data proxy service log — RED HERRING: timestamps appear early due to clock skew."""
    lines = []
    lines.append("2024-06-15T02:00:00Z  INFO  {} started port={}".format(svc_c, port_c))
    # Normal ops
    for i in range(35):
        t_min = 2 + i // 12
        t_sec = (i * 5) % 60
        lines.append(f"2024-06-15T0{t_min}:{t_sec:02d}:00Z  INFO  query executed duration=8ms rows=1")
    # RED HERRING: Due to clock skew, svc_c's errors appear at 03:47:08
    # (4 seconds before svc_b's pool exhaustion at 03:47:12)
    # But this is clock skew: svc_c's clock is 4s ahead
    lines.append("2024-06-15T03:47:08Z  ERROR connection refused from {}: upstream unavailable [CLOCK_SKEW_ADJUSTED]".format(svc_b))
    lines.append("2024-06-15T03:47:09Z  ERROR retry 1/3: {} unreachable".format(svc_b))
    lines.append("2024-06-15T03:47:10Z  ERROR retry 2/3: {} unreachable".format(svc_b))
    lines.append("2024-06-15T03:47:11Z  ERROR retry 3/3: {} unreachable — giving up".format(svc_b))
    lines.append("2024-06-15T03:47:11Z  WARN  cascade detected: {} → {} failure propagating".format(svc_b, svc_c))
    lines.append("2024-06-15T03:47:12Z  ERROR connection flood: retry storm from multiple callers")
    lines.append("2024-06-15T03:47:13Z  ERROR own connection pool overwhelmed: proxy_connections=95/100")
    lines.append("2024-06-15T03:47:14Z  ERROR {}".format(cascade_error))
    lines.append("2024-06-15T03:47:15Z  ALERT downstream_cascade health=CRITICAL")
    for i in range(20):
        lines.append(f"2024-06-15T03:{47 + i // 8}:{(i * 4) % 60:02d}Z  ERROR query FAILED: upstream {svc_b} pool_exhausted")
    return "\n".join(lines) + "\n"


def _topology(svc_a, svc_b, svc_c, port_a, port_b, port_c):
    return f"""services:
  {svc_a}:
    port: {port_a}
    role: entry_point
    upstream: []
    downstream:
      - {svc_b}

  {svc_b}:
    port: {port_b}
    role: business_logic
    upstream:
      - {svc_a}
    downstream:
      - {svc_c}
    db_pool:
      max_size: 10
      max_overflow: 0
      timeout_ms: 5000

  {svc_c}:
    port: {port_c}
    role: data_proxy
    upstream:
      - {svc_b}
    downstream: []

call_chain: "{svc_a} -> {svc_b} -> {svc_c}"
failure_propagation: downstream_to_upstream
"""


def _scheduled_jobs(batch_job):
    return json.dumps({
        "scheduled_jobs": [
            {
                "name": batch_job,
                "schedule": "daily at 03:30 UTC",
                "expected_duration_minutes": 8,
                "expected_behavior": "causes elevated 5xx rate on api layer for duration",
                "is_error_spike_expected": True,
                "documented_since": "2023-11-01",
                "note": "Error spike during this job is NORMAL and expected. Not an incident.",
            },
            {
                "name": "weekly_config_sync",
                "schedule": "weekly sunday 02:00 UTC",
                "expected_duration_minutes": 2,
                "expected_behavior": "brief config reload, <100ms downtime",
                "is_error_spike_expected": False,
            },
        ]
    }, indent=2) + "\n"


def _ntp_status(clock_skew_note):
    return (
        "NTP Synchronisation Status Report\n"
        "Generated: 2024-06-15T03:50:00Z\n"
        "\n"
        f"NOTE: {clock_skew_note}\n"
        "\n"
        "Node               NTP-Server       Offset(ms)   Jitter(ms)   Reachable\n"
        "service_a_node     ntp1.internal    -2.8         0.4          YES\n"
        "service_b_node     ntp1.internal    +1.3         0.3          YES\n"
        "service_c_node     ntp2.internal    +5.4         0.7          YES\n"
        "\n"
        "service_c_node is ahead of service_b_node by ~4.1 seconds.\n"
        "This explains apparent out-of-order log events between these nodes.\n"
        "Corrected timestamps: service_b errors precede service_c errors by ~6s.\n"
    )


def _alert_history(svc_a, svc_b, svc_c, batch_job):
    return json.dumps({
        "alerts": [
            {
                "time": "2024-06-15T03:30:00Z",
                "name": "high_error_rate",
                "service": svc_a,
                "value": "12.3%",
                "threshold": "5%",
                "resolved_at": "2024-06-15T03:38:10Z",
                "note": f"caused by scheduled {batch_job} — auto-suppressed",
            },
            {
                "time": "2024-06-15T03:47:25Z",
                "name": "high_error_rate",
                "service": svc_a,
                "value": "87.3%",
                "threshold": "5%",
                "resolved_at": None,
                "note": "active — P1 incident",
            },
            {
                "time": "2024-06-15T03:47:15Z",
                "name": "health_check_failing",
                "service": svc_b,
                "value": "FAIL",
                "threshold": "OK",
                "resolved_at": None,
                "note": "active — connection pool exhausted",
            },
            {
                "time": "2024-06-15T03:47:15Z",
                "name": "cascade_detected",
                "service": svc_c,
                "value": "CRITICAL",
                "threshold": "OK",
                "resolved_at": None,
                "note": "active — downstream cascade from {}".format(svc_b),
            },
        ]
    }, indent=2) + "\n"
