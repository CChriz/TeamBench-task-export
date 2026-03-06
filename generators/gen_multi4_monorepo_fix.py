"""
Parameterized generator for MULTI4: Monorepo Dependency Fix.

Each seed produces a monorepo with 5 Python packages that have 3 dependency issues:
  1. Circular import: models imports from api (models->api->core->models)
  2. Stale version pin: utils pins core==1.0 but needs core>=1.2
  3. Moved function: worker imports process_item from core, but it moved to utils

Seed variation: different package names, function names, class names, version numbers.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


DOMAINS = [
    {
        # Seed 0: Web application packages
        "prefix": "webapp",
        "core_pkg": "core",
        "models_pkg": "models",
        "api_pkg": "api",
        "worker_pkg": "worker",
        "utils_pkg": "utils",
        "base_class": "BaseProcessor",
        "moved_func": "process_item",
        "circular_func": "format_response",
        "entity_class": "UserModel",
        "entity_field": "username",
        "core_version": "1.2.0",
        "utils_stale_pin": "1.0",
        "utils_correct_pin": "1.2",
        "worker_helper": "run_batch",
    },
    {
        # Seed 1: Data platform packages
        "prefix": "dataplatform",
        "core_pkg": "engine",
        "models_pkg": "schemas",
        "api_pkg": "gateway",
        "worker_pkg": "scheduler",
        "utils_pkg": "toolkit",
        "base_class": "BaseTransformer",
        "moved_func": "transform_record",
        "circular_func": "render_output",
        "entity_class": "DataSchema",
        "entity_field": "schema_name",
        "core_version": "2.1.0",
        "utils_stale_pin": "2.0",
        "utils_correct_pin": "2.1",
        "worker_helper": "schedule_job",
    },
    {
        # Seed 2: ML pipeline packages
        "prefix": "mlpipe",
        "core_pkg": "framework",
        "models_pkg": "definitions",
        "api_pkg": "serving",
        "worker_pkg": "trainer",
        "utils_pkg": "helpers",
        "base_class": "BasePipeline",
        "moved_func": "execute_step",
        "circular_func": "format_prediction",
        "entity_class": "ModelConfig",
        "entity_field": "model_name",
        "core_version": "3.0.0",
        "utils_stale_pin": "2.8",
        "utils_correct_pin": "3.0",
        "worker_helper": "train_model",
    },
]


class Generator(TaskGenerator):
    task_id = "MULTI4_monorepo_fix"
    domain = "Multi-language"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        d = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(d, seed)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "MULTI4_monorepo_fix")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="MULTI4_monorepo_fix",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": [
                    "B1_circular_import",
                    "B2_stale_version_pin",
                    "B3_moved_function",
                ],
                "seed": seed,
                "domain": d["prefix"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Multi-language"},
        )

    def _make_workspace(self, d: dict, seed: int) -> dict:
        files = {}

        # Core package
        files[f"{d['core_pkg']}/__init__.py"] = self._core_init(d)
        files[f"{d['core_pkg']}/base.py"] = self._core_base(d)
        files[f"{d['core_pkg']}/processing.py"] = self._core_processing(d)
        files[f"{d['core_pkg']}/setup.cfg"] = self._core_setup(d)

        # Models package (has circular import bug)
        files[f"{d['models_pkg']}/__init__.py"] = self._models_init(d)
        files[f"{d['models_pkg']}/entities.py"] = self._models_entities(d)
        files[f"{d['models_pkg']}/helpers.py"] = self._models_helpers(d)
        files[f"{d['models_pkg']}/setup.cfg"] = self._models_setup(d)

        # API package
        files[f"{d['api_pkg']}/__init__.py"] = self._api_init(d)
        files[f"{d['api_pkg']}/endpoints.py"] = self._api_endpoints(d)
        files[f"{d['api_pkg']}/formatters.py"] = self._api_formatters(d)
        files[f"{d['api_pkg']}/setup.cfg"] = self._api_setup(d)

        # Worker package (has moved function bug)
        files[f"{d['worker_pkg']}/__init__.py"] = self._worker_init(d)
        files[f"{d['worker_pkg']}/tasks.py"] = self._worker_tasks(d)
        files[f"{d['worker_pkg']}/setup.cfg"] = self._worker_setup(d)

        # Utils package (has stale version pin)
        files[f"{d['utils_pkg']}/__init__.py"] = self._utils_init(d)
        files[f"{d['utils_pkg']}/processing.py"] = self._utils_processing(d)
        files[f"{d['utils_pkg']}/formatters.py"] = self._utils_formatters(d)
        files[f"{d['utils_pkg']}/setup.cfg"] = self._utils_setup(d)

        # Changelog
        files["CHANGELOG.md"] = self._changelog(d)

        # Tests
        files["tests/__init__.py"] = ""
        files["tests/test_imports.py"] = self._test_imports(d)
        files["tests/test_versions.py"] = self._test_versions(d)

        return files

    # ------------------------------------------------------------------
    # Core package
    # ------------------------------------------------------------------
    def _core_init(self, d: dict) -> str:
        return f'''"""
{d["core_pkg"]} package — v{d["core_version"]}

