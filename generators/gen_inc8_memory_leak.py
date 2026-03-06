"""
Parameterized generator for INC8: Memory Leak Triage.

Each seed produces:
  - Different component names (event processor, cache manager, test helper)
  - Different leak sizes and memory growth numbers in metrics.json
  - Different event/cache types varying the workspace code
  - Seed-specific expected.json, spec.md, brief.md, workspace files

TNI driver: The spec tells the Planner which component has the real leak, which
has expected-by-design growth, and which is a test artifact. The brief only says
"investigate memory growth across 3 components and fix the real leak." Without
the Planner's analysis the Executor may fix all three (breaking the cache),
fix the wrong one, or miss the bounded data structure requirement.

The grader checks:
  1. event_processor.py uses a bounded data structure (deque with maxlen)
  2. cache_manager.py is NOT modified (expected growth)
  3. test_helper.py is NOT modified (test artifact)
  4. All existing tests pass
  5. INCIDENT_REPORT.md exists and classifies all 3 components
"""
from __future__ import annotations

import json
import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Pools
# ---------------------------------------------------------------------------

# (event_type, processor_class, description)
EVENT_TYPES = [
    ("order", "OrderEventProcessor", "order placement and fulfillment events"),
    ("audit", "AuditEventProcessor", "security audit trail events"),
    ("metric", "MetricEventProcessor", "application performance metric events"),
    ("log", "LogEventProcessor", "structured application log events"),
    ("payment", "PaymentEventProcessor", "payment transaction events"),
    ("webhook", "WebhookEventProcessor", "incoming webhook delivery events"),
]

# (cache_type, cache_class, item_description)
CACHE_TYPES = [
    ("session", "SessionCache", "user session tokens"),
    ("query", "QueryResultCache", "database query results"),
    ("asset", "AssetCache", "static asset responses"),
    ("auth", "AuthTokenCache", "authentication tokens"),
    ("response", "ResponseCache", "API response payloads"),
    ("config", "ConfigCache", "configuration key-value pairs"),
]

# (test_helper_name, helper_class, mock_type)
TEST_HELPER_TYPES = [
    ("mock_db", "MockDatabase", "database connection objects"),
    ("mock_http", "MockHttpClient", "HTTP response objects"),
    ("mock_queue", "MockQueue", "queue message objects"),
    ("mock_store", "MockStore", "key-value store entries"),
    ("mock_bus", "MockEventBus", "event bus subscriber objects"),
    ("mock_rpc", "MockRpcClient", "RPC call stub objects"),
]

# Memory growth numbers (leak_mb_per_hour, cache_max_mb, test_accumulated_mb)
MEMORY_PROFILES = [
    (120, 256, 45),
    (85, 512, 30),
    (200, 128, 60),
    (150, 384, 50),
    (95, 192, 35),
    (175, 320, 55),
]

# Max sizes for bounded deque (the fix)
MAXLEN_OPTIONS = [1000, 5000, 10000, 2000, 500, 8000]


class Generator(TaskGenerator):
    task_id = "INC8_memory_leak"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        event_type, processor_class, event_desc = EVENT_TYPES[seed % len(EVENT_TYPES)]
        cache_type, cache_class, cache_item_desc = CACHE_TYPES[(seed * 3 + 1) % len(CACHE_TYPES)]
        helper_name, helper_class, mock_type = TEST_HELPER_TYPES[(seed * 5 + 2) % len(TEST_HELPER_TYPES)]
        leak_mb_hr, cache_max_mb, test_accum_mb = MEMORY_PROFILES[(seed * 7 + 3) % len(MEMORY_PROFILES)]
        maxlen = MAXLEN_OPTIONS[seed % len(MAXLEN_OPTIONS)]

        expected = {
            "real_leak_component": "event_processor.py",
            "real_leak_class": processor_class,
            "real_leak_fix": "use collections.deque(maxlen={}) instead of list".format(maxlen),
            "expected_growth_component": "cache_manager.py",
            "expected_growth_class": cache_class,
            "expected_growth_reason": "LRU cache grows to max_size by design (ARCHITECTURE.md)",
            "test_artifact_component": "test_helper.py",
            "test_artifact_class": helper_class,
            "test_artifact_reason": "accumulates mock objects at module level -- only in CI, not production",
            "do_not_modify": ["cache_manager.py", "test_helper.py"],
            "maxlen": maxlen,
            "leak_mb_per_hour": leak_mb_hr,
            "cache_max_mb": cache_max_mb,
        }

        workspace_files = _build_workspace(
            event_type, processor_class, event_desc,
            cache_type, cache_class, cache_item_desc,
            helper_name, helper_class, mock_type,
            leak_mb_hr, cache_max_mb, test_accum_mb,
            maxlen, seed,
        )

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "INC8_memory_leak"
        )
        spec_path = os.path.join(tasks_dir, "spec.md")
        brief_path = os.path.join(tasks_dir, "brief.md")
        if os.path.exists(spec_path):
            with open(spec_path) as f:
                spec_md = f.read()
        else:
            spec_md = _generate_spec(
                processor_class, cache_class, helper_class,
                leak_mb_hr, cache_max_mb, test_accum_mb,
                event_desc, cache_item_desc, mock_type, maxlen,
            )
        if os.path.exists(brief_path):
            with open(brief_path) as f:
                brief_md = f.read()
        else:
            brief_md = _generate_brief(processor_class, cache_class, helper_class)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )


