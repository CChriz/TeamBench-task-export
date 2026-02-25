"""
Parameterized generator for S2: Dependency Conflict Trap.

Each seed produces:
  - Different package names (libfoo/libbar -> e.g. libauth/libcache)
  - Different utility package name (utils_pkg -> e.g. common_pkg)
  - Different function names and import paths
  - Different version numbers causing the conflict
  - Different specific fix needed (always: pin version >= 2.0 + patch import in pkg2_core)

The task structure stays the same: resolve a version conflict between two vendored
libraries where pkg2 uses a compat import that doesn't exist in utils v2.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Pool of realistic library name pairs
LIB_PAIRS = [
    ("libauth", "libcache"),
    ("libqueue", "libmetrics"),
    ("libstorage", "libnotify"),
    ("libgrpc", "libhttp"),
    ("libsearch", "libaudit"),
    ("libpayment", "libreport"),
    ("libtrack", "libmail"),
    ("libsync", "libalert"),
]

# Pool of utility package names
UTIL_PKG_NAMES = [
    "common_pkg",
    "core_utils",
    "shared_pkg",
    "base_lib",
    "helpers_pkg",
    "toolkit_pkg",
    "foundation_pkg",
    "support_pkg",
]

# Pool of process function name templates: (pkg1_func, pkg2_func)
FUNC_NAME_PAIRS = [
    ("process", "handle"),
    ("run", "execute"),
    ("transform", "convert"),
    ("validate", "check"),
    ("encode", "decode"),
    ("dispatch", "receive"),
    ("compute", "analyze"),
    ("publish", "consume"),
]

# Pool of version pairs: (pkg1_requires, pkg2_requires, actual_utils_version)
# pkg1 always needs >= 2.0, pkg2 always needs < 2.0 — this is the invariant conflict
VERSION_SCENARIOS = [
    ("1.2.0", "0.9.1", "1.5.0"),
    ("2.0.0", "1.3.2", "1.8.0"),
    ("1.5.0", "0.7.3", "1.4.0"),
    ("3.1.0", "1.1.0", "1.6.0"),
    ("2.3.0", "0.8.5", "1.9.0"),
    ("1.8.0", "1.2.4", "1.5.5"),
    ("2.1.0", "0.6.0", "1.7.0"),
    ("1.4.0", "1.0.1", "1.3.0"),
]

# Mode names used in transform return values
MODE_NAMES = [
    ("alpha", "beta"),
    ("primary", "secondary"),
    ("reader", "writer"),
    ("sender", "receiver"),
    ("master", "replica"),
    ("upstream", "downstream"),
    ("producer", "consumer"),
    ("leader", "follower"),
]


class Generator(TaskGenerator):
    task_id = "S2_dependency_conflict"
    domain = "software"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick all seed-specific names
        pkg1_name, pkg2_name = rng.choice(LIB_PAIRS)
        util_pkg_name = rng.choice(UTIL_PKG_NAMES)
        # util module name (the importable package inside util_pkg)
        util_module = util_pkg_name.replace("_pkg", "").replace("_lib", "")
        pkg1_func, pkg2_func = rng.choice(FUNC_NAME_PAIRS)
        pkg1_ver, pkg2_ver, actual_utils_ver = rng.choice(VERSION_SCENARIOS)
        mode1, mode2 = rng.choice(MODE_NAMES)

        # Fixed: utils v2 module path is always "utils_module.v2"
        # pkg1 uses: from {util_module}.v2 import helper
        # pkg2 (buggy) uses: from {util_module}.compat import helper
        # Fix: change pkg2 to use {util_module}.v2 as well

        # ── Generate vendor files ──

        # utils package __init__.py
        utils_init = f"# {util_module} package\n__version__ = '2.0.0'\n"

        # utils v2 module
        utils_v2 = f"""class helper:
    @staticmethod
    def transform(data, mode="default"):
        return {{"result": data, "mode": mode, "version": "2.0"}}
"""

        # pkg1 core (correct — uses v2)
        pkg1_core = f"""from {util_module}.v2 import helper

def {pkg1_func}(data):
    return helper.transform(data, mode="{mode1}")
"""

        # pkg2 core (buggy — uses compat which doesn't exist in v2)
        pkg2_core = f"""from {util_module}.compat import helper

def {pkg2_func}(data):
    return helper.transform(data, mode="{mode2}")
"""

        # setup.py for utils_pkg
        utils_setup = f"""from setuptools import setup, find_packages
setup(
    name="{util_module}",
    version="2.0.0",
    packages=find_packages(),
)
"""

        # setup.py for pkg1
        pkg1_setup = f"""from setuptools import setup
setup(
    name="{pkg1_name}",
    version="{pkg1_ver}",
    py_modules=["{pkg1_name}_core"],
    install_requires=["{util_module}>=2.0,<3.0"],
)
"""

        # setup.py for pkg2 (requires old utils < 2.0 — the conflict)
        pkg2_setup = f"""from setuptools import setup