Base classes and interfaces for the {d["prefix"]} monorepo.
"""
__version__ = "{d["core_version"]}"

from {d["core_pkg"]}.base import {d["base_class"]}
'''

    def _core_base(self, d: dict) -> str:
        return f'''"""
Base classes for {d["core_pkg"]}.
Added {d["base_class"]} in v{d["utils_correct_pin"]}.
"""


class {d["base_class"]}:
    """Base class for all processors in the {d["prefix"]} system."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def validate(self) -> bool:
        return self._initialized

    def run(self, data: dict) -> dict:
        raise NotImplementedError("Subclasses must implement run()")
'''

    def _core_processing(self, d: dict) -> str:
        return f'''"""
Processing utilities for {d["core_pkg"]}.

NOTE: {d["moved_func"]}() was moved to {d["utils_pkg"]}.processing in v{d["utils_correct_pin"]}.
This module retains other processing helpers.
"""


def validate_input(data: dict) -> bool:
    """Validate that input data has required fields."""
    required = ["id", "type", "payload"]
    return all(k in data for k in required)


def normalize_output(result: dict) -> dict:
    """Normalize output fields."""
    return {{k.lower(): v for k, v in result.items()}}


# {d["moved_func"]} was here but moved to {d["utils_pkg"]}.processing in v{d["utils_correct_pin"]}
# Keeping this comment for historical reference.
'''

    def _core_setup(self, d: dict) -> str:
        return f'''[metadata]
name = {d["core_pkg"]}
version = {d["core_version"]}

[options]
packages = {d["core_pkg"]}
python_requires = >=3.9
'''

    # ------------------------------------------------------------------
    # Models package (with circular import bug)
    # ------------------------------------------------------------------
    def _models_init(self, d: dict) -> str:
        return f'''"""
{d["models_pkg"]} package — data model definitions.
"""
from {d["models_pkg"]}.entities import {d["entity_class"]}
'''

    def _models_entities(self, d: dict) -> str:
        return f'''"""
Entity definitions for {d["models_pkg"]}.
"""
from {d["core_pkg"]}.base import {d["base_class"]}


class {d["entity_class"]}:
    """Primary entity model."""

    def __init__(self, {d["entity_field"]}: str, data: dict | None = None):
        self.{d["entity_field"]} = {d["entity_field"]}
        self.data = data or {{}}

    def to_dict(self) -> dict:
        return {{
            "{d["entity_field"]}": self.{d["entity_field"]},
            "data": self.data,
        }}

    @classmethod
    def from_dict(cls, d: dict) -> "{d["entity_class"]}":
        return cls(
            {d["entity_field"]}=d["{d["entity_field"]}"],
            data=d.get("data", {{}}),
        )
