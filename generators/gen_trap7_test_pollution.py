"""
Parameterized generator for TRAP7: Test Pollution vs Real Bugs.

Each seed produces a Python app with 8 failing tests:
  - 5 failures from real bugs in application code
  - 3 failures from test pollution (shared mutable state)

The 3 pollution types are always:
  1. Global registry dict (not cleared between tests)
  2. Class-level cache (shared across test instances)
  3. Module-level counter (not reset between tests)

Seed variation: app domain, function names, bug types, which tests are polluted.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized domain variants ────────────────────────────────────

DOMAINS = ["inventory", "ticketing", "scoring"]

ITEM_NAMES = ["product", "ticket", "entry"]
ITEM_PLURALS = ["products", "tickets", "entries"]

REGISTRY_NAMES = ["_product_registry", "_ticket_registry", "_entry_registry"]
CACHE_NAMES = ["_price_cache", "_seat_cache", "_score_cache"]
COUNTER_NAMES = ["_order_counter", "_booking_counter", "_round_counter"]

# Bug descriptions per domain (5 bugs each)
BUG_SPECS = [
    # inventory domain
    [
        {"module": "pricing", "function": "calculate_discount",
         "bug": "off-by-one: uses > instead of >=",
         "test_input": {"price": 100, "quantity": 10},
         "expected_output": 90.0,
         "buggy_op": "if quantity > 10:", "fixed_op": "if quantity >= 10:"},
        {"module": "stock", "function": "check_availability",
         "bug": "returns True when stock is 0",
         "test_input": {"item_id": "A1", "stock_level": 0},
         "expected_output": False,
         "buggy_op": "return stock_level >= 0", "fixed_op": "return stock_level > 0"},
        {"module": "shipping", "function": "calculate_weight",
         "bug": "forgets to multiply by quantity",
         "test_input": {"unit_weight": 2.5, "quantity": 4},
         "expected_output": 10.0,
         "buggy_op": "return unit_weight", "fixed_op": "return unit_weight * quantity"},
        {"module": "tax", "function": "apply_tax",
         "bug": "adds tax rate instead of multiplying",
         "test_input": {"amount": 100.0, "rate": 0.08},
         "expected_output": 108.0,
         "buggy_op": "return amount + rate", "fixed_op": "return amount * (1 + rate)"},
        {"module": "catalog", "function": "format_sku",
         "bug": "uses wrong separator",
         "test_input": {"category": "EL", "item_id": 42},
         "expected_output": "EL-042",
         "buggy_op": 'return f"{category}_{item_id:03d}"',
         "fixed_op": 'return f"{category}-{item_id:03d}"'},
    ],
    # ticketing domain
    [
        {"module": "pricing", "function": "calculate_discount",
         "bug": "off-by-one: uses > instead of >=",
         "test_input": {"price": 50, "quantity": 5},
         "expected_output": 45.0,
         "buggy_op": "if quantity > 5:", "fixed_op": "if quantity >= 5:"},
        {"module": "seats", "function": "check_availability",
         "bug": "returns True when seats is 0",
         "test_input": {"section": "A", "remaining": 0},
         "expected_output": False,
         "buggy_op": "return remaining >= 0", "fixed_op": "return remaining > 0"},
        {"module": "fees", "function": "calculate_service_fee",
         "bug": "forgets to add base fee",
         "test_input": {"ticket_price": 100.0, "fee_rate": 0.15},
         "expected_output": 17.0,
         "buggy_op": "return ticket_price * fee_rate",
         "fixed_op": "return ticket_price * fee_rate + 2.0"},
        {"module": "tax", "function": "apply_tax",
         "bug": "adds tax rate instead of multiplying",
         "test_input": {"amount": 50.0, "rate": 0.10},
         "expected_output": 55.0,
         "buggy_op": "return amount + rate", "fixed_op": "return amount * (1 + rate)"},
        {"module": "venue", "function": "format_seat_id",
         "bug": "uses wrong separator",
         "test_input": {"section": "B", "row": 3, "seat": 12},
         "expected_output": "B-3-12",
         "buggy_op": 'return f"{section}.{row}.{seat}"',
         "fixed_op": 'return f"{section}-{row}-{seat}"'},
    ],
    # scoring domain
    [
        {"module": "grading", "function": "calculate_curve",
         "bug": "off-by-one: uses > instead of >=",
         "test_input": {"score": 90, "threshold": 90},
         "expected_output": "A",
         "buggy_op": "if score > threshold:", "fixed_op": "if score >= threshold:"},
        {"module": "ranking", "function": "check_eligibility",
         "bug": "returns True when score is 0",
         "test_input": {"player": "P1", "score": 0},
         "expected_output": False,
         "buggy_op": "return score >= 0", "fixed_op": "return score > 0"},
        {"module": "bonus", "function": "calculate_multiplier",
         "bug": "forgets to add base multiplier",
         "test_input": {"streak": 5, "bonus_rate": 0.1},
         "expected_output": 1.5,
         "buggy_op": "return streak * bonus_rate",
         "fixed_op": "return 1.0 + streak * bonus_rate"},
        {"module": "penalty", "function": "apply_penalty",
         "bug": "subtracts rate instead of multiplying",
         "test_input": {"score": 100.0, "penalty_rate": 0.20},
         "expected_output": 80.0,
         "buggy_op": "return score - penalty_rate",
         "fixed_op": "return score * (1 - penalty_rate)"},
        {"module": "leaderboard", "function": "format_rank",
         "bug": "uses wrong separator",
         "test_input": {"division": "Gold", "rank": 7},
         "expected_output": "Gold-007",
         "buggy_op": 'return f"{division}_{rank:03d}"',
         "fixed_op": 'return f"{division}-{rank:03d}"'},
    ],
]


class Generator(TaskGenerator):
    task_id = "TRAP7_test_pollution"
    domain = "Adversarial"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(DOMAINS)

        domain = DOMAINS[idx]
        item_name = ITEM_NAMES[idx]
        item_plural = ITEM_PLURALS[idx]
        registry_name = REGISTRY_NAMES[idx]
        cache_name = CACHE_NAMES[idx]
        counter_name = COUNTER_NAMES[idx]
        bugs = BUG_SPECS[idx]

        workspace_files = self._make_workspace(
            domain=domain,
            item_name=item_name,
            item_plural=item_plural,
            registry_name=registry_name,
            cache_name=cache_name,
            counter_name=counter_name,
            bugs=bugs,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "TRAP7_test_pollution")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        # Build expected with bug module info for grader
        bug_modules = []
        for b in bugs:
            bug_modules.append({
                "module": b["module"],
                "function": b["function"],
                "test_input": b["test_input"],
                "expected_output": b["expected_output"],
            })

        return GeneratedTask(
            task_id="TRAP7_test_pollution",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": domain,
                "bug_modules": bug_modules,
                "pollution_types": ["global_registry", "class_cache", "module_counter"],
                "critical_assertions": [
                    f"assert result == {bugs[0]['expected_output']}",
                    f"assert result == {bugs[1]['expected_output']}",
                ],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Adversarial"},
        )

    def _make_workspace(
        self,
        domain: str,
        item_name: str,
        item_plural: str,
        registry_name: str,
        cache_name: str,
        counter_name: str,
        bugs: list,
    ) -> dict:
        files = {}

        # ── app/__init__.py ───────────────────────────────────────────────
        files["app/__init__.py"] = f'"""{domain.capitalize()} application."""\n'

        # ── app/registry.py — shared mutable global (pollution source 1) ──
        files["app/registry.py"] = f'''\
"""
Global {item_name} registry.

