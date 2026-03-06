"""
Parameterized generator for O7: Service Capacity Planning.

Each seed produces 3 services with different performance anti-patterns:
  1. service_a: N+1 query pattern (fetches items in a loop)
  2. service_b: Unbounded in-memory cache (grows until OOM)
  3. service_c: Synchronous blocking external API call

Seed variants use different domain names (order_system, user_platform, inventory_tracker).
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

CONFIGS = [
    {
        "name": "order_system",
        "svc_a_entity": "Order",
        "svc_a_related": "OrderItem",
        "svc_a_table": "orders",
        "svc_a_rel_table": "order_items",
        "svc_b_cache_name": "product_cache",
        "svc_b_entity": "Product",
        "svc_c_api": "payment_gateway",
        "svc_c_endpoint": "https://payments.example.com/verify",
        "p99_current": 450,
        "error_rate_current": 0.3,
        "mem_current_mb": 1800,
    },
    {
        "name": "user_platform",
        "svc_a_entity": "User",
        "svc_a_related": "Session",
        "svc_a_table": "users",
        "svc_a_rel_table": "sessions",
        "svc_b_cache_name": "profile_cache",
        "svc_b_entity": "Profile",
        "svc_c_api": "email_service",
        "svc_c_endpoint": "https://mail.example.com/send",
        "p99_current": 320,
        "error_rate_current": 0.5,
        "mem_current_mb": 2200,
    },
    {
        "name": "inventory_tracker",
        "svc_a_entity": "Warehouse",
        "svc_a_related": "StockItem",
        "svc_a_table": "warehouses",
        "svc_a_rel_table": "stock_items",
        "svc_b_cache_name": "location_cache",
        "svc_b_entity": "Location",
        "svc_c_api": "shipping_api",
        "svc_c_endpoint": "https://ship.example.com/rates",
        "p99_current": 380,
        "error_rate_current": 0.2,
        "mem_current_mb": 1500,
    },
]


class Generator(TaskGenerator):
    task_id = "O7_capacity_planning"
    domain = "operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        c = CONFIGS[seed % len(CONFIGS)]

        workspace_files = self._make_workspace(c, rng)

        expected = {
            "system": c["name"],
            "bug_count": 3,
            "bugs": [
                "n_plus_one_query_in_service_a",
                "unbounded_cache_in_service_b",
                "synchronous_blocking_api_in_service_c",
            ],
            "svc_a_fix": "batch_query_all_related_in_single_query",
            "svc_b_fix": "bounded_lru_cache_max_1000",
            "svc_c_fix": "async_non_blocking_api_call",
            "sla_p99_ms": 100,
            "sla_error_rate_pct": 0.1,
            "sla_memory_mb": 512,
            "svc_a_entity": c["svc_a_entity"],
            "svc_b_entity": c["svc_b_entity"],
            "svc_c_api": c["svc_c_api"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._spec(c),
            brief_md=self._brief(c),
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_workspace(self, c: dict, rng: SeededRandom) -> dict[str, str]:
        files: dict[str, str] = {}
        files["service_a.py"] = self._service_a(c)
        files["service_b.py"] = self._service_b(c)
        files["service_c.py"] = self._service_c(c)
        files["db.py"] = self._fake_db(c)
        files["load_test_results.json"] = self._load_test_results(c)
        files["SLA.md"] = self._sla_md(c)
        files["CAPACITY_REPORT.md"] = self._capacity_report(c)
        files["run_benchmark.py"] = self._benchmark(c)
        files["tests/__init__.py"] = ""
        files["tests/test_services.py"] = self._test_services(c)
        return files

    def _service_a(self, c: dict) -> str:
        ent = c["svc_a_entity"]
        rel = c["svc_a_related"]
        tbl = c["svc_a_table"]
        rel_tbl = c["svc_a_rel_table"]
        ent_lower = ent.lower()
        rel_lower = rel.lower()
        return f'''\
"""Service A: {ent} listing for {c["name"]}.

This service fetches {ent_lower}s with their related {rel_lower}s.