'''

    def _models_helpers(self, d: dict) -> str:
        return f'''"""
Helper functions for {d["models_pkg"]}.

Bug 1: Imports {d["circular_func"]} from {d["api_pkg"]}.formatters,
creating a circular dependency:
  {d["models_pkg"]} -> {d["api_pkg"]} -> {d["core_pkg"]} -> {d["models_pkg"]}

Fix: Import from {d["utils_pkg"]}.formatters instead (where it should live).
"""
# Bug 1: circular import — {d["models_pkg"]} should NOT import from {d["api_pkg"]}
from {d["api_pkg"]}.formatters import {d["circular_func"]}
from {d["models_pkg"]}.entities import {d["entity_class"]}


def serialize_entity(entity: {d["entity_class"]}) -> str:
    """Serialize an entity to a formatted string."""
    raw = entity.to_dict()
    return {d["circular_func"]}(raw)


def validate_entity(entity: {d["entity_class"]}) -> bool:
    """Validate that an entity has required fields."""
    return bool(entity.{d["entity_field"]})
'''

    def _models_setup(self, d: dict) -> str:
        return f'''[metadata]
name = {d["models_pkg"]}
version = 1.1.0

[options]
packages = {d["models_pkg"]}
python_requires = >=3.9
install_requires =
    {d["core_pkg"]}>=1.0
'''

    # ------------------------------------------------------------------
    # API package
    # ------------------------------------------------------------------
    def _api_init(self, d: dict) -> str:
        return f'''"""
{d["api_pkg"]} package — REST/API endpoints.
"""
'''

    def _api_endpoints(self, d: dict) -> str:
        return f'''"""
API endpoint definitions.
"""
from {d["core_pkg"]}.base import {d["base_class"]}
from {d["models_pkg"]}.entities import {d["entity_class"]}
from {d["api_pkg"]}.formatters import {d["circular_func"]}


def get_entity(entity_id: str) -> dict:
    """Retrieve and format an entity."""
    entity = {d["entity_class"]}({d["entity_field"]}=entity_id)
    raw = entity.to_dict()
    return {d["circular_func"]}(raw)


def list_entities() -> list[dict]:
    """List all entities (stub)."""
    return []
'''

    def _api_formatters(self, d: dict) -> str:
        return f'''"""
Response formatters for {d["api_pkg"]}.

The {d["circular_func"]}() function is defined here but SHOULD live in
{d["utils_pkg"]}.formatters to avoid the circular dependency with {d["models_pkg"]}.
"""
import json


def {d["circular_func"]}(data: dict) -> str:
    """Format a response dict as a JSON string with standard fields."""
    output = {{
        "status": "ok",
        "data": data,
        "version": "1.0",
    }}
    return json.dumps(output, indent=2)


def format_error(message: str, code: int = 500) -> str:
    """Format an error response."""
    output = {{
        "status": "error",
        "message": message,
        "code": code,
    }}
    return json.dumps(output, indent=2)
'''

    def _api_setup(self, d: dict) -> str:
        return f'''[metadata]
name = {d["api_pkg"]}
version = 1.0.0

[options]
packages = {d["api_pkg"]}
python_requires = >=3.9
install_requires =
    {d["core_pkg"]}>=1.0
    {d["models_pkg"]}>=1.0
'''

    # ------------------------------------------------------------------
    # Worker package (with moved function bug)
    # ------------------------------------------------------------------
    def _worker_init(self, d: dict) -> str:
        return f'''"""
{d["worker_pkg"]} package — background job processing.
"""
'''

    def _worker_tasks(self, d: dict) -> str:
        return f'''"""
Background tasks for {d["worker_pkg"]}.

Bug 3: Imports {d["moved_func"]} from {d["core_pkg"]}.processing, but that
function was moved to {d["utils_pkg"]}.processing in v{d["utils_correct_pin"]}.

Fix: Change import to `from {d["utils_pkg"]}.processing import {d["moved_func"]}`
"""
from {d["core_pkg"]}.base import {d["base_class"]}
# Bug 3: {d["moved_func"]} was moved to {d["utils_pkg"]}.processing
from {d["core_pkg"]}.processing import {d["moved_func"]}


