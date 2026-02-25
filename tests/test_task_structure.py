"""
Validates all tasks have required files and correct structure.

Run: python -m pytest tests/test_task_structure.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks")

# Required fields in task.yaml (base schema)
REQUIRED_YAML_FIELDS = [
    "task_id",
    "domain",
    "network",
    "time_limit_sec",
    "seeds",
]

# Enhanced schema fields (v2)
ENHANCED_YAML_FIELDS = [
    "difficulty",
    "languages",
    "tags",
    "workspace_file_count",
    "lines_changed_expected",
    "parameterized",
]

VALID_DIFFICULTIES = {"easy", "medium", "hard", "expert"}


def _get_all_task_names() -> list[str]:
    """Discover all task directories containing task.yaml."""
    tasks = []
    if not os.path.isdir(TASKS_DIR):
        return tasks
    for entry in sorted(os.listdir(TASKS_DIR)):
        task_path = os.path.join(TASKS_DIR, entry)
        if os.path.isdir(task_path) and os.path.isfile(os.path.join(task_path, "task.yaml")):
            tasks.append(entry)
    return tasks


def _parse_yaml_value(val: str):
    """Parse a scalar YAML value string into a Python object."""
    val = val.strip()
    # Boolean
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    # Inline list: [0, 1, 2] or [python] or [api, hidden-requirements]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        items = [item.strip().strip('"').strip("'") for item in inner.split(",")]
        parsed = []
        for item in items:
            try:
                parsed.append(int(item))
            except ValueError:
                parsed.append(item)
        return parsed
    # Integer
    try:
        return int(val)
    except ValueError:
        pass
    # Float
    try:
        return float(val)
    except ValueError:
        pass
    # String (strip optional quotes)
    return val.strip('"').strip("'")


def _load_task_yaml(task_name: str) -> dict:
    """Load task.yaml as a dict. Returns empty dict on parse error."""
    yaml_path = os.path.join(TASKS_DIR, task_name, "task.yaml")
    try:
        import yaml  # type: ignore[import]
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        pass
    except Exception:
        return {}

    # Fall back to basic key: value parsing when PyYAML is not installed
    result: dict = {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, _, val = line.partition(":")
                    result[key.strip()] = _parse_yaml_value(val)
    except Exception:
        return {}
    return result


ALL_TASKS = _get_all_task_names()


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_required_files_exist(task_name: str) -> None:
    """Every task must have: task.yaml, spec.md, brief.md, grade.sh, setup.sh, workspace/."""
    task_dir = os.path.join(TASKS_DIR, task_name)

    required_files = ["task.yaml", "spec.md", "brief.md", "grade.sh", "setup.sh"]
    for fname in required_files:
        fpath = os.path.join(task_dir, fname)
        assert os.path.isfile(fpath), (
            f"{task_name}: missing required file '{fname}' in {task_dir}"
        )

    workspace = os.path.join(task_dir, "workspace")
    assert os.path.isdir(workspace), (
        f"{task_name}: missing required directory 'workspace/' in {task_dir}"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_grade_sh_is_executable(task_name: str) -> None:
    """grade.sh must have executable permission."""
    grade_sh = os.path.join(TASKS_DIR, task_name, "grade.sh")
    if not os.path.isfile(grade_sh):
        pytest.skip(f"{task_name}: grade.sh not found (caught by test_required_files_exist)")
    assert os.access(grade_sh, os.X_OK), (
        f"{task_name}: grade.sh is not executable. Run: chmod +x {grade_sh}"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_task_yaml_base_schema(task_name: str) -> None:
    """task.yaml must contain all required base schema fields."""
    config = _load_task_yaml(task_name)
    assert config, f"{task_name}: task.yaml is empty or failed to parse"

    for field in REQUIRED_YAML_FIELDS:
        assert field in config, (
            f"{task_name}: task.yaml missing required field '{field}'"
        )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_task_yaml_enhanced_schema(task_name: str) -> None:
    """task.yaml should contain all enhanced schema (v2) fields."""
    config = _load_task_yaml(task_name)
    if not config:
        pytest.skip(f"{task_name}: task.yaml is empty or failed to parse")

    missing = [f for f in ENHANCED_YAML_FIELDS if f not in config]
    assert not missing, (
        f"{task_name}: task.yaml missing enhanced schema fields: {missing}"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_task_yaml_task_id_matches_dirname(task_name: str) -> None:
    """task.yaml task_id must match the directory name."""
    config = _load_task_yaml(task_name)
    if "task_id" not in config:
        pytest.skip(f"{task_name}: task.yaml missing task_id field")

    assert str(config["task_id"]) == task_name, (
        f"{task_name}: task.yaml task_id='{config['task_id']}' does not match directory name '{task_name}'"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_task_yaml_difficulty_valid(task_name: str) -> None:
    """difficulty field must be one of: easy, medium, hard, expert."""
    config = _load_task_yaml(task_name)
    if "difficulty" not in config:
        pytest.skip(f"{task_name}: no 'difficulty' field in task.yaml")

    difficulty = str(config["difficulty"])
    assert difficulty in VALID_DIFFICULTIES, (
        f"{task_name}: invalid difficulty='{difficulty}', must be one of {sorted(VALID_DIFFICULTIES)}"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_task_yaml_time_limit_positive(task_name: str) -> None:
    """time_limit_sec must be a positive integer."""
    config = _load_task_yaml(task_name)
    if "time_limit_sec" not in config:
        pytest.skip(f"{task_name}: no 'time_limit_sec' field in task.yaml")

    try:
        tl = int(config["time_limit_sec"])
    except (ValueError, TypeError):
        pytest.fail(f"{task_name}: time_limit_sec must be an integer, got '{config['time_limit_sec']}'")

    assert tl > 0, f"{task_name}: time_limit_sec={tl} must be positive"


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_task_yaml_seeds_is_list(task_name: str) -> None:
    """seeds must be a non-empty list of integers."""
    config = _load_task_yaml(task_name)
    if "seeds" not in config:
        pytest.skip(f"{task_name}: no 'seeds' field in task.yaml")

    seeds = config["seeds"]
    assert isinstance(seeds, list), (
        f"{task_name}: seeds must be a list, got {type(seeds)}"
    )
    assert len(seeds) > 0, f"{task_name}: seeds list must not be empty"
    for s in seeds:
        assert isinstance(s, int), (
            f"{task_name}: all seeds must be integers, got {s!r} (type={type(s)})"
        )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_spec_md_not_empty(task_name: str) -> None:
    """spec.md must be non-empty."""
    spec_path = os.path.join(TASKS_DIR, task_name, "spec.md")
    if not os.path.isfile(spec_path):
        pytest.skip(f"{task_name}: spec.md not found")

    content = open(spec_path, encoding="utf-8").read().strip()
    assert content, f"{task_name}: spec.md is empty"


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_brief_md_not_empty(task_name: str) -> None:
    """brief.md must be non-empty."""
    brief_path = os.path.join(TASKS_DIR, task_name, "brief.md")
    if not os.path.isfile(brief_path):
        pytest.skip(f"{task_name}: brief.md not found")

    content = open(brief_path, encoding="utf-8").read().strip()
    assert content, f"{task_name}: brief.md is empty"


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_workspace_has_files(task_name: str) -> None:
    """workspace/ directory must contain at least one file."""
    workspace = os.path.join(TASKS_DIR, task_name, "workspace")
    if not os.path.isdir(workspace):
        pytest.skip(f"{task_name}: workspace/ not found")

    all_files = []
    for root, dirs, files in os.walk(workspace):
        all_files.extend(files)

    assert len(all_files) > 0, (
        f"{task_name}: workspace/ directory is empty — tasks must have at least one workspace file"
    )