WARNING: This module-level dict is shared across all callers.
"""

{registry_name}: dict[str, dict] = {{}}


def register_{item_name}(key: str, data: dict) -> None:
    """Register a {item_name} in the global registry."""
    {registry_name}[key] = data


def get_{item_name}(key: str) -> dict | None:
    """Look up a {item_name} from the global registry."""
    return {registry_name}.get(key)


def count_{item_plural}() -> int:
    """Return the number of registered {item_plural}."""
    return len({registry_name})


def clear_registry() -> None:
    """Clear all entries from the registry."""
    {registry_name}.clear()
'''

        # ── app/cache.py — class-level cache (pollution source 2) ─────────
        files["app/cache.py"] = f'''\
"""
{item_name.capitalize()} cache with class-level shared storage.

WARNING: The cache dict is a class variable, shared across ALL instances.
"""


class {item_name.capitalize()}Cache:
    """Caches {item_name} lookups. Class-level cache shared across instances."""

    {cache_name}: dict[str, float] = {{}}

    def get(self, key: str) -> float | None:
        """Get a cached value."""
        return self.{cache_name}.get(key)

    def put(self, key: str, value: float) -> None:
        """Cache a value."""
        self.{cache_name}[key] = value

    def size(self) -> int:
        """Return cache size."""
        return len(self.{cache_name})

    @classmethod
    def clear(cls) -> None:
        """Clear the class-level cache."""
        cls.{cache_name}.clear()
'''

        # ── app/counter.py — module-level counter (pollution source 3) ────
        files["app/counter.py"] = f'''\
"""
Module-level {domain} counter.