class {d["worker_helper"].title().replace("_", "")}Task({d["base_class"]}):
    """Background task that processes items."""

    def __init__(self, name: str = "batch"):
        super().__init__(name)
        self.results = []

    def run(self, data: dict) -> dict:
        """Process a batch of items."""
        self.initialize()
        items = data.get("items", [])
        processed = []
        for item in items:
            result = {d["moved_func"]}(item)
            processed.append(result)
        self.results.extend(processed)
        return {{"processed": len(processed), "results": processed}}


def {d["worker_helper"]}(items: list[dict]) -> list[dict]:
    """Convenience function to process a batch."""
    task = {d["worker_helper"].title().replace("_", "")}Task()
    result = task.run({{"items": items}})
    return result["results"]
'''

    def _worker_setup(self, d: dict) -> str:
        return f'''[metadata]
name = {d["worker_pkg"]}
version = 1.0.0

[options]
packages = {d["worker_pkg"]}
python_requires = >=3.9
install_requires =
    {d["core_pkg"]}>=1.0
'''

    # ------------------------------------------------------------------
    # Utils package (with stale version pin)
    # ------------------------------------------------------------------
    def _utils_init(self, d: dict) -> str:
        return f'''"""
{d["utils_pkg"]} package — shared utilities.
"""
'''

    def _utils_processing(self, d: dict) -> str:
        return f'''"""
Processing utilities for {d["utils_pkg"]}.

Contains {d["moved_func"]}() which was moved here from {d["core_pkg"]}.processing
in v{d["utils_correct_pin"]}.
"""
from {d["core_pkg"]}.base import {d["base_class"]}


def {d["moved_func"]}(item: dict) -> dict:
    """Process a single item and return the result.

    This function was moved from {d["core_pkg"]}.processing in v{d["utils_correct_pin"]}.
    """
    result = dict(item)
    result["processed"] = True
    result["processor"] = "{d["utils_pkg"]}.processing.{d["moved_func"]}"
    return result


def batch_process(items: list[dict]) -> list[dict]:
    """Process multiple items."""
    return [{d["moved_func"]}(item) for item in items]
'''

    def _utils_formatters(self, d: dict) -> str:
        return f'''"""
Formatting utilities for {d["utils_pkg"]}.

This is where {d["circular_func"]}() should be imported from to avoid
circular dependencies with {d["api_pkg"]}.
"""
import json


def {d["circular_func"]}(data: dict) -> str:
    """Format a response dict as a JSON string with standard fields.

    This is the canonical location for this function.
    {d["api_pkg"]}.formatters should re-export from here.
    """
    output = {{
        "status": "ok",
        "data": data,
        "version": "1.0",
    }}
    return json.dumps(output, indent=2)
'''

    def _utils_setup(self, d: dict) -> str:
        return f'''[metadata]
name = {d["utils_pkg"]}
version = 1.1.0

[options]
packages = {d["utils_pkg"]}
python_requires = >=3.9
install_requires =
    {d["core_pkg"]}=={d["utils_stale_pin"]}
'''

    # ------------------------------------------------------------------
    # Changelog
    # ------------------------------------------------------------------
    def _changelog(self, d: dict) -> str:
        return f'''# Changelog

## {d["core_pkg"]} v{d["core_version"]}
- Added `{d["base_class"]}` class in `{d["core_pkg"]}.base`
- Moved `{d["moved_func"]}()` from `{d["core_pkg"]}.processing` to `{d["utils_pkg"]}.processing`

## {d["core_pkg"]} v{d["utils_stale_pin"]}
- Initial release with `{d["moved_func"]}()` in `{d["core_pkg"]}.processing`
- Basic validation and normalization utilities

## {d["models_pkg"]} v1.1.0
- Added `{d["entity_class"]}` entity
- Added `helpers.py` with `serialize_entity()` (requires `{d["circular_func"]}`)

## {d["api_pkg"]} v1.0.0
- REST endpoint definitions
- Response formatters including `{d["circular_func"]}()`