# ---------------------------------------------------------------------------
# File generation helpers (module-level to avoid indentation in triple-quotes)
# ---------------------------------------------------------------------------

def _build_workspace(
    event_type, processor_class, event_desc,
    cache_type, cache_class, cache_item_desc,
    helper_name, helper_class, mock_type,
    leak_mb_hr, cache_max_mb, test_accum_mb,
    maxlen, seed,
):
    return {
        "event_processor.py": _event_processor_py(
            event_type, processor_class, event_desc
        ),
        "cache_manager.py": _cache_manager_py(
            cache_type, cache_class, cache_item_desc, cache_max_mb
        ),
        "test_helper.py": _test_helper_py(
            helper_name, helper_class, mock_type
        ),
        "metrics.json": _metrics_json(
            processor_class, cache_class, helper_class,
            leak_mb_hr, cache_max_mb, test_accum_mb,
        ),
        "INCIDENT_TICKET.md": _incident_ticket(
            processor_class, cache_class, helper_class,
            leak_mb_hr, cache_max_mb, test_accum_mb,
        ),
        "ARCHITECTURE.md": _architecture_md(
            cache_class, cache_type, cache_item_desc, cache_max_mb
        ),
        "tests/__init__.py": "",
        "tests/test_components.py": _tests_py(
            event_type, processor_class,
            cache_type, cache_class,
            helper_name, helper_class, mock_type,
            maxlen,
        ),
    }


def _generate_spec(
    processor_class, cache_class, helper_class,
    leak_mb_hr, cache_max_mb, test_accum_mb,
    event_desc, cache_item_desc, mock_type, maxlen,
):
    return """\
# INC8: Memory Leak Triage

## Goal
Investigate memory growth across 3 components. Identify and fix only the real
production memory leak. Leave expected behavior and test-only artifacts alone.

## Component Analysis

### {proc} -- event_processor.py
**Classification: REAL LEAK**
Stores every processed event in an unbounded Python `list`. The list grows without
bound for the lifetime of the process. At {leak} MB/hour growth rate under
normal load, it caused OOM-kill in production within ~12 hours.

**Fix**: Replace the list with `collections.deque(maxlen={maxlen})`. This bounds
memory to the last {maxlen} events regardless of runtime duration.

### {cache} -- cache_manager.py
**Classification: EXPECTED GROWTH (DO NOT FIX)**
Implements an LRU cache that grows until it reaches `max_size` (currently set to
fill ~{cmax} MB). This behaviour is documented in `ARCHITECTURE.md` as
intentional. After reaching capacity, old entries are evicted.

**Do NOT modify this file.** Changing the cache design would break downstream
components that depend on warm cache hits.

### {helper} -- test_helper.py
**Classification: TEST ARTIFACT (DO NOT FIX)**
Accumulates {mock} at module level during test runs. This only occurs when
tests are active (CI environment). In production there is no test runner, so
this code never executes and has no memory impact.

**Do NOT modify this file.** Changing test helpers can break CI pipelines.

## Required Output

1. Fix `event_processor.py` to use `collections.deque(maxlen={maxlen})`
2. Do NOT modify `cache_manager.py`
3. Do NOT modify `test_helper.py`
4. Write `INCIDENT_REPORT.md` classifying all 3 components:
   - Component name, classification (REAL_LEAK / EXPECTED / TEST_ARTIFACT), reason
5. All tests in `tests/test_components.py` must continue to pass

## Constraints
- The deque maxlen must be exactly {maxlen}
- Verifier must produce `attestation.json` with `verdict="pass"`
""".format(
        proc=processor_class, cache=cache_class, helper=helper_class,
        leak=leak_mb_hr, cmax=cache_max_mb, mock=mock_type, maxlen=maxlen,
    )


