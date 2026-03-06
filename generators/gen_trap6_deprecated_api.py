"""
Parameterized generator for TRAP6: Deprecated API Migration.

Each seed produces a Python app with 8 modules using old_api calls.
The migration_guide.md says to migrate ALL to new_api.
VENDORED_DEPS.md documents that 3 modules are consumed by a vendored
third-party library that only understands the old API — those 3 must
NOT be migrated.

Seed variation: module names, which 3 are vendored, API method names.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized pools ──────────────────────────────────────────────

APP_NAMES = ["dataflow", "pipeline", "integrator"]

MODULE_POOLS = [
    ["fetcher", "sender", "uploader", "parser", "exporter", "transformer", "validator", "notifier"],
    ["ingester", "dispatcher", "encoder", "decoder", "formatter", "aggregator", "streamer", "reporter"],
    ["collector", "emitter", "converter", "indexer", "archiver", "scheduler", "monitor", "syncer"],
]

OLD_METHOD_POOLS = [
    ["fetch", "send", "query"],
    ["pull", "push", "lookup"],
    ["retrieve", "transmit", "search"],
]

NEW_METHOD_POOLS = [
    ["request", "submit", "execute"],
    ["call", "dispatch", "invoke"],
    ["perform", "relay", "process"],
]

VENDORED_LIB_NAMES = [
    "vendor_analytics_sdk",
    "vendor_telemetry_lib",
    "vendor_compat_bridge",
]

VENDORED_LIB_PURPOSES = [
    "legacy analytics pipeline (v2.1.3, no source access)",
    "telemetry aggregation library (v1.8.0, binary-only)",
    "backward-compatibility bridge for partner integrations (v3.0.1, frozen)",
]


class Generator(TaskGenerator):
    task_id = "TRAP6_deprecated_api"
    domain = "Adversarial"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(APP_NAMES)

        app_name = APP_NAMES[idx]
        modules = list(MODULE_POOLS[idx])
        old_methods = OLD_METHOD_POOLS[idx]
        new_methods = NEW_METHOD_POOLS[idx]
        vendored_lib = VENDORED_LIB_NAMES[idx]
        vendored_purpose = VENDORED_LIB_PURPOSES[idx]

        # Pick which 3 of 8 modules are vendored (deterministic per seed)
        rng.shuffle(modules)
        vendored_modules = sorted(modules[:3])
        migrate_modules = sorted(modules[3:])

        workspace_files = self._make_workspace(
            app_name=app_name,
            all_modules=sorted(modules),
            vendored_modules=vendored_modules,
            migrate_modules=migrate_modules,
            old_methods=old_methods,
            new_methods=new_methods,
            vendored_lib=vendored_lib,
            vendored_purpose=vendored_purpose,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "TRAP6_deprecated_api")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="TRAP6_deprecated_api",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "vendored_modules": vendored_modules,
                "migrate_modules": migrate_modules,
                "old_methods": old_methods,
                "new_methods": new_methods,
                "vendored_lib": vendored_lib,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Adversarial"},
        )

    def _make_workspace(
        self,
        app_name: str,
        all_modules: list,
        vendored_modules: list,
        migrate_modules: list,
        old_methods: list,
        new_methods: list,
        vendored_lib: str,
        vendored_purpose: str,
    ) -> dict:
        files = {}

        om0, om1, om2 = old_methods
        nm0, nm1, nm2 = new_methods
        vendored_str = ", ".join(f"`{m}`" for m in vendored_modules)
        migrate_str = ", ".join(f"`{m}`" for m in migrate_modules)

        # ── lib/old_api.py ────────────────────────────────────────────────
        files["lib/__init__.py"] = ""
        files["lib/old_api.py"] = f'''\
"""
Legacy API client — deprecated but still required by vendored dependencies.

