"""
Parameterized generator for TEST8: Unit Test Basics.

Each seed produces:
  - Different function names and bug types
  - Different input/output values
  - A buggy mathutils.py with 3 functions, each with one bug
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Pool of function triplets with their bug types
FUNC_POOLS = [
    # (func_name, description, bug_type)
    [
        ("sum_range", "Sum integers from a to b inclusive", "off_by_one"),
        ("average", "Return average of a list as float", "wrong_return_type"),
        ("clamp", "Clamp value between min and max", "missing_edge_case"),
    ],
    [
        ("factorial", "Return factorial of n", "off_by_one"),
        ("median", "Return median of a list", "wrong_return_type"),
        ("safe_divide", "Divide a by b, return 0 on zero division", "missing_edge_case"),
    ],
    [
        ("fibonacci", "Return nth Fibonacci number (0-indexed)", "off_by_one"),
        ("to_celsius", "Convert Fahrenheit to Celsius as float", "wrong_return_type"),
        ("max_subarray", "Return max element, or 0 for empty list", "missing_edge_case"),
    ],
]


class Generator(TaskGenerator):
    task_id = "TEST8_unit_basic"
    domain = "testing"
    difficulty = "easy"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        funcs = FUNC_POOLS[seed % len(FUNC_POOLS)]

        workspace_files = {}
        workspace_files["mathutils.py"] = self._make_buggy_module(funcs, rng)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        expected = self._make_expected(funcs, rng, seed)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "Testing"},
        )

    def _make_buggy_module(self, funcs: list, rng: SeededRandom) -> str:
        fn1_name, fn1_desc, _ = funcs[0]
        fn2_name, fn2_desc, _ = funcs[1]
        fn3_name, fn3_desc, _ = funcs[2]

        if fn1_name == "sum_range":
            fn1_code = '''def sum_range(a: int, b: int) -> int:
    """Sum integers from a to b inclusive."""
    total = 0
    for i in range(a, b):  # BUG: should be range(a, b + 1)
        total += i
    return total'''
        elif fn1_name == "factorial":
            fn1_code = '''def factorial(n: int) -> int:
    """Return factorial of n (n >= 0)."""
    if n <= 1:
        return 1
    result = 1
    for i in range(1, n):  # BUG: should be range(1, n + 1)
        result *= i
    return result'''
        else:  # fibonacci
            fn1_code = '''def fibonacci(n: int) -> int:
    """Return nth Fibonacci number (0-indexed). fib(0)=0, fib(1)=1."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(n - 1):  # BUG: should be range(n - 1) but starts from wrong values
        a, b = b, a + b
    return a  # BUG: should return b'''

        if fn2_name == "average":
            fn2_code = '''def average(numbers: list) -> float:
    """Return the average of a list of numbers as a float."""
    if not numbers:
        return 0.0
    return sum(numbers) // len(numbers)  # BUG: integer division, should be /'''
        elif fn2_name == "median":
            fn2_code = '''def median(numbers: list) -> float:
    """Return the median of a list of numbers as a float."""
    if not numbers:
        return 0.0
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_nums[mid - 1] + sorted_nums[mid]) // 2  # BUG: should be / not //
    return sorted_nums[mid]'''
        else:  # to_celsius
            fn2_code = '''def to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return int((fahrenheit - 32) * 5 / 9)  # BUG: returns int, should return float'''

        if fn3_name == "clamp":
            fn3_code = '''def clamp(value: int, low: int, high: int) -> int:
    """Clamp value between low and high (inclusive)."""
    if value < low:
        return low
    if value > high:
        return high
    return value  # Missing edge case: does not handle low > high'''
        elif fn3_name == "safe_divide":
            fn3_code = '''def safe_divide(a: float, b: float) -> float:
    """Divide a by b. Return 0.0 if b is zero."""
    return a / b  # BUG: no check for b == 0, raises ZeroDivisionError'''
        else:  # max_subarray (actually max_element)
            fn3_code = '''def max_subarray(numbers: list) -> int:
    """Return the maximum element in the list, or 0 for empty list."""
    result = numbers[0]  # BUG: crashes on empty list, should check first
    for n in numbers[1:]:
        if n > result:
            result = n
    return result'''

        return f'''"""{fn1_desc}. {fn2_desc}. {fn3_desc}."""


{fn1_code}


{fn2_code}


{fn3_code}
'''

    def _make_expected(self, funcs: list, rng: SeededRandom, seed: int) -> dict:
        fn1_name = funcs[0][0]
        fn2_name = funcs[1][0]
        fn3_name = funcs[2][0]

        if fn1_name == "sum_range":
            bug1_args = [1, 5]
            bug1_expected = 15  # 1+2+3+4+5
        elif fn1_name == "factorial":
            bug1_args = [5]
            bug1_expected = 120
        else:  # fibonacci
            bug1_args = [6]
            bug1_expected = 8  # 0,1,1,2,3,5,8

        if fn2_name == "average":
            bug2_args = [[1, 2, 3, 4]]
            bug2_expected = 2.5
            bug2_type = "float"
        elif fn2_name == "median":
            bug2_args = [[1, 3, 5, 7]]
            bug2_expected = 4.0
            bug2_type = "float"
        else:  # to_celsius
            bug2_args = [100.0]
            bug2_expected = 37.77777777777778
            bug2_type = "float"

        if fn3_name == "clamp":
            bug3_args = [5, 1, 10]
            bug3_expected = 5
        elif fn3_name == "safe_divide":
            bug3_args = [10.0, 0.0]
            bug3_expected = 0.0
        else:  # max_subarray
            bug3_args = [[]]
            bug3_expected = 0

        return {
            "seed": seed,
            "bug1_function": fn1_name,
            "bug1_args": bug1_args,
            "bug1_expected": bug1_expected,
            "bug2_function": fn2_name,
            "bug2_args": bug2_args,
            "bug2_expected": bug2_expected,
            "bug2_expected_type": bug2_type,
            "bug3_function": fn3_name,
            "bug3_args": bug3_args,
            "bug3_expected": bug3_expected,
        }