## {d["utils_pkg"]} v1.1.0
- Received `{d["moved_func"]}()` from `{d["core_pkg"]}.processing`
- Added `{d["circular_func"]}()` in `{d["utils_pkg"]}.formatters`
- NOTE: `setup.cfg` still pins `{d["core_pkg"]}=={d["utils_stale_pin"]}` — needs update to `>={d["utils_correct_pin"]}`

## {d["worker_pkg"]} v1.0.0
- Background job processing
- NOTE: Still imports `{d["moved_func"]}` from `{d["core_pkg"]}.processing` — needs update
'''

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def _test_imports(self, d: dict) -> str:
        return f'''"""
Tests for import validity and circular dependency detection.
"""
import importlib
import sys
import pytest


def _fresh_import(module_name: str):
    """Import a module fresh (remove from cache first)."""
    # Remove all related modules from cache
    to_remove = [k for k in sys.modules if k.startswith(module_name.split(".")[0])]
    for k in to_remove:
        del sys.modules[k]
    return importlib.import_module(module_name)


class TestNoCircularImports:
    """Bug 1: models must not import from api (circular dependency)."""

    def test_models_helpers_no_api_import(self):
        """models.helpers should import from utils.formatters, not api.formatters."""
        import ast
        with open("{d["models_pkg"]}/helpers.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module and node.module.startswith("{d["api_pkg"]}.")), (
                    f"{{node.module}} import in {d["models_pkg"]}/helpers.py creates "
                    f"circular dependency. Import from {d["utils_pkg"]} instead."
                )

    def test_models_imports_successfully(self):
        """After fixing the circular import, models should import cleanly."""
        # Clear module cache
        to_remove = [k for k in list(sys.modules.keys())
                     if k.startswith(("{d["models_pkg"]}", "{d["api_pkg"]}", "{d["core_pkg"]}", "{d["utils_pkg"]}"))]
        for k in to_remove:
            del sys.modules[k]
        mod = importlib.import_module("{d["models_pkg"]}.helpers")
        assert hasattr(mod, "serialize_entity")
        assert hasattr(mod, "{d["circular_func"]}")

    def test_dependency_graph_acyclic(self):
        """Verify no circular dependencies exist in the import graph."""
        import ast
        packages = ["{d["core_pkg"]}", "{d["models_pkg"]}", "{d["api_pkg"]}", "{d["worker_pkg"]}", "{d["utils_pkg"]}"]
        # Build adjacency list from imports
        graph = {{pkg: set() for pkg in packages}}
        for pkg in packages:
            for suffix in ["__init__", "helpers", "entities", "endpoints", "formatters",
                           "tasks", "processing", "base"]:
                path = f"{{pkg}}/{{suffix}}.py"
                try:
                    with open(path) as f:
                        source = f.read()
                except FileNotFoundError:
                    continue
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        dep_pkg = node.module.split(".")[0]
                        if dep_pkg in packages and dep_pkg != pkg:
                            graph[pkg].add(dep_pkg)

        # Detect cycles using DFS
        visited = set()
        in_stack = set()
        def has_cycle(node):
            visited.add(node)
            in_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor in in_stack:
                    return True
                if neighbor not in visited and has_cycle(neighbor):
                    return True
            in_stack.discard(node)
            return False

        for pkg in packages:
            if pkg not in visited:
                assert not has_cycle(pkg), (
                    f"Circular dependency detected involving {{pkg}}. "
                    f"Graph: {{{{k: sorted(v) for k, v in graph.items()}}}}"
                )


class TestMovedFunction:
    """Bug 3: worker must import {d["moved_func"]} from utils, not core."""

    def test_worker_imports_from_utils(self):
        """worker/tasks.py should import from utils.processing, not core.processing."""
        import ast
        with open("{d["worker_pkg"]}/tasks.py") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.names and any(a.name == "{d["moved_func"]}" for a in node.names):
                    assert node.module == "{d["utils_pkg"]}.processing", (
                        f"{d["moved_func"]} must be imported from "
                        f"{d["utils_pkg"]}.processing, not {{node.module}}"
                    )

    def test_worker_task_runs(self):
        """After fixing the import, the worker task should execute."""
        to_remove = [k for k in list(sys.modules.keys())
                     if k.startswith(("{d["worker_pkg"]}", "{d["core_pkg"]}", "{d["utils_pkg"]}"))]
        for k in to_remove:
            del sys.modules[k]
        mod = importlib.import_module("{d["worker_pkg"]}.tasks")
        result = mod.{d["worker_helper"]}([{{"id": 1, "type": "test"}}])
        assert len(result) == 1
        assert result[0]["processed"] is True