BUG: N+1 query pattern — fetches each {rel_lower} set in a separate query.
FIX: Use a single JOIN or IN-clause query to batch all related rows.
"""
import time
from db import Database


def get_database() -> Database:
    return Database()


def list_{ent_lower}s_with_items(db: Database = None) -> list[dict]:
    """List all {ent_lower}s with related {rel_lower}s.

    BUG: N+1 — one query per {ent_lower} to fetch its {rel_lower}s.
    """
    if db is None:
        db = get_database()

    # 1 query to fetch all parent entities
    {ent_lower}s = db.query("SELECT * FROM {tbl}")

    results = []
    for entity in {ent_lower}s:
        # BUG: N additional queries (one per entity)
        items = db.query(
            f"SELECT * FROM {rel_tbl} WHERE {ent_lower}_id = {{entity['id']}}"
        )
        entity["items"] = items
        results.append(entity)

    return results


def get_{ent_lower}_count(db: Database = None) -> int:
    """Get total count of {ent_lower}s."""
    if db is None:
        db = get_database()
    rows = db.query("SELECT COUNT(*) as cnt FROM {tbl}")
    return rows[0]["cnt"] if rows else 0
'''

    def _service_b(self, c: dict) -> str:
        ent = c["svc_b_entity"]
        cache_name = c["svc_b_cache_name"]
        ent_lower = ent.lower()
        return f'''\
"""Service B: {ent} caching for {c["name"]}.

BUG: Cache grows unbounded — no size limit or eviction policy.
FIX: Bound the cache to a maximum size (e.g., 1000 entries) with LRU eviction.
"""
from db import Database


class {ent}Cache:
    """In-memory cache for {ent_lower} lookups.

    BUG: No size limit — cache grows until OOM under sustained load.
    """

    def __init__(self):
        self._cache: dict = {{}}   # BUG: unbounded dict
        self._db = Database()

    def get(self, key: str):
        """Get a {ent_lower} by key, using cache if available."""
        if key in self._cache:
            return self._cache[key]

        result = self._db.query(
            f"SELECT * FROM {ent_lower}s WHERE id = '{{key}}'"
        )
        if result:
            self._cache[key] = result[0]
            return result[0]
        return None

    def put(self, key: str, value: dict) -> None:
        """Store a value in the cache with no eviction."""
        self._cache[key] = value   # BUG: no max size check

    def size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()


# Global cache instance
{cache_name} = {ent}Cache()


def lookup_{ent_lower}(key: str):
    return {cache_name}.get(key)


def cache_stats() -> dict:
    return {{"size": {cache_name}.size()}}
'''

    def _service_c(self, c: dict) -> str:
        api = c["svc_c_api"]
        endpoint = c["svc_c_endpoint"]
        return f'''\
"""Service C: {api} integration for {c["name"]}.

BUG: Synchronous blocking HTTP call holds up the worker thread.
FIX: Use asyncio, threading, or concurrent.futures to make the call non-blocking.
"""
import time
import requests


API_ENDPOINT = "{endpoint}"
API_TIMEOUT = 30  # seconds


def call_external_api(payload: dict) -> dict:
    """Call the external {api} API.

    BUG: Synchronous blocking call — blocks the entire worker thread until done.
    Under concurrent load all threads pile up waiting for the API response.
    """
    # BUG: blocking call
    response = requests.post(
        API_ENDPOINT,
        json=payload,
        timeout=API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def process_request(data: dict) -> dict:
    """Process an incoming request with external API verification."""
    validated = validate_payload(data)
    if not validated:
        return {{"error": "Invalid payload"}}

    # BUG: synchronous call blocks here
    api_result = call_external_api(validated)

    return {{
        "status": "processed",
        "external_result": api_result,
        "timestamp": time.time(),
    }}


def validate_payload(data: dict) -> dict | None:
    """Validate incoming request payload."""
    if not isinstance(data, dict):
        return None
    if "id" not in data:
        return None
    return data
'''

    def _fake_db(self, c: dict) -> str:
        tbl = c["svc_a_table"]
        rel_tbl = c["svc_a_rel_table"]
        ent_lower = c["svc_b_entity"].lower()
        return f'''\
"""Fake database for testing {c["name"]} services."""
import time


class Database:
    """Simulated database with configurable per-query latency."""

    def __init__(self, latency_ms: float = 2.0):
        self._latency = latency_ms / 1000.0
        self._query_count = 0

    def query(self, sql: str) -> list[dict]:
        """Execute a simulated query."""
        time.sleep(self._latency)
        self._query_count += 1

        if "COUNT" in sql.upper():
            return [{{"cnt": 50}}]
        elif "{rel_tbl}" in sql:
            return [
                {{"id": 1, "name": "item_1", "quantity": 10}},
                {{"id": 2, "name": "item_2", "quantity": 5}},
            ]
        elif "{tbl}" in sql:
            return [{{"id": i, "name": f"entity_{{i}}"}} for i in range(1, 51)]
        elif "{ent_lower}" in sql:
            return [{{"id": "1", "name": "cached_item", "value": 42}}]
        return []

    @property
    def query_count(self) -> int:
        return self._query_count
'''

    def _load_test_results(self, c: dict) -> str:
        data = {
            "test_date": "2025-01-15",
            "duration_seconds": 300,
            "services": {
                "service_a": {
                    "requests": 10000,
                    "p50_ms": 85,
                    "p95_ms": 210,
                    "p99_ms": c["p99_current"],
                    "error_rate_pct": 0.02,
                    "issue": "N+1 query pattern causing latency spikes under load",
                },
                "service_b": {
                    "requests": 50000,
                    "p50_ms": 5,
                    "p95_ms": 15,
                    "p99_ms": 45,
                    "error_rate_pct": c["error_rate_current"],
                    "memory_mb": c["mem_current_mb"],
                    "issue": "Cache grows linearly with unique keys, no eviction",
                },
                "service_c": {
                    "requests": 5000,
                    "p50_ms": 150,
                    "p95_ms": 800,
                    "p99_ms": 2500,
                    "error_rate_pct": 15.0,
                    "issue": "Synchronous external API calls blocking all worker threads",
                },
            },
        }
        return json.dumps(data, indent=2)

    def _sla_md(self, c: dict) -> str:
        return f"""\
