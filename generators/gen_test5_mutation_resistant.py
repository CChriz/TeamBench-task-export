"""
Parameterized generator for TEST5: Mutation-Resistant Test Suite.

Each seed produces:
- A mathlib.py with 25 functions/behaviors
- An empty tests/test_mathlib.py the agent must fill
- 20 mutant files with single subtle bugs
- Different function names, boundary values per seed

The grade.sh runs the agent's tests against each mutant; score = mutants killed / 20.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-variant pools ───────────────────────────────────────────────────────

# Function name variants (prefix for math operations)
MODULE_NAMES = ["mathlib", "mathlib", "mathlib"]  # keep module name stable for grader

# Overflow thresholds per seed
OVERFLOW_LIMITS = [1e15, 1e12, 1e18]

# Prime test boundary values per seed
PRIME_BOUNDARIES = [
    (2, 3, 97, 100),
    (2, 5, 89, 91),
    (2, 7, 83, 85),
]

# Fibonacci large-index per seed
FIB_LARGE = [20, 25, 30]

# Statistics test data per seed
STATS_DATA = [
    [4, 8, 6, 5, 3, 7, 2, 9, 1, 10],
    [12, 15, 11, 14, 13, 16, 10, 17, 18, 19],
    [22, 25, 28, 21, 24, 27, 23, 26, 29, 20],
]

# Mutation pool: (name, description, target_function, original_snippet, mutated_snippet)
# IMPORTANT: each original_snippet must be UNIQUE in the generated mathlib.py
# so that replace(..., 1) targets the correct function.
MUTATION_POOL = [
    ("add_returns_sub", "add returns subtraction", "add",
     "return float(a + b)", "return float(a - b)"),
    ("subtract_returns_add", "subtract returns addition", "subtract",
     "return float(a - b)", "return float(a + b)"),
    ("multiply_returns_add", "multiply returns addition", "multiply",
     "return float(a * b)", "return float(a + b)"),
    ("divide_floor", "divide uses floor division", "divide",
     "return float(a / b)", "return float(a // b)"),
    ("modulo_wrong_op", "modulo returns division instead", "modulo",
     "return a % b", "return a // b"),
    ("power_no_overflow", "power skips overflow check", "power",
     'raise MathLibError("overflow")', "pass  # skip overflow"),
    ("sqrt_wrong_error", "sqrt wrong error code", "sqrt",
     'raise MathLibError("domain_error")\n    return math.sqrt',
     'raise MathLibError("math_error")\n    return math.sqrt'),
    ("abs_returns_negative", "absolute negates", "absolute",
     "return abs(x)", "return -abs(x)"),
    ("min_returns_max", "minimum returns maximum", "minimum",
     "a if a <= b else b", "a if a >= b else b"),
    ("max_returns_min", "maximum returns minimum", "maximum",
     "a if a >= b else b", "a if a <= b else b"),
    ("clamp_lo_hi_swap", "clamp returns hi when below lo", "clamp",
     "return lo\n    if x > hi:", "return hi\n    if x > hi:"),
    ("is_even_wrong", "is_even checks mod 3", "is_even",
     "return n % 2 == 0", "return n % 3 == 0"),
    ("is_odd_inverted", "is_odd returns inverted", "is_odd",
     "return n % 2 != 0", "return n % 2 == 0"),
    ("is_prime_skips_2", "is_prime says 2 is not prime", "is_prime",
     "if n == 2:\n        return True",
     "if n == 2:\n        return False"),
    ("factorial_off_by_one", "factorial range off by one", "factorial",
     "for i in range(2, n + 1):\n        result *= i", "for i in range(2, n):\n        result *= i"),
    ("fibonacci_wrong_base", "fibonacci fib(1) returns 0", "fibonacci",
     "return n  # base cases 0 and 1", "return 0  # base cases 0 and 1"),
    ("gcd_no_abs", "gcd skips absolute value", "gcd",
     "a, b = abs(a), abs(b)", "pass  # skip abs"),
    ("lcm_wrong_formula", "lcm uses addition instead of multiplication", "lcm",
     "abs(a * b) // gcd(a, b)", "abs(a + b) // gcd(a, b)"),
    ("mean_off_by_one", "mean divides by len+1", "mean",
     "return sum(values) / len(values)", "return sum(values) / (len(values) + 1)"),
    ("median_no_sort", "median skips sorting", "median",
     "sorted_vals = sorted(values)\n    n = len(sorted_vals)",
     "sorted_vals = list(values)\n    n = len(sorted_vals)"),
    ("mode_counts_wrong", "mode decrements instead of increments", "mode",
     "counts[v] = counts.get(v, 0) + 1", "counts[v] = counts.get(v, 0) - 1"),
    ("std_dev_no_sqrt", "std_dev returns variance not std dev", "std_dev",
     "return math.sqrt(variance)", "return variance"),
    ("percentile_wrong_idx", "percentile index off by one", "percentile",
     "idx = p / 100 * (len(sorted_vals) - 1)", "idx = p / 100 * len(sorted_vals)"),
    ("normalize_inverted", "normalize inverts the mapping", "normalize",
     "(v - min_val) / span", "(max_val - v) / span"),
    ("validate_range_strict", "validate_range uses strict inequality", "validate_range",
     "return lo <= value <= hi", "return lo < value < hi"),
]


class Generator(TaskGenerator):
    task_id = "TEST5_mutation_resistant"
    domain = "testing"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 3

        overflow_limit = OVERFLOW_LIMITS[idx]
        prime_bounds = PRIME_BOUNDARIES[idx]
        fib_large = FIB_LARGE[idx]
        stats_data = STATS_DATA[idx]

        # Pick 20 mutations from pool (deterministic per seed)
        all_indices = list(range(len(MUTATION_POOL)))
        mutation_indices = rng.sample(all_indices, 20)
        selected_mutations = [MUTATION_POOL[i] for i in mutation_indices]

        params = dict(
            overflow_limit=overflow_limit,
            prime_bounds=prime_bounds,
            fib_large=fib_large,
            stats_data=stats_data,
        )

        workspace_files = self._make_workspace(**params)

        # Generate mutant files (stored in workspace for the grader)
        mathlib_src = workspace_files["mathlib.py"]
        for i, (name, desc, target_fn, original, mutated) in enumerate(
            selected_mutations, start=1
        ):
            mutant_src = self._make_mutant(mathlib_src, i, name, desc, original, mutated)
            workspace_files[f"mutants/mutant_{i:02d}.py"] = mutant_src

        # Build expected
        mutant_descriptions = {}
        for i, (name, desc, target_fn, original, mutated) in enumerate(
            selected_mutations, start=1
        ):
            mutant_descriptions[f"mutant_{i:02d}"] = {
                "name": name,
                "description": desc,
                "function": target_fn,
                "original": original,
                "mutated": mutated,
            }

        expected = {
            "seed": seed,
            "overflow_limit": overflow_limit,
            "fib_large": fib_large,
            "stats_data": stats_data,
            "mutants_required_killed": 16,
            "mutant_count": 20,
            "min_test_functions": 25,
            "mutant_descriptions": mutant_descriptions,
        }

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "TEST5_mutation_resistant"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

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
        overflow_limit: float,
        prime_bounds: tuple,
        fib_large: int,
        stats_data: list,
    ) -> dict:
        files = {}

        overflow_limit_str = f"{overflow_limit:.0e}".replace("+", "")

        # ── mathlib.py ───────────────────────────────────────────────────────
        files["mathlib.py"] = f'''"""Math and validation library with 25 behaviors."""
import math


class MathLibError(Exception):
    """Library-specific error with a code."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


