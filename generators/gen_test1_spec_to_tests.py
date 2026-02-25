"""
Parameterized generator for TEST1: Write Tests from Specification.

Each seed produces:
- A different module being tested (calculator, string_utils, date_parser,
  url_builder, config_validator, data_transformer)
- Different function signatures and behaviors for that module
- Different edge cases to test
- 10 mutant implementations with different mutations
- A skeleton test file the agent must fill in

The grade.sh for TEST1 references 'calculator/' and mutants from TASK_DIR/mutants/.
Since we are generating a new workspace, we keep the module name as 'calculator'
but vary the internal specification, behaviors, and mutant bugs so each seed
requires genuinely different tests to catch the mutants.
"""
from __future__ import annotations

import hashlib
import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Mutation descriptions keyed by type — we pick 10 per seed from this pool
# Each mutation is (description, the code change that creates the bug)
MUTATION_POOL = [
    # Arithmetic mutations
    ("wrong_div_zero_code", "division_by_zero", "zero_division"),
    ("wrong_overflow_limit", "2 ** 53", "2 ** 52"),
    ("wrong_precision", "round(value, 6)", "round(value, 4)"),
    ("wrong_percent_divisor", "base * pct / 100", "base * pct / 10"),
    ("history_cap_wrong", "self._history[-10:]", "self._history[-20:]"),
    ("undo_clears_memory", "# undo", "self._memory = 0.0  # MUTANT"),
    ("batch_returns_zero", "results.append(func(*args))", "func(*args); results.append(0.0)"),
    ("chain_mult_is_add", "self._value * self._calc._coerce(n)", "self._value + self._calc._coerce(n)"),
    ("coerce_swallows_error", "raise CalculatorError(\"invalid_input\")", "return 0.0"),
    ("subtract_is_add", "a - b", "a + b"),
    ("multiply_is_divide", "a * b", "a / b"),
    ("sqrt_wrong_error", "domain_error", "sqrt_error"),
    ("memory_recall_returns_zero", "return self._memory", "return 0.0"),
    ("add_no_overflow_check", "self._check_overflow(result)", "pass  # no overflow check"),
    ("chain_add_is_subtract", "self._value + self._calc._coerce(n)", "self._value - self._calc._coerce(n)"),
    ("wrong_history_format", 'f"{op_str} = {result}"', 'f"{op_str}: {result}"'),
    ("evaluate_ignores_parens", "ast.parse(expr, mode='eval')", "ast.parse(expr.replace('(','').replace(')',''), mode='eval')"),
    ("percent_base_pct_swapped", "base * pct / 100", "pct * base / 100"),
    ("reset_keeps_history", "self._history = []", "pass  # history not cleared"),
    ("divide_floor_division", "a / b", "a // b"),
]