# SLA Requirements: {c["name"]}

## Latency
- p99 latency < 100ms for all services

## Error Rate
- Error rate < 0.1% for all services

## Memory
- Peak memory < 512MB per service instance

## Notes
- SLAs measured over 5-minute rolling windows
- Violations trigger automated incident response
"""

    def _capacity_report(self, c: dict) -> str:
        ent = c["svc_a_entity"]
        ent_lower = ent.lower()
        return f"""\
# Capacity Report: {c["name"]}

## Current Status: SLA VIOLATIONS DETECTED

### Service A ({ent} Listing)
- p99: {c["p99_current"]}ms  [SLA: < 100ms — VIOLATION]
- Root cause: N+1 query in `list_{ent_lower}s_with_items()` — 50 queries per request

### Service B ({c["svc_b_entity"]} Cache)
- Memory: {c["mem_current_mb"]}MB  [SLA: < 512MB — VIOLATION]
- Error rate: {c["error_rate_current"]}%  [SLA: < 0.1% — VIOLATION]
- Root cause: cache `{c["svc_b_cache_name"]}` grows without bound; eventual OOM kills

### Service C ({c["svc_c_api"]} Integration)
- p99: 2500ms  [SLA: < 100ms — VIOLATION]
- Error rate: 15%  [SLA: < 0.1% — VIOLATION]
- Root cause: synchronous blocking call to `{c["svc_c_endpoint"]}`

