"""
Parameterized generator for TEST6: Property-Based Testing.

Each seed produces:
- A data structure library (datastructs.py) with SortedList, BoundedQueue, LRUCache
- Each data structure has 3-4 invariants that must always hold
- Subtle bugs seeded that only property-based / Hypothesis tests catch reliably
- A spec_invariants.txt listing 10 invariants
- An empty tests/test_properties.py for the agent to fill in

Seed variation:
  - Different class/method names for data structures
  - Different capacity limits and thresholds
  - Which invariants have bugs (always 3 bugs out of 10 invariants)

TNI driver (Pattern A + B):
  - Brief: "Write property-based tests using Hypothesis for the data structure library"
  - Spec: Full invariant list with expected behaviors and edge case hints
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized pools ───────────────────────────────────────────────

SORTED_LIST_NAMES = ["SortedList", "OrderedCollection", "SortedArray", "RankedList"]
BOUNDED_QUEUE_NAMES = ["BoundedQueue", "CapacityQueue", "LimitedQueue", "FixedQueue"]
LRU_CACHE_NAMES = ["LRUCache", "EvictingCache", "BoundedCache", "RecentCache"]

CAPACITY_VALUES = [5, 8, 10, 16, 20]

# Bug configurations: each tuple = (bug_location, description)
# We always pick 3 per seed from this pool of 6
BUG_POOL = [
    ("sorted_insert_dup", "SortedList.insert fails to maintain order with duplicate keys"),
    ("sorted_remove_last", "SortedList.remove breaks when removing the last element"),
    ("queue_full_check", "BoundedQueue uses > instead of >= for capacity check (off-by-one)"),
    ("queue_dequeue_empty", "BoundedQueue.dequeue doesn't raise on empty queue"),
    ("lru_update_order", "LRUCache.get doesn't move item to most-recent on access"),
    ("lru_size_on_update", "LRUCache.put on existing key increments size instead of updating"),
]


class Generator(TaskGenerator):
    task_id = "TEST6_property_based"
    domain = "testing"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick names
        sl_name = SORTED_LIST_NAMES[seed % len(SORTED_LIST_NAMES)]
        bq_name = BOUNDED_QUEUE_NAMES[seed % len(BOUNDED_QUEUE_NAMES)]
        lru_name = LRU_CACHE_NAMES[seed % len(LRU_CACHE_NAMES)]

        # Pick capacities
        bq_cap = CAPACITY_VALUES[rng.randint(0, len(CAPACITY_VALUES) - 1)]
        lru_cap = CAPACITY_VALUES[rng.randint(0, len(CAPACITY_VALUES) - 1)]

        # Pick 3 bugs from pool
        bug_indices = rng.sample(list(range(len(BUG_POOL))), 3)
        active_bugs = [BUG_POOL[i] for i in bug_indices]
        active_bug_ids = {b[0] for b in active_bugs}

        workspace_files = self._make_workspace(
            sl_name, bq_name, lru_name, bq_cap, lru_cap, active_bug_ids
        )

        expected = {
            "seed": seed,
            "sorted_list_name": sl_name,
            "bounded_queue_name": bq_name,
            "lru_cache_name": lru_name,
            "bq_capacity": bq_cap,
            "lru_capacity": lru_cap,
            "active_bugs": [{"id": b[0], "desc": b[1]} for b in active_bugs],
            "invariant_count": 10,
            "bug_count": 3,
        }

        spec_md = self._generate_spec(sl_name, bq_name, lru_name, bq_cap, lru_cap)
        brief_md = self._generate_brief(sl_name, bq_name, lru_name)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_workspace(
        self,
        sl_name: str,
        bq_name: str,
        lru_name: str,
        bq_cap: int,
        lru_cap: int,
        active_bugs: set,
    ) -> dict:
        files = {}

        files["datastructs.py"] = self._gen_datastructs(
            sl_name, bq_name, lru_name, bq_cap, lru_cap, active_bugs
        )
        files["spec_invariants.txt"] = self._gen_invariants_txt(
            sl_name, bq_name, lru_name, bq_cap, lru_cap
        )
        files["tests/__init__.py"] = ""
        files["tests/test_properties.py"] = self._gen_test_skeleton(
            sl_name, bq_name, lru_name
        )
        files["requirements.txt"] = "hypothesis>=6.82.0\npytest>=7.0.0\n"

        return files

    def _gen_datastructs(
        self,
        sl_name: str,
        bq_name: str,
        lru_name: str,
        bq_cap: int,
        lru_cap: int,
        bugs: set,
    ) -> str:
        # SortedList insert: bug = doesn't handle duplicates properly
        sl_insert_body = """        if not self._items:
            self._items.append(value)
            return
        lo, hi = 0, len(self._items)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._items[mid] < value:
                lo = mid + 1
            else:
                hi = mid
        self._items.insert(lo, value)"""

        if "sorted_insert_dup" in bugs:
            # Bug: uses <= instead of <, causing duplicates to land in wrong position
            sl_insert_body = """        if not self._items:
            self._items.append(value)
            return
        lo, hi = 0, len(self._items)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._items[mid] <= value:
                lo = mid + 1
            else:
                hi = mid
        self._items.insert(lo, value)"""

        # SortedList remove: bug = breaks on last element
        sl_remove_body = """        lo, hi = 0, len(self._items)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._items[mid] < value:
                lo = mid + 1
            elif self._items[mid] > value:
                hi = mid
            else:
                self._items.pop(mid)
                return True
        raise ValueError(f"{value} not found")"""

        if "sorted_remove_last" in bugs:
            # Bug: off-by-one when removing last element
            sl_remove_body = """        lo, hi = 0, len(self._items) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self._items[mid] < value:
                lo = mid + 1
            elif self._items[mid] > value:
                hi = mid
            else:
                self._items.pop(mid)
                return True
        if lo < len(self._items) and self._items[lo] == value:
            self._items.pop(lo)
            return True
        raise ValueError(f"{value} not found")"""

        # BoundedQueue full check
        bq_enqueue_guard = f"if self._size >= self._capacity:"
        if "queue_full_check" in bugs:
            bq_enqueue_guard = f"if self._size > self._capacity:"

        # BoundedQueue dequeue empty
        bq_dequeue_guard = """        if self._size == 0:
            raise IndexError("dequeue from empty queue")"""
        if "queue_dequeue_empty" in bugs:
            bq_dequeue_guard = """        if False:
            raise IndexError("dequeue from empty queue")"""

        # LRU get order
        lru_get_move = """            self._order.remove(key)
            self._order.append(key)"""
        if "lru_update_order" in bugs:
            # Bug: doesn't move to end on access
            lru_get_move = """            pass  # accessed"""

        # LRU put size on update
        lru_put_existing = """            self._store[key] = value
            self._order.remove(key)
            self._order.append(key)"""
        if "lru_size_on_update" in bugs:
            # Bug: increments size even on existing key update
            lru_put_existing = """            self._store[key] = value
            self._order.remove(key)
            self._order.append(key)
            self._size += 1"""

        return f'''"""Data structure library with SortedList, BoundedQueue, and LRUCache."""


class {sl_name}:
    """A list that maintains sorted order after every insertion."""

    def __init__(self):
        self._items = []

    def insert(self, value):
        """Insert value maintaining sorted order."""
{sl_insert_body}

    def remove(self, value):
        """Remove first occurrence of value. Raises ValueError if not found."""
{sl_remove_body}

    def contains(self, value):
        """Check if value is in the list using binary search."""
        lo, hi = 0, len(self._items)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._items[mid] < value:
                lo = mid + 1
            elif self._items[mid] > value:
                hi = mid
            else:
                return True
        return False

    def to_list(self):
        """Return a copy of internal list."""
        return list(self._items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, idx):
        return self._items[idx]

    def __iter__(self):
        return iter(self._items)


class {bq_name}:
    """A queue with a fixed maximum capacity."""

    def __init__(self, capacity={bq_cap}):
        self._capacity = capacity
        self._items = []
        self._size = 0

    def enqueue(self, value):
        """Add value to the back. Raises OverflowError if full."""
        {bq_enqueue_guard}
            raise OverflowError("queue is full")
        self._items.append(value)
        self._size += 1

    def dequeue(self):
        """Remove and return front element. Raises IndexError if empty."""
{bq_dequeue_guard}
        self._size -= 1
        return self._items.pop(0)

    def peek(self):
        """Return front element without removing. Raises IndexError if empty."""
        if self._size == 0:
            raise IndexError("peek from empty queue")
        return self._items[0]

    @property
    def capacity(self):
        return self._capacity

    @property
    def size(self):
        return self._size

    @property
    def is_full(self):
        return self._size >= self._capacity

    @property
    def is_empty(self):
        return self._size == 0

    def to_list(self):
        return list(self._items)

    def __len__(self):
        return self._size


class {lru_name}:
    """Least-Recently-Used cache with a fixed capacity."""

    def __init__(self, capacity={lru_cap}):
        self._capacity = capacity
        self._store = {{}}
        self._order = []  # oldest first, newest last
        self._size = 0

    def get(self, key):
        """Get value by key. Returns None if not found. Marks as recently used."""
        if key in self._store:
{lru_get_move}
            return self._store[key]
        return None

    def put(self, key, value):
        """Insert or update key-value pair. Evicts LRU item if at capacity."""
        if key in self._store:
{lru_put_existing}
            return
        if self._size >= self._capacity:
            evicted = self._order.pop(0)
            del self._store[evicted]
            self._size -= 1
        self._store[key] = value
        self._order.append(key)
        self._size += 1

    def delete(self, key):
        """Remove key from cache. Returns True if found, False otherwise."""
        if key in self._store:
            del self._store[key]
            self._order.remove(key)
            self._size -= 1
            return True
        return False

    @property
    def size(self):
        return self._size

    @property
    def capacity(self):
        return self._capacity

    def keys(self):
        """Return keys in order from least to most recently used."""
        return list(self._order)

    def __contains__(self, key):
        return key in self._store

    def __len__(self):
        return self._size
'''

    def _gen_invariants_txt(
        self,
        sl_name: str,
        bq_name: str,
        lru_name: str,
        bq_cap: int,
        lru_cap: int,
    ) -> str:
        return f"""# Invariants for Data Structure Library
# Each invariant MUST be tested with Hypothesis property-based tests.

## {sl_name} Invariants
INV-1: After any sequence of insert() calls, to_list() is always sorted in non-decreasing order.
INV-2: After inserting N distinct values, len() == N. After inserting K duplicates, len() == N + K.
INV-3: For every value v in to_list(), contains(v) returns True.
INV-4: After remove(v), v no longer appears at its original position (if duplicates exist, only one copy is removed).

## {bq_name} Invariants (capacity={bq_cap})
INV-5: size never exceeds capacity after any sequence of enqueue/dequeue operations.
INV-6: dequeue returns elements in FIFO order (first enqueued = first dequeued).
INV-7: enqueue on a full queue (size == capacity) raises OverflowError, size unchanged.

## {lru_name} Invariants (capacity={lru_cap})
INV-8: size never exceeds capacity after any sequence of put/get/delete operations.
INV-9: After put(k, v) then get(k), the returned value is v (cache consistency).
INV-10: When cache is full and a new key is inserted, the least-recently-used key is evicted (the key that was neither put nor get'd most recently).
"""

    def _gen_test_skeleton(self, sl_name: str, bq_name: str, lru_name: str) -> str:
        return f'''"""Property-based tests for datastructs.py using Hypothesis.

Write Hypothesis property-based tests that verify all 10 invariants
listed in spec_invariants.txt. Your tests should find the seeded bugs.

Run with: python -m pytest tests/test_properties.py -v
"""
import pytest
from hypothesis import given, settings, assume
import hypothesis.strategies as st

from datastructs import {sl_name}, {bq_name}, {lru_name}

# TODO: Write property-based tests for all 10 invariants
# Use @given decorators with appropriate Hypothesis strategies.
# Each invariant should have at least one corresponding test.
'''

    def _generate_spec(
        self,
        sl_name: str,
        bq_name: str,
        lru_name: str,
        bq_cap: int,
        lru_cap: int,
    ) -> str:
        return f"""# TEST6: Property-Based Testing with Hypothesis

## Goal
Write Hypothesis property-based tests that verify 10 invariants for a data
structure library (`datastructs.py`) containing {sl_name}, {bq_name}, and {lru_name}.

## Data Structures

### {sl_name}
A sorted list that maintains non-decreasing order after every insertion.
- `insert(value)`: insert maintaining sorted order
- `remove(value)`: remove first occurrence, raises ValueError if not found
- `contains(value)`: binary search lookup
- `to_list()`: returns a copy of internal list
- `len()`: number of elements

### {bq_name} (capacity={bq_cap})
A bounded FIFO queue.
- `enqueue(value)`: add to back, raises OverflowError if full
- `dequeue()`: remove from front, raises IndexError if empty
- `peek()`: view front without removing
- Properties: `size`, `capacity`, `is_full`, `is_empty`

### {lru_name} (capacity={lru_cap})
A Least-Recently-Used cache.
- `put(key, value)`: insert or update. Evicts LRU when at capacity
- `get(key)`: returns value or None. Marks as recently used
- `delete(key)`: remove key, returns True/False
- `keys()`: return keys from least to most recently used
- Properties: `size`, `capacity`

## 10 Invariants (from spec_invariants.txt)

1. {sl_name}: `to_list()` always sorted after any insert sequence
2. {sl_name}: `len()` tracks inserts/removals correctly including duplicates
3. {sl_name}: `contains(v)` returns True for every v in `to_list()`
4. {sl_name}: `remove(v)` removes exactly one occurrence
5. {bq_name}: `size` never exceeds `capacity`
6. {bq_name}: FIFO ordering preserved
7. {bq_name}: `enqueue` on full queue raises OverflowError, size unchanged
8. {lru_name}: `size` never exceeds `capacity`
9. {lru_name}: `get(k)` returns value after `put(k, v)` (cache consistency)
10. {lru_name}: LRU eviction policy correct (least recently used key evicted)

## Known Issue
Some implementations have subtle bugs that only emerge under random testing
with edge cases (duplicates, capacity boundaries, access patterns). Your
property tests should reliably detect these issues.

## Deliverables
- `tests/test_properties.py` with Hypothesis `@given` property tests
- At least 10 test functions (one per invariant)
- Tests must use Hypothesis strategies (`st.integers()`, `st.lists()`, `st.text()`, etc.)
- Run: `python -m pytest tests/test_properties.py -v`
- Verifier writes `attestation.json` with verdict

## Grading
- Each invariant checked for a corresponding test function
- Tests run on the provided (buggy) code: bug-revealing tests that fail count as valid
- Tests also run on a fixed version: tests must PASS on correct implementations
"""

    def _generate_brief(self, sl_name: str, bq_name: str, lru_name: str) -> str:
        return f"""# TEST6: Property-Based Testing (Brief)

Write Hypothesis property-based tests for the data structure library in `datastructs.py`.

The library contains three classes: `{sl_name}`, `{bq_name}`, and `{lru_name}`.
See `spec_invariants.txt` for the 10 invariants that must be tested.

Write your tests in `tests/test_properties.py` using `@given` decorators.

Install dependencies: `pip install -r requirements.txt`
Run: `python -m pytest tests/test_properties.py -v`
"""