def _generate_brief(processor_class, cache_class, helper_class):
    return """\
# INC8: Memory Leak Triage (Brief)

Three components are showing memory growth in production:
- `event_processor.py` ({proc})
- `cache_manager.py` ({cache})
- `test_helper.py` ({helper})

Review `INCIDENT_TICKET.md` for the OOM-kill timeline, `ARCHITECTURE.md` for
design decisions, and `metrics.json` for memory growth data.

**Goal**: Fix only the real production memory leak. Leave the other two components
unchanged. Write `INCIDENT_REPORT.md` classifying each component's behavior.

The Planner has a full root-cause analysis identifying which component has the
real leak and what the correct fix is. Coordinate with the Planner before making
changes.

Run tests after fix: `pytest tests/`
""".format(proc=processor_class, cache=cache_class, helper=helper_class)


def _event_processor_py(event_type, processor_class, event_desc):
    return '''\
"""
{klass} -- processes incoming {desc}.

REAL MEMORY LEAK: self._processed_events grows without bound.
Every event is appended to a list that is never trimmed. Under production
load this causes the process to consume memory continuously until the OOM
killer terminates it.

Fix: replace list with collections.deque(maxlen=N) to bound memory usage.
"""
from __future__ import annotations

import time
import threading
from typing import Any


class {klass}:
    """Processes {desc} and maintains a processing history."""

    def __init__(self):
        self._lock = threading.Lock()
        # BUG: unbounded list -- grows forever as events arrive
        self._processed_events = []
        self._error_count = 0
        self._total_processed = 0
        self._start_time = time.time()

    def process(self, event: dict) -> dict:
        """Process a single {etype} event and record it."""
        if not isinstance(event, dict):
            raise ValueError("Expected dict, got {{}}".format(type(event).__name__))

        event_id = event.get("id", "{etype}_{{}}".format(self._total_processed))
        timestamp = event.get("timestamp", time.time())

        result = {{
            "id": event_id,
            "status": "processed",
            "timestamp": timestamp,
            "data": event.get("data"),
        }}

        with self._lock:
            # BUG: appending to an unbounded list -- this is the memory leak
            self._processed_events.append(result)
            self._total_processed += 1

        return result

    def process_batch(self, events: list) -> list:
        """Process a batch of {etype} events."""
        return [self.process(e) for e in events]

    def get_recent(self, n: int = 10) -> list:
        """Return the most recent n processed events."""
        with self._lock:
            return list(self._processed_events[-n:])

    def stats(self) -> dict:
        """Return processing statistics."""
        uptime = time.time() - self._start_time
        with self._lock:
            buffered = len(self._processed_events)
        return {{
            "total_processed": self._total_processed,
            "error_count": self._error_count,
            "buffered_events": buffered,
            "uptime_seconds": round(uptime, 2),
        }}

    def clear_history(self) -> None:
        """Clear the event history buffer."""
        with self._lock:
            self._processed_events.clear()
'''.format(klass=processor_class, desc=event_desc, etype=event_type)


def _cache_manager_py(cache_type, cache_class, cache_item_desc, cache_max_mb):
    return '''\
"""
{klass} -- LRU cache for {desc}.

EXPECTED GROWTH (not a bug): This cache grows until it reaches max_size.
Once full, it evicts the least-recently-used entry before adding a new one.
This behaviour is intentional and documented in ARCHITECTURE.md.

Do NOT modify this file.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Optional


class {klass}:
    """
    LRU cache for {desc}.

    Memory grows linearly until max_size is reached (expected by design).
    After max_size, old entries are evicted and memory stays bounded.
    The growth phase is normal startup behaviour, not a leak.
    """

    def __init__(self, max_size: int = 10000):
        self._lock = threading.RLock()
        self._cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item, moving it to the front (most-recently-used)."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        """Store an item, evicting the LRU entry if at capacity."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
                return
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._evictions += 1
            self._cache[key] = value

    def delete(self, key: str) -> bool:
        """Remove an item from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def size(self) -> int:
        """Return the current number of cached items."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {{
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(hit_rate, 4),
                "expected_max_mb": {cmax},
            }}
'''.format(klass=cache_class, desc=cache_item_desc, cmax=cache_max_mb)