# ── Basic Arithmetic ─────────────────────────────────────────────────────

def add(a, b):
    """Return a + b as float."""
    return float(a + b)


def subtract(a, b):
    """Return a - b as float."""
    return float(a - b)


def multiply(a, b):
    """Return a * b as float."""
    return float(a * b)


def divide(a, b):
    """Return a / b as float. Raises on division by zero."""
    if b == 0:
        raise MathLibError("division_by_zero")
    return float(a / b)


def modulo(a, b):
    """Return a % b. Raises on division by zero."""
    if b == 0:
        raise MathLibError("division_by_zero")
    return a % b


# ── Advanced Math ────────────────────────────────────────────────────────

def power(base, exp):
    """Return base ** exp. Raises on overflow."""
    result = base ** exp
    if abs(result) > {overflow_limit_str}:
        raise MathLibError("overflow")
    return float(result)


def sqrt(x):
    """Return square root. Raises for negative input."""
    if x < 0:
        raise MathLibError("domain_error")
    return math.sqrt(x)


def absolute(x):
    """Return absolute value."""
    return abs(x)


def minimum(a, b):
    """Return the smaller of a and b."""
    return a if a <= b else b


def maximum(a, b):
    """Return the larger of a and b."""
    return a if a >= b else b


def clamp(x, lo, hi):
    """Clamp x to [lo, hi]. Raises if lo > hi."""
    if lo > hi:
        raise MathLibError("invalid_range")
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


