"""Parameterized generator for EA4: Code Quality."""
from __future__ import annotations
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


class Generator(TaskGenerator):
    task_id = "EA4_code_quality"
    domain = "CodeReview"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        workspace_files = self._make_workspace(seed)
        spec_md = open(__file__.replace("gen_ea4_code_quality.py", "../tasks/EA4_code_quality/spec.md")).read()
        brief_md = open(__file__.replace("gen_ea4_code_quality.py", "../tasks/EA4_code_quality/brief.md")).read()
        return GeneratedTask(
            task_id="EA4_code_quality",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={"ruff_errors": 0, "pylint_min_score": 9.0, "seed": seed},
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "CodeReview"},
        )

    def _make_workspace(self, seed: int) -> dict:
        files = {}
        # Vary module description per seed for cross-seed differentiation
        module_descs = ["inventory processing", "order management", "billing pipeline"]
        desc = module_descs[seed % len(module_descs)]
        files["app/__init__.py"] = f'"""Application package for {desc} — seed {seed}."""\n'

        files["app/processor.py"] = '''import sys
import os
from typing import List


def process_items(data: List[dict]) -> List[str]:
    l = []
    for i in range(10):
        pass
    for item in data:
        O = item.get("name", "")
        if O == None:
            continue
        if item.get("active") == True:
            l.append(O)
    return l


def is_high_value(value: int) -> bool:
    return value > 1000


def transform_batch(items, flags, config, context, mode, debug, verbose, strict, fast, retry):
    result = []
    if mode == "a":
        if strict:
            if debug: result.append("debug-a")
            else: result.append("a")
        else:
            if verbose: result.append("verbose-a")
            else: result.append("a-lite")
    elif mode == "b":
        if fast:
            result.append("fast-b")
        else:
            result.append("slow-b")
    return result


def compute_totals(values: list):
    return sum(values)
'''

        files["app/helpers.py"] = '''from collections import OrderedDict
import re


def ProcessData(X, threshold=0):
    """Process data."""
    return [x for x in X if x > threshold]


def calculate_weighted_moving_average_with_decay(values, weights, decay_factor):
    """Calculate weighted moving average with exponential decay factor."""
    result = sum(v * w * decay_factor for v, w in zip(values, weights))
    return result / max(1, sum(weights))


def validate_pattern(text: str) -> bool:
    """Validate text against pattern."""
    pattern = "\d+"
    return bool(re.match(pattern, text))


def complex_router(action, data, user, config, permissions, flags, cache, db, log, metrics):
    result = {}
    if action == "read": result["data"] = data
    elif action == "write":
        if user: result["user"] = user
        if config: result["config"] = config
    elif action == "admin":
        if permissions: result["perms"] = permissions
    return result


def build_report(items: list):
    return {"count": len(items), "items": items}
'''

        files["app/models.py"] = '''from typing import Optional, List, Tuple


class DataRecord:
    field: str = ""

    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value
        if self.value == 42:
            self.is_special = True
        else:
            self.is_special = False
class DataCollection:
    def __init__(self):
        self.records: List[DataRecord] = []
'''

        files["app/compat.py"] = '''"""Compatibility shim for Python 2/3."""


def safe_import(module_name):
    """Safely import a module, returning None if import fails."""
    try:
        return __import__(module_name)
    except:  # noqa: E722  — intentional broad except for compat
        return None
'''

        return files