def _test_helper_py(helper_name, helper_class, mock_type):
    return '''\
"""
{klass} -- test infrastructure for unit tests.

TEST ARTIFACT (not a production issue): This module accumulates {mock}
at module level during test collection and execution. Because Python imports
are cached, the module-level list persists for the lifetime of the test runner.

This only runs in CI environments with an active pytest session.
In production, this module is never imported, so it has zero memory impact.

Do NOT modify this file.
"""
from __future__ import annotations

import threading
from typing import Any, List, Optional


# Module-level accumulation -- only relevant during test runs (CI only)
# This is a test artifact, not a production memory leak.
_ALL_INSTANCES: List["{klass}"] = []
_instance_lock = threading.Lock()


class {klass}:
    """
    Mock {mock} for use in unit tests.

    Instances are tracked at module level to support test teardown assertions
    (e.g., verifying all mocks were cleaned up). This is a known test pattern
    and is NOT a production memory concern.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._calls: list = []
        self._responses: dict = {{}}
        self._closed = False

        # Register this instance for test teardown tracking
        with _instance_lock:
            _ALL_INSTANCES.append(self)

    def configure_response(self, method: str, response: Any) -> None:
        """Configure a mock response for a given method."""
        self._responses[method] = response

    def call(self, method: str, *args, **kwargs) -> Any:
        """Record a call and return the configured mock response."""
        if self._closed:
            raise RuntimeError(self.name + " is closed")
        record = {{"method": method, "args": args, "kwargs": kwargs}}
        self._calls.append(record)
        return self._responses.get(method, {{"status": "ok"}})

    def call_count(self, method: Optional[str] = None) -> int:
        """Return number of calls, optionally filtered by method."""
        if method is None:
            return len(self._calls)
        return sum(1 for c in self._calls if c["method"] == method)

    def close(self) -> None:
        """Mark the mock as closed."""
        self._closed = True

    @classmethod
    def reset_all(cls) -> None:
        """Reset all tracked instances (call in test teardown)."""
        with _instance_lock:
            for inst in _ALL_INSTANCES:
                inst._calls.clear()
                inst._closed = False

    @classmethod
    def instance_count(cls) -> int:
        """Return total number of instances created (for teardown assertions)."""
        with _instance_lock:
            return len(_ALL_INSTANCES)
'''.format(klass=helper_class, mock=mock_type)