setup(
    name="{pkg2_name}",
    version="{pkg2_ver}",
    py_modules=["{pkg2_name}_core"],
    install_requires=["{util_module}>=1.0,<2.0"],
)
"""

        # requirements.txt (pinned to old version — must be fixed to >= 2.0)
        requirements_txt = f"{util_module}=={actual_utils_ver}\n"

        # Makefile
        makefile = f""".PHONY: test install

install:
\tpip install -r requirements.txt
\tpip install -e vendor/{pkg1_name} -e vendor/{pkg2_name}

test: install
\tpython -m pytest tests/ -q
"""

        # Test file
        test_file = f"""import json


def test_{pkg1_name.replace("-", "_")}_import():
    from {pkg1_name}_core import {pkg1_func}
    result = {pkg1_func}("hello")
    assert result["mode"] == "{mode1}"


def test_{pkg2_name.replace("-", "_")}_import():
    from {pkg2_name}_core import {pkg2_func}
    result = {pkg2_func}("world")
    assert result["mode"] == "{mode2}"


def test_utils_version():
    import {util_module}
    assert hasattr({util_module}, '__version__'), "{util_module} missing __version__"


def test_both_together():
    from {pkg1_name}_core import {pkg1_func}
    from {pkg2_name}_core import {pkg2_func}
    r1 = {pkg1_func}("x")
    r2 = {pkg2_func}("y")
    assert r1["version"] == r2["version"], "version mismatch between libs"
"""

        workspace_files = {
            f"vendor/{util_pkg_name}/utils/__init__.py": utils_init,
            f"vendor/{util_pkg_name}/utils/v2.py": utils_v2,
            f"vendor/{util_pkg_name}/setup.py": utils_setup,
            f"vendor/{pkg1_name}/{pkg1_name}_core.py": pkg1_core,
            f"vendor/{pkg1_name}/setup.py": pkg1_setup,
            f"vendor/{pkg2_name}/{pkg2_name}_core.py": pkg2_core,
            f"vendor/{pkg2_name}/setup.py": pkg2_setup,
            "requirements.txt": requirements_txt,
            "Makefile": makefile,
            "tests/test_integration.py": test_file,
        }

        expected = {
            "pkg1_name": pkg1_name,
            "pkg2_name": pkg2_name,
            "util_pkg_name": util_pkg_name,
            "util_module": util_module,
            "pkg1_func": pkg1_func,
            "pkg2_func": pkg2_func,
            "pkg1_ver": pkg1_ver,
            "pkg2_ver": pkg2_ver,
            "actual_utils_ver": actual_utils_ver,
            "mode1": mode1,
            "mode2": mode2,
            "fix_description": (
                f"Pin {util_module}==2.0.0 in requirements.txt and change "
                f"{pkg2_name}_core.py to import from {util_module}.v2 instead of {util_module}.compat"
            ),
            "required_utils_version": "2.0.0",
            "pkg2_buggy_import": f"{util_module}.compat",
            "pkg2_correct_import": f"{util_module}.v2",
        }

        spec_md = self._generate_spec(
            pkg1_name, pkg2_name, util_module, pkg1_ver, pkg2_ver,
            pkg1_func, pkg2_func,
        )
        brief_md = self._generate_brief(pkg1_name, pkg2_name)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_spec(
        self,
        pkg1: str, pkg2: str,
        util_module: str,
        pkg1_ver: str, pkg2_ver: str,
        pkg1_func: str, pkg2_func: str,
    ) -> str:
        return f"""# S2: Dependency Conflict Trap

## Goal
Fix the Python project so that `make test` passes.

## Hard Requirements

1. The project has a `Makefile` with a `test` target that runs `python -m pytest tests/ -q`.
2. The project depends on two libraries (provided as local packages in `vendor/`):
   - `{pkg1}=={pkg1_ver}` requires `{util_module}>=2.0,<3.0`
   - `{pkg2}=={pkg2_ver}` requires `{util_module}>=1.0,<2.0`
3. The version conflict must be resolved such that both `{pkg1}` and `{pkg2}` function correctly
   at runtime. Simply pinning `{util_module}` to the version range demanded by one library will
   break the other — the resolution requires both a version pin and a compatibility adjustment.
4. `requirements.txt` must list exact pinned versions.
5. No additional packages may be introduced.
6. All 4 test cases in `tests/test_integration.py` must pass.

## Deliverables
- Fixed code + `requirements.txt` in workspace.
- Verifier must confirm all constraints and produce attestation.
"""

    def _generate_brief(self, pkg1: str, pkg2: str) -> str:
        return f"""# S2: Dependency Conflict (Brief)

Fix the project so that `make test` passes.
The project has dependency version conflicts between `{pkg1}` and `{pkg2}`.
The Planner has the dependency resolution details.
Resolve the conflict and ensure all tests pass.
"""