# ── Number Properties ────────────────────────────────────────────────────

def is_even(n):
    """Return True if n is divisible by 2."""
    return n % 2 == 0


def is_odd(n):
    """Return True if n is not divisible by 2."""
    return n % 2 != 0


def is_prime(n):
    """Return True if n is prime (n >= 2)."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


# ── Combinatorics ────────────────────────────────────────────────────────

def factorial(n):
    """Return n!. Raises for negative n."""
    if n < 0:
        raise MathLibError("domain_error")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n):
    """Return n-th Fibonacci number (0-indexed). Raises for negative n."""
    if n < 0:
        raise MathLibError("domain_error")
    if n <= 1:
        return n  # base cases 0 and 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def gcd(a, b):
    """Return greatest common divisor."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """Return least common multiple."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


# ── Statistics ───────────────────────────────────────────────────────────

def mean(values):
    """Return arithmetic mean."""
    if not values:
        raise MathLibError("empty_input")
    return sum(values) / len(values)


def median(values):
    """Return median value."""
    if not values:
        raise MathLibError("empty_input")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    return sorted_vals[mid]


def mode(values):
    """Return most frequent value (first if tied)."""
    if not values:
        raise MathLibError("empty_input")
    counts = {{}}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    max_count = max(counts.values())
    for v in values:
        if counts[v] == max_count:
            return v


def std_dev(values):
    """Return population standard deviation."""
    if not values or len(values) < 2:
        raise MathLibError("empty_input")
    m = sum(values) / len(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def percentile(values, p):
    """Return p-th percentile (0-100)."""
    if not values:
        raise MathLibError("empty_input")
    if p < 0 or p > 100:
        raise MathLibError("invalid_range")
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = p / 100 * (len(sorted_vals) - 1)
    lower = int(idx)
    upper = lower + 1
    if upper >= len(sorted_vals):
        return sorted_vals[-1]
    frac = idx - lower
    return sorted_vals[lower] + frac * (sorted_vals[upper] - sorted_vals[lower])


# ── Utilities ────────────────────────────────────────────────────────────

def normalize(values, lo=0.0, hi=1.0):
    """Scale values to [lo, hi] range."""
    if not values:
        raise MathLibError("empty_input")
    min_val = min(values)
    max_val = max(values)
    span = max_val - min_val
    if span == 0:
        raise MathLibError("constant_input")
    return [(v - min_val) / span * (hi - lo) + lo for v in values]


def validate_range(value, lo, hi):
    """Return True if lo <= value <= hi. Raises if lo > hi."""
    if lo > hi:
        raise MathLibError("invalid_range")
    return lo <= value <= hi
'''

        # ── tests/__init__.py ────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_mathlib.py (skeleton) ─────────────────────────────────
        files["tests/test_mathlib.py"] = f'''"""Tests for mathlib.py. Write comprehensive tests here."""
import pytest
from mathlib import (
    add, subtract, multiply, divide, modulo,
    power, sqrt, absolute, minimum, maximum, clamp,
    is_even, is_odd, is_prime,
    factorial, fibonacci, gcd, lcm,
    mean, median, mode, std_dev, percentile,
    normalize, validate_range,
    MathLibError,
)

# Sample test data: {stats_data}
# Prime boundaries: {prime_bounds}
# Fibonacci large index: {fib_large}

# TODO: Write at least 25 test functions covering all 25 behaviors
# TODO: Include edge cases for error paths (division by zero, negative inputs, empty lists)
# TODO: Make sure tests are specific enough to catch subtle mutations
'''

        # ── conftest.py ──────────────────────────────────────────────────────
        files["conftest.py"] = '''"""Pytest configuration."""
'''

        return files

    def _make_mutant(
        self,
        original_src: str,
        mutant_num: int,
        name: str,
        desc: str,
        original_snippet: str,
        mutated_snippet: str,
    ) -> str:
        """Generate a mutant by replacing the first occurrence of the snippet."""
        mutated = original_src.replace(original_snippet, mutated_snippet, 1)
        # Prepend mutant header as a comment
        header = f'# MUTANT {mutant_num:02d}: {name} — {desc}\n'
        return header + mutated