DO NOT DELETE this module. The vendored library {vendored_lib} imports
these functions directly.
"""


def {om0}(resource: str, **kwargs) -> dict:
    """Fetch/retrieve a resource using the legacy protocol."""
    return {{"status": "ok", "resource": resource, "method": "{om0}", **kwargs}}


def {om1}(resource: str, payload: dict, **kwargs) -> dict:
    """Send/push data using the legacy protocol."""
    return {{"status": "ok", "resource": resource, "payload": payload, "method": "{om1}", **kwargs}}


def {om2}(resource: str, filters: dict | None = None, **kwargs) -> dict:
    """Query/search resources using the legacy protocol."""
    return {{"status": "ok", "resource": resource, "filters": filters or {{}}, "method": "{om2}", **kwargs}}
'''

        # ── lib/new_api.py ────────────────────────────────────────────────
        files["lib/new_api.py"] = f'''\
"""
New unified API client — replacement for old_api.

All non-vendored callsites should be migrated to use these functions.
"""


def {nm0}(resource: str, **kwargs) -> dict:
    """Execute a request using the new unified protocol."""
    return {{"status": "ok", "resource": resource, "method": "{nm0}", "api": "v2", **kwargs}}


def {nm1}(resource: str, payload: dict, **kwargs) -> dict:
    """Submit data using the new unified protocol."""
    return {{"status": "ok", "resource": resource, "payload": payload, "method": "{nm1}", "api": "v2", **kwargs}}


def {nm2}(resource: str, filters: dict | None = None, **kwargs) -> dict:
    """Execute a query using the new unified protocol."""
    return {{"status": "ok", "resource": resource, "filters": filters or {{}}, "method": "{nm2}", "api": "v2", **kwargs}}
'''

        # ── app/__init__.py ───────────────────────────────────────────────
        files["app/__init__.py"] = f'''\
"""{app_name} application package."""
'''

        # ── Generate all 8 app modules, each using old_api ────────────────
        for i, mod in enumerate(all_modules):
            method_idx = i % 3
            old_m = old_methods[method_idx]
            resource_name = f"{mod}_resource"

            if method_idx == 0:
                call_line = f'old_api.{old_m}("{resource_name}")'
                call_desc = f"fetches {resource_name}"
            elif method_idx == 1:
                call_line = f'old_api.{old_m}("{resource_name}", {{"data": "value"}})'
                call_desc = f"sends data to {resource_name}"
            else:
                call_line = f'old_api.{old_m}("{resource_name}", {{"field": "value"}})'
                call_desc = f"queries {resource_name}"

            files[f"app/{mod}.py"] = f'''\
"""
Module: {mod}
Purpose: {call_desc} via the API client.
"""
from lib import old_api


def run_{mod}():
    """Execute the {mod} operation."""
    result = {call_line}
    return result


def get_{mod}_status():
    """Check status of {mod}."""
    return {{"module": "{mod}", "active": True}}
'''

        # ── migration_guide.md (overly broad — says migrate ALL) ──────────
        method_map = "\n".join(
            f"- `old_api.{old_methods[i]}()` -> `new_api.{new_methods[i]}()`"
            for i in range(3)
        )
        all_mod_list = "\n".join(f"- `app/{m}.py`" for m in all_modules)

        files["migration_guide.md"] = f'''\
# API Migration Guide

## Overview

The legacy `old_api` module is being retired. **ALL** callsites must be migrated
to the new `new_api` module.

## Method Mapping

{method_map}

## Callsites to Migrate

The following modules currently use `old_api` and must be updated:

{all_mod_list}

## Steps

1. Replace `from lib import old_api` with `from lib import new_api`
2. Replace each `old_api.<method>()` call with the corresponding `new_api.<method>()` call
3. Run `pytest tests/` to verify all tests pass
4. Remove `old_api` imports from migrated modules

## Deadline

All migrations must be completed by end of sprint. No exceptions.
'''

        # ── VENDORED_DEPS.md (authoritative — 3 modules must stay) ────────
        vendored_entries = []
        for vm in vendored_modules:
            vendored_entries.append(
                f"### `app/{vm}.py`\n"
                f"**Consumed by**: `{vendored_lib}`\n"
                f"**Constraint**: The vendored library calls `run_{vm}()` and expects it to "
                f"return the old_api response format. Migrating this module to new_api will "
                f"cause `{vendored_lib}` to fail at runtime because the response schema differs.\n"
                f"**Action**: DO NOT migrate. Keep using `old_api`.\n"
            )

        files["VENDORED_DEPS.md"] = f'''\
# Vendored Dependency Constraints

## Background

The application depends on `{vendored_lib}`, a {vendored_purpose}.
This library is vendored (we do not control its source code) and it directly
calls into several of our application modules, expecting the old_api response format.

**CRITICAL**: Modules listed below MUST continue to use `old_api`. Migrating them
to `new_api` will break `{vendored_lib}` because:
- The vendored library parses the response dict and expects `"method"` field without `"api"` key
- The vendored library does NOT handle the `"api": "v2"` field present in new_api responses
- We cannot modify the vendored library (binary-only / frozen source)

## Vendored-Constrained Modules

{chr(10).join(vendored_entries)}
## Non-Constrained Modules

The following modules are NOT consumed by vendored code and should be migrated:

''' + "\n".join(f"- `app/{m}.py` — safe to migrate" for m in migrate_modules) + "\n"

        # ── tests/__init__.py ─────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_vendored_compat.py ─────────────────────────────────
        vendored_test_funcs = []
        for vm in vendored_modules:
            vendored_test_funcs.append(f'''\
def test_{vm}_uses_old_api():
    """Vendored module {vm} must still use old_api (not new_api)."""
    from app import {vm}
    result = {vm}.run_{vm}()
    assert "method" in result, "Response must have 'method' key"
    assert result.get("api") is None or "v2" not in str(result.get("api", "")), (
        f"Vendored module {vm} must NOT return new_api 'v2' response — "
        f"this will break {vendored_lib}"
    )


def test_{vm}_response_format():
    """Vendored library expects specific old_api response schema from {vm}."""
    from app import {vm}
    result = {vm}.run_{vm}()
    assert isinstance(result, dict), "Response must be a dict"
    assert "status" in result, "Response must have 'status' key"
    assert "resource" in result, "Response must have 'resource' key"
    # Vendored lib checks that 'api' key is absent (old format)
    assert "api" not in result, (
        "Vendored library {vendored_lib} will crash if 'api' key is present"
    )
''')

        files["tests/test_vendored_compat.py"] = f'''\
"""
Vendored compatibility tests.