def _metrics_json(
    processor_class, cache_class, helper_class,
    leak_mb_hr, cache_max_mb, test_accum_mb,
):
    data = {
        "measurement_period": "2024-11-20T00:00:00Z to 2024-11-20T12:00:00Z",
        "interval_minutes": 60,
        "components": {
            processor_class: {
                "description": "Memory used by event processing buffer",
                "growth_pattern": "linear_unbounded",
                "samples_mb": [
                    round(leak_mb_hr * i * 0.85 + 12, 1)
                    for i in range(13)
                ],
                "growth_rate_mb_per_hour": leak_mb_hr,
                "note": "Unbounded growth -- no plateau observed",
            },
            cache_class: {
                "description": "Memory used by LRU cache entries",
                "growth_pattern": "bounded_plateau",
                "samples_mb": [
                    round(min(cache_max_mb, cache_max_mb * i / 6), 1)
                    for i in range(13)
                ],
                "growth_rate_mb_per_hour": "~{} until plateau".format(cache_max_mb // 6),
                "plateau_mb": cache_max_mb,
                "note": "Plateaus at {}MB as documented in ARCHITECTURE.md".format(cache_max_mb),
            },
            helper_class: {
                "description": "Memory from test mock objects (CI only)",
                "growth_pattern": "test_run_only",
                "samples_mb": [0] * 13,
                "ci_run_peak_mb": test_accum_mb,
                "note": "Zero in production; accumulates to ~{}MB during test suite".format(test_accum_mb),
            },
        },
        "oom_kill_timestamp": "2024-11-20T11:47:23Z",
        "oom_kill_rss_mb": leak_mb_hr * 12 + cache_max_mb + 50,
    }
    return json.dumps(data, indent=2)


def _incident_ticket(
    processor_class, cache_class, helper_class,
    leak_mb_hr, cache_max_mb, test_accum_mb,
):
    return """\
# Incident Ticket: OOM Kill -- Memory Leak Investigation

**Ticket ID**: INC-MEM-0042
**Severity**: P1
**Reported**: 2024-11-20T12:05:00Z
**Status**: Active

## Timeline

- **00:00** UTC -- Service deployed, RSS at ~{base}MB (normal startup)
- **02:00** UTC -- RSS at ~{t2}MB; on-call notes slow growth
- **06:00** UTC -- RSS at ~{t6}MB; memory alert fires
- **11:47** UTC -- OOM kill. Process terminated. All in-flight requests lost.
- **12:05** UTC -- Ticket opened. On-call begins investigation.

## Observed Memory Growth

Three components show memory growth in `metrics.json`:
1. **{proc}**: {leak} MB/hour, unbounded
2. **{cache}**: grows to ~{cmax}MB then plateaus
3. **{helper}**: appears in CI metrics (~{taccum}MB), zero in production

## Investigation Notes

The total RSS growth matches {proc} growth rate + constant {cache} plateau.
This suggests {proc} is the primary contributor to the OOM condition.

However, both {cache} and {helper} also show non-zero memory figures.
Triage required to classify each component before making changes.

See `ARCHITECTURE.md` for documented memory budgets and design decisions.
See `metrics.json` for time-series data.

## Action Required

1. Classify each component: real leak, expected growth, or test artifact
2. Fix only the real leak
3. Do not break documented cache behavior (see ARCHITECTURE.md)
4. Write INCIDENT_REPORT.md with triage findings
""".format(
        proc=processor_class, cache=cache_class, helper=helper_class,
        leak=leak_mb_hr, cmax=cache_max_mb, taccum=test_accum_mb,
        base=cache_max_mb + 80,
        t2=cache_max_mb + leak_mb_hr * 2 + 80,
        t6=cache_max_mb + leak_mb_hr * 6 + 80,
    )


def _architecture_md(cache_class, cache_type, cache_item_desc, cache_max_mb):
    return """\
# Architecture Document: Memory Subsystem

## {klass} -- Design Rationale

The `{klass}` implements an LRU cache for {desc}. Its memory
growth during startup is **intentional and expected**.

### Memory Budget

| Phase | Expected RSS | Notes |
|-------|-------------|-------|
| Cold start | ~80MB | No cached {ctype} entries |
| Warm (50% capacity) | ~{half}MB | Normal operating range |
| Hot (100% capacity) | ~{full}MB | Maximum; entries evicted after this |

The cache is capped at `max_size` entries. Once the cap is reached, the least-recently-used
entry is evicted before a new entry is added. Memory usage is therefore **bounded**
and will not grow beyond ~{cmax}MB under sustained load.

### Why Not a Leak

A memory leak is characterized by **unbounded** growth. The {klass} grows
to a maximum of {cmax}MB and then remains stable. This is visible in the
metrics plateau. Do not treat this as a defect.

### Configuration

To reduce the memory footprint, decrease `max_size` in the constructor. This will
increase cache misses and reduce performance. The current value was chosen based on
load testing at P99 traffic levels.

## Event Processor Subsystem

The event processors use an in-memory buffer for recent event history. The buffer
size must be bounded to prevent unbounded memory growth during extended operation.
Use `collections.deque(maxlen=N)` where N reflects the required history window.

## Test Infrastructure

Test helpers (`test_helper.py` and related modules) track mock object instances at
module level. This is a standard Python testing pattern. These modules are never
imported in production deployments and have no production memory footprint.
""".format(
        klass=cache_class, desc=cache_item_desc, ctype=cache_type,
        cmax=cache_max_mb,
        half=cache_max_mb // 2 + 80,
        full=cache_max_mb + 80,
    )


def _tests_py(
    event_type, processor_class,
    cache_type, cache_class,
    helper_name, helper_class, mock_type,
    maxlen,
):
    return '''\
"""Tests for event_processor, cache_manager, and test_helper components."""
import collections
import pytest

from event_processor import {proc}
from cache_manager import {cache}
from test_helper import {helper}


# -- {proc} tests ---------------------------------------------------------

class TestEventProcessor:

    def test_process_single_event(self):
        proc = {proc}()
        result = proc.process({{"id": "e1", "data": "payload"}})
        assert result["status"] == "processed"
        assert result["id"] == "e1"

    def test_process_batch(self):
        proc = {proc}()
        events = [{{"id": "e{{}}".format(i), "data": i}} for i in range(5)]
        results = proc.process_batch(events)
        assert len(results) == 5
        assert all(r["status"] == "processed" for r in results)

    def test_get_recent(self):
        proc = {proc}()
        for i in range(20):
            proc.process({{"id": "e{{}}".format(i), "data": i}})
        recent = proc.get_recent(5)
        assert len(recent) == 5

    def test_stats(self):
        proc = {proc}()
        proc.process({{"id": "e1", "data": "x"}})
        stats = proc.stats()
        assert stats["total_processed"] == 1
        assert "uptime_seconds" in stats

    def test_invalid_event_raises(self):
        proc = {proc}()
        with pytest.raises((ValueError, TypeError)):
            proc.process("not_a_dict")

    def test_buffer_is_bounded(self):
        """After fix: internal buffer must be bounded (deque with maxlen)."""
        proc = {proc}()
        for i in range({maxlen} + 100):
            proc.process({{"id": "e{{}}".format(i), "data": i}})
        stats = proc.stats()
        assert stats["buffered_events"] <= {maxlen}, (
            "Buffer must be bounded to {maxlen}, got {{}}".format(stats["buffered_events"])
        )

    def test_internal_buffer_is_deque(self):
        """After fix: internal store must be a deque, not a list."""
        proc = {proc}()
        assert isinstance(proc._processed_events, collections.deque), (
            "Fix required: replace list with collections.deque(maxlen={maxlen})"
        )
        assert proc._processed_events.maxlen == {maxlen}, (
            "deque maxlen must be {maxlen}"
        )

    def test_clear_history(self):
        proc = {proc}()
        proc.process({{"id": "e1", "data": 1}})
        proc.clear_history()
        assert proc.get_recent(10) == []


# -- {cache} tests --------------------------------------------------------

class TestCacheManager:

    def test_put_and_get(self):
        cache = {cache}(max_size=100)
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_miss_returns_none(self):
        cache = {cache}(max_size=100)
        assert cache.get("nonexistent") is None

    def test_eviction_at_capacity(self):
        cache = {cache}(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # should evict "a" (LRU)
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_lru_order(self):
        cache = {cache}(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")       # touch "a" -> "b" becomes LRU
        cache.put("c", 3)    # should evict "b"
        assert cache.get("b") is None
        assert cache.get("a") == 1

    def test_stats(self):
        cache = {cache}(max_size=100)
        cache.put("x", 42)
        cache.get("x")
        cache.get("missing")
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_delete(self):
        cache = {cache}(max_size=100)
        cache.put("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None


# -- {helper} tests -------------------------------------------------------

class TestHelper:

    def test_call_records(self):
        mock = {helper}("test")
        mock.configure_response("read", {{"data": [1, 2, 3]}})
        result = mock.call("read")
        assert result == {{"data": [1, 2, 3]}}
        assert mock.call_count("read") == 1

    def test_call_count_all(self):
        mock = {helper}("test2")
        mock.call("read")
        mock.call("write")
        assert mock.call_count() == 2

    def test_closed_raises(self):
        mock = {helper}("test3")
        mock.close()
        with pytest.raises(RuntimeError):
            mock.call("any")

    def test_reset_all(self):
        mock = {helper}("test4")
        mock.call("op")
        {helper}.reset_all()
        assert mock.call_count() == 0

    def test_instance_count(self):
        before = {helper}.instance_count()
        {helper}("counter_test")
        assert {helper}.instance_count() == before + 1
'''.format(
        proc=processor_class, cache=cache_class, helper=helper_class,
        maxlen=maxlen,
    )