# Spec behaviors for the calculator — we pick a subset per seed to emphasize
BEHAVIOR_SETS = [
    # Set A: emphasizes error codes and precision
    {
        "add_test": ("add(3, 4)", "7.0"),
        "subtract_test": ("subtract(10, 4)", "6.0"),
        "multiply_test": ("multiply(3, 7)", "21.0"),
        "divide_test": ("divide(15, 3)", "5.0"),
        "chain_test": ("chain(5).add(3).multiply(4).result()", "32.0"),
        "percent_test": ("percent(150, 20)", "30.0"),
        "precision_test": ("divide(1, 3)", "0.333333"),
        "overflow_value": str(2**53 + 1),
    },
    # Set B: emphasizes chaining and batch
    {
        "add_test": ("add(7, 8)", "15.0"),
        "subtract_test": ("subtract(20, 9)", "11.0"),
        "multiply_test": ("multiply(6, 7)", "42.0"),
        "divide_test": ("divide(100, 4)", "25.0"),
        "chain_test": ("chain(2).multiply(5).add(10).result()", "20.0"),
        "percent_test": ("percent(500, 10)", "50.0"),
        "precision_test": ("divide(2, 3)", "0.666667"),
        "overflow_value": str(2**53 + 100),
    },
    # Set C: emphasizes memory and undo
    {
        "add_test": ("add(11, 22)", "33.0"),
        "subtract_test": ("subtract(50, 17)", "33.0"),
        "multiply_test": ("multiply(9, 9)", "81.0"),
        "divide_test": ("divide(49, 7)", "7.0"),
        "chain_test": ("chain(10).subtract(3).multiply(2).result()", "14.0"),
        "percent_test": ("percent(1000, 5)", "50.0"),
        "precision_test": ("divide(1, 6)", "0.166667"),
        "overflow_value": str(2**53 + 50),
    },
    # Set D: emphasizes evaluate and type coercion
    {
        "add_test": ("add(100, 200)", "300.0"),
        "subtract_test": ("subtract(99, 44)", "55.0"),
        "multiply_test": ("multiply(12, 12)", "144.0"),
        "divide_test": ("divide(81, 9)", "9.0"),
        "chain_test": ("chain(8).add(2).multiply(3).subtract(6).result()", "24.0"),
        "percent_test": ("percent(80, 25)", "20.0"),
        "precision_test": ("divide(1, 9)", "0.111111"),
        "overflow_value": str(2**53 + 999),
    },
]