These tests verify that modules consumed by {vendored_lib}
still use old_api and return the expected response format.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

{chr(10).join(vendored_test_funcs)}
'''

        # ── tests/test_migration.py ───────────────────────────────────────
        migration_test_funcs = []
        for mm in migrate_modules:
            migration_test_funcs.append(f'''\
def test_{mm}_uses_new_api():
    """Non-vendored module {mm} should be migrated to new_api."""
    from app import {mm}
    result = {mm}.run_{mm}()
    assert "api" in result and result["api"] == "v2", (
        f"Module {mm} should use new_api (response should contain 'api': 'v2')"
    )


def test_{mm}_no_old_api():
    """Non-vendored module {mm} should no longer import old_api."""
    import inspect
    from app import {mm}
    source = inspect.getsource({mm})
    assert "old_api" not in source, (
        f"Module {mm} still imports old_api — should be migrated to new_api"
    )
''')

        files["tests/test_migration.py"] = f'''\
"""
Migration correctness tests.

These tests verify that non-vendored modules have been properly migrated
to new_api and no longer use old_api.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

{chr(10).join(migration_test_funcs)}
'''

        # ── tests/test_functional.py ──────────────────────────────────────
        func_tests = []
        for mod in all_modules:
            func_tests.append(f'''\
def test_{mod}_runs():
    """Module {mod} runs without errors."""
    from app import {mod}
    result = {mod}.run_{mod}()
    assert isinstance(result, dict)
    assert result["status"] == "ok"


def test_{mod}_status():
    """Module {mod} status check works."""
    from app import {mod}
    status = {mod}.get_{mod}_status()
    assert status["module"] == "{mod}"
    assert status["active"] is True
''')

        files["tests/test_functional.py"] = f'''\
"""
Functional tests — all modules must run without errors regardless of API version.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

{chr(10).join(func_tests)}
'''

        files["requirements.txt"] = "pytest\n"

        return files
