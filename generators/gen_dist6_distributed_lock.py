"""
Parameterized generator for DIST6: Distributed Lock.

Each seed produces a Redis-style distributed lock implementation with 4 bugs:
1. No fencing token
2. Stale TTL calculation
3. Fixed retry delay (no backoff/jitter)
4. Release without ownership check
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed pools ────────────────────────────────────────────────────────────

LOCK_KEY_PREFIXES = [
    "resource", "order", "payment", "inventory",
    "account", "session", "job", "task",
]

NODE_ID_SETS = [
    ["node-alpha", "node-beta", "node-gamma"],
    ["worker-1", "worker-2", "worker-3"],
    ["svc-east", "svc-west", "svc-central"],
    ["replica-a", "replica-b", "replica-c"],
    ["pod-x1", "pod-x2", "pod-x3"],
    ["inst-01", "inst-02", "inst-03"],
]

TTL_VALUES = [5, 10, 15, 20, 30]  # seconds

RETRY_COUNTS = [3, 5, 8, 10]

RETRY_DELAYS = [0.05, 0.1, 0.2, 0.5]  # seconds (fixed — the bug)

APP_NAMES = [
    "lock_manager", "distributed_coordinator", "resource_guard",
    "consensus_lock", "cluster_mutex", "sync_service",
    "lock_service", "resource_broker",
]


class Generator(TaskGenerator):
    task_id = "DIST6_distributed_lock"
    domain = "Distributed"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 8

        lock_prefix = LOCK_KEY_PREFIXES[idx]
        node_ids = NODE_ID_SETS[seed % len(NODE_ID_SETS)]
        ttl = TTL_VALUES[seed % len(TTL_VALUES)]
        retry_count = RETRY_COUNTS[seed % len(RETRY_COUNTS)]
        retry_delay = RETRY_DELAYS[seed % len(RETRY_DELAYS)]
        app_name = APP_NAMES[idx]

        workspace_files = self._make_workspace(
            lock_prefix=lock_prefix,
            node_ids=node_ids,
            ttl=ttl,
            retry_count=retry_count,
            retry_delay=retry_delay,
            app_name=app_name,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "DIST6_distributed_lock")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="DIST6_distributed_lock",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs": [
                    "no_fencing_token",
                    "stale_ttl",
                    "fixed_retry_delay",
                    "unchecked_release",
                ],
                "lock_prefix": lock_prefix,
                "node_ids": node_ids,
                "ttl": ttl,
                "retry_count": retry_count,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Distributed"},
        )

    def _make_workspace(
        self,
        lock_prefix: str,
        node_ids: list[str],
        ttl: int,
        retry_count: int,
        retry_delay: float,
        app_name: str,
    ) -> dict:
        files = {}

        node_ids_repr = repr(node_ids)

        # ── config.py ────────────────────────────────────────────────────
        files["config.py"] = f"""\
\"\"\"Configuration for {app_name}.\"\"\"

LOCK_KEY_PREFIX = "{lock_prefix}"
DEFAULT_TTL = {ttl}  # seconds
MAX_RETRIES = {retry_count}
RETRY_DELAY = {retry_delay}  # seconds (fixed — should use backoff)
NODE_IDS = {node_ids_repr}
"""

        # ── mock_redis.py ────────────────────────────────────────────────
        files["mock_redis.py"] = f"""\
\"\"\"
Simulated Redis backend for {app_name}.

Provides SET NX, GET, DEL, and TTL operations with in-memory storage.
Thread-safe for testing concurrent lock operations.
\"\"\"
import time
import threading


class MockRedis:
    \"\"\"In-memory Redis-like store for testing distributed lock logic.\"\"\"

    def __init__(self):
        self._store: dict = {{}}
        self._ttls: dict = {{}}
        self._lock = threading.Lock()
        self._fencing_counter = 0

    def set_nx(self, key: str, value: str, ttl: float = None) -> bool:
        \"\"\"SET key value NX — only set if key does not exist.\"\"\"
        with self._lock:
            now = time.time()
            # Clean up expired keys
            if key in self._ttls and self._ttls[key] < now:
                del self._store[key]
                del self._ttls[key]

            if key in self._store:
                return False

            self._store[key] = value
            if ttl is not None:
                self._ttls[key] = now + ttl
            return True

    def get(self, key: str) -> str | None:
        \"\"\"GET key — return value or None.\"\"\"
        with self._lock:
            now = time.time()
            if key in self._ttls and self._ttls[key] < now:
                del self._store[key]
                del self._ttls[key]
                return None
            return self._store.get(key)

    def delete(self, key: str) -> bool:
        \"\"\"DEL key — return True if key was deleted.\"\"\"
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._ttls.pop(key, None)
                return True
            return False

    def ttl(self, key: str) -> float:
        \"\"\"TTL key — return remaining TTL in seconds, -1 if no TTL, -2 if not found.\"\"\"
        with self._lock:
            if key not in self._store:
                return -2
            if key not in self._ttls:
                return -1
            remaining = self._ttls[key] - time.time()
            return max(0, remaining)

    def next_fencing_token(self) -> int:
        \"\"\"Generate a monotonically increasing fencing token.\"\"\"
        with self._lock:
            self._fencing_counter += 1
            return self._fencing_counter

    def exists(self, key: str) -> bool:
        \"\"\"Check if key exists (respects TTL).\"\"\"
        with self._lock:
            now = time.time()
            if key in self._ttls and self._ttls[key] < now:
                del self._store[key]
                del self._ttls[key]
                return False
            return key in self._store