'''

    def _test_versions(self, d: dict) -> str:
        return f'''"""
Tests for version constraint consistency across the monorepo.
"""
import configparser
import os
import re
import pytest


def _parse_setup_cfg(path: str) -> dict:
    """Parse a setup.cfg and return metadata + dependencies."""
    config = configparser.ConfigParser()
    config.read(path)
    result = {{
        "name": config.get("metadata", "name", fallback="unknown"),
        "version": config.get("metadata", "version", fallback="0.0.0"),
        "deps": [],
    }}
    if config.has_option("options", "install_requires"):
        raw = config.get("options", "install_requires")
        for line in raw.strip().splitlines():
            line = line.strip()
            if line:
                result["deps"].append(line)
    return result


class TestVersionPins:
    """Bug 2: utils must pin core>={d["utils_correct_pin"]}, not core=={d["utils_stale_pin"]}."""

    def test_utils_core_pin_not_stale(self):
        """utils/setup.cfg must require core>={d["utils_correct_pin"]}."""
        cfg = _parse_setup_cfg("{d["utils_pkg"]}/setup.cfg")
        core_deps = [d for d in cfg["deps"] if d.startswith("{d["core_pkg"]}")]
        assert len(core_deps) == 1, f"Expected 1 {d["core_pkg"]} dep, got {{core_deps}}"
        dep = core_deps[0]
        # Must NOT be ==1.0 (stale pin)
        assert "=={d["utils_stale_pin"]}" not in dep, (
            f"{d["utils_pkg"]} still has stale pin: {{dep}}. "
            f"Change to {d["core_pkg"]}>={d["utils_correct_pin"]}"
        )
        # Must be >= the correct version
        assert ">=" in dep, (
            f"{d["utils_pkg"]} {d["core_pkg"]} dep must use >=, got: {{dep}}"
        )

    def test_all_versions_satisfiable(self):
        """All version constraints must be satisfiable together."""
        packages = {{}}
        for pkg in ["{d["core_pkg"]}", "{d["models_pkg"]}", "{d["api_pkg"]}", "{d["worker_pkg"]}", "{d["utils_pkg"]}"]:
            cfg_path = f"{{pkg}}/setup.cfg"
            if os.path.exists(cfg_path):
                packages[pkg] = _parse_setup_cfg(cfg_path)

        # Check each dependency is satisfiable
        for pkg_name, pkg_info in packages.items():
            for dep in pkg_info["deps"]:
                # Parse dependency spec
                match = re.match(r"([a-zA-Z_]+)(.*)", dep)
                if not match:
                    continue
                dep_name = match.group(1)
                dep_spec = match.group(2).strip()

                if dep_name in packages:
                    dep_version = packages[dep_name]["version"]
                    dep_parts = [int(x) for x in dep_version.split(".")]

                    if dep_spec.startswith(">="):
                        min_ver = dep_spec[2:]
                        min_parts = [int(x) for x in min_ver.split(".")]
                        assert dep_parts >= min_parts, (
                            f"{{pkg_name}} requires {{dep}}, but {{dep_name}} is v{{dep_version}}"
                        )
                    elif dep_spec.startswith("=="):
                        pin_ver = dep_spec[2:]
                        pin_parts = [int(x) for x in pin_ver.split(".")]
                        assert dep_parts[:len(pin_parts)] == pin_parts, (
                            f"{{pkg_name}} requires {{dep}}, but {{dep_name}} is v{{dep_version}}"
                        )
'''
