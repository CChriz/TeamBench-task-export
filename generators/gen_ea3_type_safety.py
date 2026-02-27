"""Parameterized generator for EA3: Type Safety."""
from __future__ import annotations
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


class Generator(TaskGenerator):
    task_id = "EA3_type_safety"
    domain = "SWE"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        workspace_files = self._make_workspace(seed)
        spec_md = open(__file__.replace("gen_ea3_type_safety.py", "../tasks/EA3_type_safety/spec.md")).read()
        brief_md = open(__file__.replace("gen_ea3_type_safety.py", "../tasks/EA3_type_safety/brief.md")).read()

        return GeneratedTask(
            task_id="EA3_type_safety",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={"mypy_errors": 0, "type_ignore_count": 3, "seed": seed},
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "SWE"},
        )

    def _make_workspace(self, seed: int) -> dict:
        files = {}
        files["app/__init__.py"] = ""

        # Vary entity names per seed for cross-seed differentiation
        entity_variants = [
            ("User", "user_id", "Product", "product_id"),
            ("Account", "account_id", "Item", "item_id"),
            ("Customer", "customer_id", "Order", "order_id"),
        ]
        entity, eid, entity2, eid2 = entity_variants[seed % len(entity_variants)]

        files["app/models.py"] = f'''"""Data models with type errors — seed {seed}."""
from typing import Any


class {entity}:
    def __init__(self, {eid}: Any, name: str):
        self.{eid} = {eid}
        self.name = name
        self.tags: list = []

    def get_name(self):
        return self.name


class {entity2}:
    def __init__(self, {eid2}: int, price: float):
        self.{eid2} = {eid2}
        self.price = price
        self.category: str = "uncategorized"
'''

        files["app/service.py"] = '''"""Service layer with type errors."""
from typing import Optional


def process(items):
    """Process items and return names."""
    return [item.get("name", "") for item in items]


def find_user(user_id: int) -> Optional[str]:
    """Find user by ID."""
    result = None
    users = {1: "Alice", 2: "Bob"}
    if user_id in users:
        result = users[user_id]
    return result


def initialize_counter() -> int:
    count: int = "0"
    return int(count)


def transform(x: int) -> str:
    return x
'''

        files["app/utils.py"] = '''"""Utility functions with type errors."""
from typing import Dict, Any, Optional
from datetime import datetime


def parse_date(s) -> Optional[datetime]:
    """Parse a date string."""
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


class Registry:
    def __init__(self):
        self.items: Dict = {}

    def register(self, key: str, value: Any) -> None:
        self.items[key] = value


def merge(a, b):
    """Merge two dicts."""
    result = dict(a)
    result.update(b)
    return result
'''

        files["app/dynamic.py"] = '''"""Dynamic dispatch module — intentional use of dynamic Python patterns."""
from typing import Any


def call_method(obj: Any, method_name: str) -> Any:
    """Dynamically call a method by name."""
    return getattr(obj, method_name)()


# Plugin registry — values are Any by design
plugin_registry: dict = {}


def get_plugin_result(key: str) -> str:
    """Get result from plugin registry."""
    return plugin_registry[key]


def apply_cast(cast_fn: Any, value: Any) -> Any:
    """Apply a runtime casting function from configuration."""
    return cast_fn(value)
'''

        return files