## Recommended Actions
1. Batch the N+1 queries in `service_a.py`
2. Add LRU eviction / size cap in `service_b.py`
3. Make external API call async/non-blocking in `service_c.py`
"""

    def _benchmark(self, c: dict) -> str:
        ent = c["svc_a_entity"]
        ent_lower = ent.lower()
        cache_cls = c["svc_b_entity"]
        return f'''\
"""Benchmark runner for {c["name"]}. DO NOT MODIFY."""
import sys
import time


def benchmark_service_a() -> bool:
    """Check service_a uses batch queries (not N+1)."""
    from db import Database
    import service_a

    db = Database(latency_ms=2.0)
    start = time.time()
    service_a.list_{ent_lower}s_with_items(db)
    elapsed_ms = (time.time() - start) * 1000

    if db.query_count > 5:
        print(f"FAIL: service_a made {{db.query_count}} queries (N+1 detected, expected <= 5)")
        return False
    if elapsed_ms > 100:
        print(f"FAIL: service_a elapsed {{elapsed_ms:.0f}}ms (SLA: < 100ms)")
        return False
    print(f"PASS: service_a — {{db.query_count}} queries in {{elapsed_ms:.0f}}ms")
    return True


def benchmark_service_b() -> bool:
    """Check service_b cache is bounded."""
    import service_b

    cache = service_b.{cache_cls}Cache()
    for i in range(10000):
        cache.put(f"key_{{i}}", {{"id": i, "data": "x" * 100}})

    if cache.size() > 1000:
        print(f"FAIL: service_b cache size = {{cache.size()}} (unbounded; expected <= 1000)")
        return False
    print(f"PASS: service_b — cache bounded at {{cache.size()}} entries")
    return True


def benchmark_service_c() -> bool:
    """Check service_c uses async/non-blocking pattern."""
    import ast

    with open("service_c.py", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)

    has_async = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            has_async = True
        if isinstance(node, ast.Name) and node.id in ("asyncio", "threading", "concurrent"):
            has_async = True
        if isinstance(node, ast.Attribute) and node.attr in (
            "run_in_executor", "gather", "Thread", "submit", "run_until_complete"
        ):
            has_async = True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("asyncio", "threading", "concurrent", "aiohttp"):
                    has_async = True
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(
                ("asyncio", "threading", "concurrent", "aiohttp")
            ):
                has_async = True

    if not has_async:
        print("FAIL: service_c still uses synchronous blocking pattern")
        return False
    print("PASS: service_c — uses async/non-blocking pattern")
    return True


if __name__ == "__main__":
    results = [
        ("service_a", benchmark_service_a()),
        ("service_b", benchmark_service_b()),
        ("service_c", benchmark_service_c()),
    ]
    if not all(ok for _, ok in results):
        print("\\nBenchmark FAILED — SLA violations remain")
        sys.exit(1)
    print("\\nBenchmark PASSED — all services within SLA")
    sys.exit(0)
'''

    def _test_services(self, c: dict) -> str:
        ent = c["svc_a_entity"]
        ent_lower = ent.lower()
        cache_cls = c["svc_b_entity"]
        cache_name = c["svc_b_cache_name"]
        return f'''\
"""Unit tests for {c["name"]} services."""
import pytest


def test_service_a_returns_list():
    from db import Database
    import service_a
    db = Database(latency_ms=0.1)
    results = service_a.list_{ent_lower}s_with_items(db)
    assert len(results) > 0
    assert "items" in results[0]


def test_service_a_count():
    from db import Database
    import service_a
    db = Database(latency_ms=0.1)
    count = service_a.get_{ent_lower}_count(db)
    assert count > 0


def test_service_b_cache_put_get():
    import service_b
    cache = service_b.{cache_cls}Cache()
    cache.put("k1", {{"id": 1, "value": "test"}})
    result = cache.get("k1")
    assert result is not None
    assert result["id"] == 1


def test_service_b_stats():
    import service_b
    stats = service_b.cache_stats()
    assert "size" in stats


def test_service_c_validates_missing_id():
    import service_c
    assert service_c.validate_payload({{}}) is None


def test_service_c_validates_valid():
    import service_c
    assert service_c.validate_payload({{"id": 1}}) is not None
'''

    def _spec(self, c: dict) -> str:
        ent = c["svc_a_entity"]
        ent_lower = ent.lower()
        return f"""\
# O7: Service Capacity Planning

## Goal
Fix performance issues in 3 services to bring them within SLA constraints.

## Requirements
1. Fix `service_a.py`: eliminate N+1 query pattern in `list_{ent_lower}s_with_items()` — batch all related-item queries into a single query
2. Fix `service_b.py`: bound the in-memory `{c["svc_b_entity"]}Cache` to prevent OOM — add LRU or size-capped eviction (max 1000 entries)
3. Fix `service_c.py`: make `call_external_api()` non-blocking — use `asyncio`, `threading`, or `concurrent.futures`
4. All services must meet SLA: p99 latency < 100ms, error rate < 0.1%, memory < 512MB
5. Do NOT remove functionality — optimize, do not delete features
6. Run `python run_benchmark.py` to verify SLA compliance

## Supporting Documents
- `service_a.py` — N+1 query bug
- `service_b.py` — Unbounded cache bug
- `service_c.py` — Blocking external API call bug
- `load_test_results.json` — Current metrics showing SLA violations
- `SLA.md` — SLA definitions
- `CAPACITY_REPORT.md` — Per-service violation summary
- `run_benchmark.py` — Benchmark runner (do not modify)

## Important
Do NOT modify `SLA.md`, `run_benchmark.py`, or `load_test_results.json`.
"""

    def _brief(self, c: dict) -> str:
        return f"""\
# O7: Service Capacity Planning (Brief)

Fix 3 performance anti-patterns in the {c["name"]} services:
1. `service_a.py` — N+1 query (batch it)
2. `service_b.py` — unbounded cache (add size cap)
3. `service_c.py` — blocking API call (make it async)

Run: `python run_benchmark.py`
"""