class Generator(TaskGenerator):
    task_id = "TEST1_spec_to_tests"
    domain = "testing"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick behavior set
        behavior_set_idx = rng.randint(0, len(BEHAVIOR_SETS) - 1)
        behaviors = BEHAVIOR_SETS[behavior_set_idx]

        # Pick 10 mutations from the pool (deterministic per seed)
        mutation_indices = rng.sample(list(range(len(MUTATION_POOL))), 10)
        selected_mutations = [MUTATION_POOL[i] for i in mutation_indices]

        # Build expected: which mutants correspond to which mutation types
        mutant_descriptions = {}
        for i, (desc, original, mutated) in enumerate(selected_mutations, start=1):
            mutant_descriptions[f"mutant_{i:02d}"] = {
                "description": desc,
                "original_code": original,
                "mutated_code": mutated,
            }

        expected = {
            "behavior_set": behavior_set_idx,
            "behaviors": behaviors,
            "mutants_required_caught": 7,
            "mutant_count": 10,
            "mutant_descriptions": mutant_descriptions,
            "min_test_functions": 15,
        }

        # Generate workspace files
        engine_py = self._generate_engine()
        test_skeleton = self._generate_test_skeleton(behaviors)
        conftest_py = self._generate_conftest()
        init_py = ""

        # Generate 10 mutant files
        mutant_files = {}
        for i, (desc, original, mutated) in enumerate(selected_mutations, start=1):
            mutant_py = self._generate_mutant(i, desc, original, mutated)
            mutant_files[f"mutants/mutant_{i:02d}.py"] = mutant_py

        workspace_files = {
            "calculator/__init__.py": init_py,
            "calculator/engine.py": engine_py,
            "calculator/test_engine.py": test_skeleton,
            "calculator/conftest.py": conftest_py,
        }
        workspace_files.update(mutant_files)

        spec_md = self._generate_spec(behaviors)
        brief_md = self._generate_brief()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_engine(self) -> str:
        return '''"""Calculator engine with 15+ behaviors."""
import threading
import re
import ast
import operator


class CalculatorError(Exception):
    """Calculator-specific error."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class Calculator:
    OVERFLOW_LIMIT = 2 ** 53

    def __init__(self):
        self._memory = 0.0
        self._history = []
        self._chain_value = None
        self._lock = threading.Lock()

    def _check_overflow(self, *values):
        for v in values:
            if isinstance(v, (int, float)) and abs(v) > self.OVERFLOW_LIMIT:
                raise CalculatorError("overflow")

    def _coerce(self, value):
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise CalculatorError("invalid_input")
        return float(value)

    def _record(self, op_str, result):
        self._history.append(f"{op_str} = {result}")
        if len(self._history) > 10:
            self._history = self._history[-10:]
        return result

    def _round(self, value):
        return round(value, 6)

    def add(self, a, b):
        with self._lock:
            a, b = self._coerce(a), self._coerce(b)
            self._check_overflow(a, b)
            result = self._round(a + b)
            self._check_overflow(result)
            return self._record(f"add({a}, {b})", result)

    def subtract(self, a, b):
        with self._lock:
            a, b = self._coerce(a), self._coerce(b)
            self._check_overflow(a, b)
            result = self._round(a - b)
            return self._record(f"subtract({a}, {b})", result)

    def multiply(self, a, b):
        with self._lock:
            a, b = self._coerce(a), self._coerce(b)
            self._check_overflow(a, b)
            result = self._round(a * b)
            self._check_overflow(result)
            return self._record(f"multiply({a}, {b})", result)

    def divide(self, a, b):
        with self._lock:
            a, b = self._coerce(a), self._coerce(b)
            self._check_overflow(a, b)
            if b == 0:
                raise CalculatorError("division_by_zero")
            result = self._round(a / b)
            return self._record(f"divide({a}, {b})", result)

    def sqrt(self, a):
        with self._lock:
            a = self._coerce(a)
            if a < 0:
                raise CalculatorError("domain_error")
            result = self._round(a ** 0.5)
            return self._record(f"sqrt({a})", result)

    def percent(self, base, pct):
        with self._lock:
            base, pct = self._coerce(base), self._coerce(pct)
            result = self._round(base * pct / 100)
            return self._record(f"percent({base}, {pct})", result)

    def evaluate(self, expr):
        """Evaluate a math expression string with proper operator precedence."""
        with self._lock:
            try:
                tree = ast.parse(expr, mode=\'eval\')
                result = self._round(self._eval_node(tree.body))
                self._check_overflow(result)
                return self._record(f"evaluate(\\"{expr}\\")", result)
            except (SyntaxError, TypeError):
                raise CalculatorError("invalid_input")

    def _eval_node(self, node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
            }
            op_func = ops.get(type(node.op))
            if op_func is None:
                raise CalculatorError("invalid_input")
            if isinstance(node.op, ast.Div) and right == 0:
                raise CalculatorError("division_by_zero")
            return op_func(left, right)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node(node.operand)
        else:
            raise CalculatorError("invalid_input")

    def chain(self, initial):
        """Start a chained operation."""
        return _Chain(self, self._coerce(initial))

    def memory_store(self, value):
        with self._lock:
            self._memory = self._coerce(value)

    def memory_recall(self):
        with self._lock:
            return self._memory

    def memory_clear(self):
        with self._lock:
            self._memory = 0.0

    def history(self):
        with self._lock:
            return list(self._history)

    def undo(self):
        with self._lock:
            if self._history:
                self._history.pop()

    def batch(self, operations):
        results = []
        for op in operations:
            name = op[0]
            args = op[1:]
            func = getattr(self, name, None)
            if func is None:
                raise CalculatorError("invalid_input")
            results.append(func(*args))
        return results

    def reset(self):
        with self._lock:
            self._memory = 0.0
            self._history = []
            self._chain_value = None


class _Chain:
    def __init__(self, calc, value):
        self._calc = calc
        self._value = value

    def add(self, n):
        self._value = self._calc._round(self._value + self._calc._coerce(n))
        return self

    def subtract(self, n):
        self._value = self._calc._round(self._value - self._calc._coerce(n))
        return self

    def multiply(self, n):
        self._value = self._calc._round(self._value * self._calc._coerce(n))
        return self

    def divide(self, n):
        n = self._calc._coerce(n)
        if n == 0:
            raise CalculatorError("division_by_zero")
        self._value = self._calc._round(self._value / n)
        return self

    def result(self):
        return self._value
'''

    def _generate_test_skeleton(self, behaviors: dict) -> str:
        add_call, add_result = behaviors["add_test"]
        subtract_call, subtract_result = behaviors["subtract_test"]
        multiply_call, multiply_result = behaviors["multiply_test"]
        divide_call, divide_result = behaviors["divide_test"]
        chain_call, chain_result = behaviors["chain_test"]
        percent_call, percent_result = behaviors["percent_test"]
        precision_call, precision_result = behaviors["precision_test"]
        overflow_val = behaviors["overflow_value"]

        return f'''"""Tests for the calculator engine. Write comprehensive tests here."""
import pytest
from calculator.engine import Calculator, CalculatorError

# Specification hints:
# - calc.{add_call} should return {add_result}
# - calc.{subtract_call} should return {subtract_result}
# - calc.{multiply_call} should return {multiply_result}
# - calc.{divide_call} should return {divide_result}
# - calc.{chain_call} should return {chain_result}
# - calc.{percent_call} should return {percent_result}
# - calc.{precision_call} should return {precision_result} (6 decimal places)
# - calc.add({overflow_val}, 1) should raise CalculatorError("overflow")
# - calc.divide(10, 0) should raise CalculatorError("division_by_zero")
# - calc.sqrt(-4) should raise CalculatorError("domain_error")
# - calc.add("abc", 1) should raise CalculatorError("invalid_input")
# - calc.add("5", "3") should return 8.0 (type coercion)
# TODO: Write tests based on the specification above
'''

    def _generate_conftest(self) -> str:
        return '''"""Pytest fixtures for calculator tests."""
import pytest
from calculator.engine import Calculator


@pytest.fixture
def calc():
    """Fresh calculator instance for each test."""
    return Calculator()
'''

    def _generate_mutant(
        self, mutant_num: int, description: str, original: str, mutated: str
    ) -> str:
        """Generate a mutant engine file by applying the mutation to the correct engine."""
        # Read the correct engine and apply the mutation textually
        engine = self._generate_engine()
        # Apply the mutation: replace first occurrence of original pattern with mutated
        mutated_engine = engine.replace(original, mutated, 1)
        mutant_header = f'"""Calculator engine with 15+ behaviors."""\n"""MUTANT {mutant_num:02d}: {description} — \'{original}\' replaced with \'{mutated}\'"""\n'
        # Remove the original first docstring line and prepend mutant header
        lines = mutated_engine.split("\n")
        # Replace the first line (docstring) with mutant header lines
        lines[0] = mutant_header.rstrip()
        return "\n".join(lines)

    def _generate_spec(self, behaviors: dict) -> str:
        add_call, add_result = behaviors["add_test"]
        subtract_call, subtract_result = behaviors["subtract_test"]
        multiply_call, multiply_result = behaviors["multiply_test"]
        divide_call, divide_result = behaviors["divide_test"]
        chain_call, chain_result = behaviors["chain_test"]
        percent_call, percent_result = behaviors["percent_test"]
        precision_call, precision_result = behaviors["precision_test"]
        overflow_val = behaviors["overflow_value"]

        return f"""# TEST1: Write Tests from Specification

## Goal
Write comprehensive tests for the calculator engine that catch bugs through mutation testing.

## Calculator Specification — 20 Behaviors

### Basic Arithmetic
1. `calc.add(a, b)` returns the sum of `a` and `b`
2. `calc.subtract(a, b)` returns the difference `a` minus `b`
3. `calc.multiply(a, b)` returns the product of `a` and `b`
4. `calc.divide(a, b)` returns the quotient `a` divided by `b`

### Error Handling
5. Dividing by zero raises `CalculatorError` with code `"division_by_zero"`
6. Numbers exceeding 2^53 raise `CalculatorError` with code `"overflow"`
7. Taking the square root of a negative number raises `CalculatorError` with code `"domain_error"`

### Chained Operations
8. The calculator supports method chaining starting from an initial value; each chained operation applies to the running result; calling `.result()` returns the final value

### Memory
9. A value stored with `memory_store` is returned by a subsequent `memory_recall`
10. After `memory_clear`, `memory_recall` returns `0.0`

### Precision
11. All results are rounded to exactly 6 decimal places (e.g., `calc.{precision_call}` returns `{precision_result}`)

### Percentage
12. `calc.percent(value, pct)` returns the given percentage of the value (e.g., `calc.{percent_call}` = `{percent_result}`)

### Expression Parsing
13. `calc.evaluate(expr)` parses and evaluates arithmetic expressions following standard operator precedence (multiplication and division before addition and subtraction)
14. Parentheses in expressions override default precedence

### History
15. `calc.history()` returns a list of the last 10 operations as strings in the format `"op(a, b) = result"`; operations beyond 10 cause the oldest to be dropped

### Undo
16. After an operation, calling `calc.undo()` reverses that operation and removes its entry from history

### Batch Mode
17. `calc.batch(ops)` accepts a list of `(operation, arg1, arg2)` tuples and returns a list of results in the same order

### Reset
18. `calc.reset()` clears history, memory, and any chain state

### Type Coercion
19. Numeric string inputs (e.g., `"5"`) are automatically converted to numbers
20. Non-numeric string inputs raise `CalculatorError` with code `"invalid_input"`

### Thread Safety
21. Concurrent operations from multiple threads must not corrupt calculator state or raise exceptions

## Test Cases Table

| # | Operation | Expected | Notes |
|---|-----------|----------|-------|
| 1 | {add_call} | {add_result} | Basic add |
| 2 | divide(10, 0) | CalculatorError("division_by_zero") | Error |
| 3 | add({overflow_val}, 1) | CalculatorError("overflow") | Boundary |
| 4 | sqrt(-4) | CalculatorError("domain_error") | Domain |
| 5 | {chain_call} | {chain_result} | Chaining |
| 6 | memory_store(99); memory_recall() | 99.0 | Memory |
| 7 | {precision_call} | {precision_result} | Precision |
| 8 | {percent_call} | {percent_result} | Percentage |
| 9 | evaluate("2 + 3 * 4") | 14.0 | Precedence |
| 10 | evaluate("(2 + 3) * 4") | 20.0 | Parentheses |
| 11 | 11 operations; history() length | 10 | History cap |
| 12 | add(1,2); undo(); history() | [] | Undo |
| 13 | batch([("add",1,2),("multiply",3,4)]) | [3.0, 12.0] | Batch |
| 14 | reset(); memory_recall() | 0.0 | Reset |
| 15 | add("5", "3") | 8.0 | Coercion |
| 16 | add("abc", 1) | CalculatorError("invalid_input") | Bad input |
| 17 | {subtract_call} | {subtract_result} | Basic subtract |
| 18 | multiply(0, 100) | 0.0 | Zero |
| 19 | {divide_call} | {divide_result} | Division |
| 20 | 10 threads each calling add(1,1) | No exceptions | Thread safety |

## Grading
- Phase 1: All tests must pass on correct engine (pytest passes, branch coverage > 80%)
- Phase 2: Tests must catch at least 7/10 mutant engines (each has one subtle bug)

## Deliverables
- `calculator/test_engine.py` with at least 15 test functions
- Verifier must run tests and verify coverage + mutation detection
"""

    def _generate_brief(self) -> str:
        return """# TEST1: Write Tests from Specification (Brief)

Write comprehensive pytest tests for the calculator engine in `calculator/test_engine.py`.
Tests must pass on the correct engine and catch at least 7 out of 10 mutant engines.
Minimum 15 test functions required.
Run: `python -m pytest calculator/test_engine.py`
"""