WARNING: This counter persists across function calls within the same process.
"""

{counter_name} = 0


def next_id() -> int:
    """Return the next sequential ID."""
    global {counter_name}
    {counter_name} += 1
    return {counter_name}


def current_count() -> int:
    """Return current counter value."""
    return {counter_name}


def reset_counter() -> None:
    """Reset the counter to zero."""
    global {counter_name}
    {counter_name} = 0
'''

        # ── Generate bug modules (5 real bugs) ────────────────────────────
        for b in bugs:
            mod = b["module"]
            func = b["function"]
            buggy_op = b["buggy_op"]
            test_input = b["test_input"]

            if mod == "pricing" or mod == "grading":
                params = list(test_input.keys())
                files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""


def {func}({params[0]}: float, {params[1]}: int) -> float:
    """Calculate discounted/curved value.

    Applies a 10% discount/curve when {params[1]} meets threshold.
    """
    {buggy_op}
        return {params[0]} * 0.9
    return float({params[0]})
'''
            elif mod in ("stock", "seats", "ranking"):
                params = list(test_input.keys())
                files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""


def {func}({params[0]}: str, {params[1]}: int) -> bool:
    """Check if {params[0]} has available {params[1]}."""
    {buggy_op}
'''
            elif mod in ("shipping", "fees", "bonus"):
                params = list(test_input.keys())
                expected = b["expected_output"]
                if mod == "fees":
                    files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""

BASE_FEE = 2.0


def {func}({params[0]}: float, {params[1]}: float) -> float:
    """Calculate service fee including base fee."""
    {buggy_op}
'''
                else:
                    files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""


def {func}({params[0]}: float, {params[1]}: float) -> float:
    """Calculate combined value."""
    {buggy_op}
'''
            elif mod in ("tax", "penalty"):
                params = list(test_input.keys())
                files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""


def {func}({params[0]}: float, {params[1]}: float) -> float:
    """Apply {mod} adjustment to amount."""
    {buggy_op}
'''
            elif mod in ("catalog", "venue", "leaderboard"):
                params = list(test_input.keys())
                if len(params) == 2:
                    files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""


def {func}({params[0]}: str, {params[1]}: int) -> str:
    """Format identifier string."""
    {buggy_op}
'''
                else:  # 3 params (venue)
                    files[f"app/{mod}.py"] = f'''\
"""{mod.capitalize()} module for the {domain} system."""


def {func}({params[0]}: str, {params[1]}: int, {params[2]}: int) -> str:
    """Format identifier string."""
    {buggy_op}
'''

        # ── TEST_ANALYSIS.md ──────────────────────────────────────────────
        files["TEST_ANALYSIS.md"] = f'''\
# Test Infrastructure Analysis — {domain.capitalize()} System

## Known Test Infrastructure Issues

### 1. Global Registry Pollution
The `{registry_name}` dict in `app/registry.py` is module-level mutable state.
Tests that register {item_plural} leave them in the registry for subsequent tests.
A test that expects an empty registry will fail if a previous test added entries.

### 2. Class-Level Cache Pollution
The `{cache_name}` dict in `app/cache.py` is a class variable shared across ALL
`{item_name.capitalize()}Cache` instances. Creating a new instance does NOT clear the cache.
Tests that check cache size or cache misses will fail if previous tests populated the cache.

### 3. Module-Level Counter Pollution
The `{counter_name}` variable in `app/counter.py` is module-level state that
monotonically increases. Tests that expect `next_id()` to return 1 will fail
if a previous test already incremented the counter.

## Recommendation

Add proper setup/teardown fixtures to clear shared state before each test:
- Call `clear_registry()` before registry tests
- Call `{item_name.capitalize()}Cache.clear()` before cache tests
- Call `reset_counter()` before counter tests

## Important

The failing tests contain BOTH real bugs in application code AND test pollution.
Do not assume all failures are pollution — some are genuine code defects.
'''

        # ── tests/__init__.py ─────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_app.py — 8 failing tests (5 real bugs + 3 pollution)
        bug_tests = []
        for b in bugs:
            mod = b["module"]
            func = b["function"]
            test_input = b["test_input"]
            expected = b["expected_output"]
            if isinstance(test_input, dict):
                args = ", ".join(f"{k}={repr(v)}" for k, v in test_input.items())
            else:
                args = repr(test_input)

            bug_tests.append(f'''\
def test_{func}():
    """Test {func} produces correct output (REAL BUG if fails)."""
    from app.{mod} import {func}
    result = {func}({args})
    assert result == {repr(expected)}, (
        f"Expected {repr(expected)}, got {{result}}"
    )
''')

        # Pollution tests
        pollution_tests = []

        # Pollution test 1: global registry
        pollution_tests.append(f'''\
def test_registry_empty_on_start():
    """Registry should be empty at start of test (POLLUTION if fails).

    This test fails because a previous test registered items and the
    global registry was not cleared.
    """
    from app.registry import count_{item_plural}, register_{item_name}
    # A previous test may have added items — this should be 0
    assert count_{item_plural}() == 0, (
        f"Expected empty registry, found {{count_{item_plural}()}} {item_plural}. "
        "This is test pollution — the global registry was not cleared between tests."
    )
''')

        # Pollution test 2: class cache
        pollution_tests.append(f'''\
def test_cache_miss_on_new_key():
    """Cache lookup for unknown key should return None (POLLUTION if fails).

    This test fails because a previous test populated the class-level cache
    and new instances share the same cache dict.
    """
    from app.cache import {item_name.capitalize()}Cache
    cache = {item_name.capitalize()}Cache()
    assert cache.size() == 0, (
        f"Expected empty cache, found {{cache.size()}} entries. "
        "This is test pollution — the class-level cache was not cleared."
    )
    result = cache.get("nonexistent_key")
    assert result is None, (
        f"Expected None for unknown key, got {{result}}"
    )
''')

        # Pollution test 3: module counter
        pollution_tests.append(f'''\
def test_counter_starts_at_one():
    """First call to next_id() should return 1 (POLLUTION if fails).

    This test fails because a previous test incremented the module-level
    counter and it was not reset.
    """
    from app.counter import next_id, current_count
    # Counter should be at 0 before first call
    result = next_id()
    assert result == 1, (
        f"Expected next_id() to return 1, got {{result}}. "
        "This is test pollution — the module counter was not reset between tests."
    )
''')

        # Add a setup test that creates pollution for subsequent tests
        setup_pollution = f'''\
def test_registry_add_and_lookup():
    """Test that registry works (this test CREATES pollution for later tests)."""
    from app.registry import register_{item_name}, get_{item_name}
    register_{item_name}("item_A", {{"name": "Alpha", "value": 100}})
    register_{item_name}("item_B", {{"name": "Beta", "value": 200}})
    assert get_{item_name}("item_A") is not None


def test_cache_put_and_get():
    """Test that cache works (this test CREATES pollution for later tests)."""
    from app.cache import {item_name.capitalize()}Cache
    cache = {item_name.capitalize()}Cache()
    cache.put("key_X", 42.0)
    cache.put("key_Y", 99.0)
    assert cache.get("key_X") == 42.0


def test_counter_multiple_ids():
    """Test that counter increments (this test CREATES pollution for later tests)."""
    from app.counter import next_id
    ids = [next_id() for _ in range(5)]
    assert len(set(ids)) == 5  # All unique
'''

        files["tests/test_app.py"] = f'''\
"""
Test suite for the {domain} system.

Contains 8 failing tests:
- 5 tests fail due to real bugs in application code
- 3 tests fail due to test pollution (shared mutable state)

The pollution-creating tests run FIRST (alphabetically) and leave behind
state that causes later tests to fail.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Tests that CREATE pollution (these pass but leave dirty state) ---

{setup_pollution}

# --- Tests for REAL BUGS (these fail due to app code defects) ---

{chr(10).join(bug_tests)}

# --- Tests affected by POLLUTION (these fail due to shared state) ---

{chr(10).join(pollution_tests)}
'''

        files["requirements.txt"] = "pytest\n"

        return files