"""

        # ── distributed_lock.py (4 bugs) ────────────────────────────────
        files["distributed_lock.py"] = f"""\
\"\"\"
Distributed lock implementation for {app_name}.

Uses a Redis-like backend (MockRedis) for lock storage.
Contains 4 correctness bugs — see spec.md for details.
\"\"\"
import time
from config import DEFAULT_TTL, MAX_RETRIES, RETRY_DELAY, LOCK_KEY_PREFIX


class DistributedLock:
    \"\"\"
    Redis-style distributed lock with acquire/release/extend.

    BUG 1: acquire() returns bool, not a fencing token.
    BUG 2: TTL calculated before lock is set (stale after network delay).
    BUG 3: Fixed retry delay without backoff or jitter.
    BUG 4: release() doesn't check lock ownership.
    \"\"\"

    def __init__(self, resource: str, backend, node_id: str = "default",
                 ttl: float = DEFAULT_TTL, max_retries: int = MAX_RETRIES):
        self.resource = resource
        self.backend = backend
        self.node_id = node_id
        self.ttl = ttl
        self.max_retries = max_retries
        self._lock_key = f"{{LOCK_KEY_PREFIX}}:lock:{{resource}}"

    def acquire(self):
        \"\"\"
        Attempt to acquire the distributed lock.

        BUG 1: Returns True/False instead of a fencing token.
        BUG 2: Calculates TTL before the SET NX call.
        BUG 3: Uses fixed retry delay.

        Should return: fencing token (int) on success, None on failure.
        Currently returns: True on success, False on failure.
        \"\"\"
        # BUG 2: TTL is captured here, but the actual SET happens after
        # potential network delay — the lock has less TTL than expected
        # TODO: capture time after SET, not before
        start_time = time.time()
        expire_at = start_time + self.ttl

        for attempt in range(self.max_retries + 1):
            # Try to acquire with SET NX
            acquired = self.backend.set_nx(self._lock_key, self.node_id, ttl=self.ttl)

            if acquired:
                # BUG 1: returns bool instead of fencing token
                # TODO: return a monotonically increasing fencing token
                return True

            if attempt < self.max_retries:
                # BUG 3: fixed delay — should use exponential backoff + jitter
                # TODO: replace with exponential backoff and random jitter
                time.sleep(RETRY_DELAY)

        return False

    def release(self):
        \"\"\"
        Release the distributed lock.

        BUG 4: Does not check if the caller is the current lock holder.
        Any client can release any other client's lock.
        \"\"\"
        # BUG 4: should check that self.node_id matches the stored owner
        # TODO: only delete if we are the owner
        return self.backend.delete(self._lock_key)

    def extend(self, additional_ttl: float = None):
        \"\"\"Extend the lock TTL (only if we hold it).\"\"\"
        if additional_ttl is None:
            additional_ttl = self.ttl
        current = self.backend.get(self._lock_key)
        if current == self.node_id:
            # Re-set with extended TTL
            self.backend.delete(self._lock_key)
            return self.backend.set_nx(self._lock_key, self.node_id, ttl=additional_ttl)
        return False

    def is_locked(self) -> bool:
        \"\"\"Check if the resource is currently locked.\"\"\"
        return self.backend.exists(self._lock_key)
"""

        # ── tests/__init__.py ────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_lock.py ───────────────────────────────────────────
        files["tests/test_lock.py"] = f"""\
\"\"\"
Tests for distributed lock.

These tests verify basic acquire/release behavior but miss the
edge-case bugs (fencing, TTL staleness, backoff, ownership).
\"\"\"
import pytest
from distributed_lock import DistributedLock
from mock_redis import MockRedis


@pytest.fixture
def backend():
    return MockRedis()


def test_acquire_and_release(backend):
    lock = DistributedLock("res-1", backend, node_id="{node_ids[0]}")
    result = lock.acquire()
    assert result  # Should be truthy (token or True)
    lock.release()
    assert not lock.is_locked()


def test_lock_prevents_double_acquire(backend):
    lock_a = DistributedLock("res-2", backend, node_id="{node_ids[0]}")
    lock_b = DistributedLock("res-2", backend, node_id="{node_ids[1]}", max_retries=0)
    token_a = lock_a.acquire()
    assert token_a  # A acquires
    token_b = lock_b.acquire()
    assert not token_b  # B fails (lock held)
    lock_a.release()


def test_lock_released_can_be_reacquired(backend):
    lock_a = DistributedLock("res-3", backend, node_id="{node_ids[0]}")
    lock_b = DistributedLock("res-3", backend, node_id="{node_ids[1]}")
    lock_a.acquire()
    lock_a.release()
    token = lock_b.acquire()
    assert token  # B acquires after A releases
    lock_b.release()


def test_extend_lock(backend):
    lock = DistributedLock("res-4", backend, node_id="{node_ids[0]}")
    lock.acquire()
    result = lock.extend(additional_ttl=30)
    assert result
    lock.release()


def test_is_locked(backend):
    lock = DistributedLock("res-5", backend, node_id="{node_ids[0]}")
    assert not lock.is_locked()
    lock.acquire()
    assert lock.is_locked()
    lock.release()
    assert not lock.is_locked()


def test_different_resources_independent(backend):
    lock_a = DistributedLock("res-6a", backend, node_id="{node_ids[0]}")
    lock_b = DistributedLock("res-6b", backend, node_id="{node_ids[1]}")
    assert lock_a.acquire()
    assert lock_b.acquire()  # Different resource, should succeed
    lock_a.release()
    lock_b.release()
"""

        files["requirements.txt"] = "pytest\n"

        return files
