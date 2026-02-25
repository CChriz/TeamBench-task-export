"""
Grader correctness validation.

For each task, verifies:
1. The initial (buggy) workspace fails grading (no false positives)
2. Grade script produces valid score.json
3. Partial scores are in [0, 1]
4. Failure modes are strings

Run: python -m pytest tests/test_grader_correctness.py -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks")


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


def _has_static_workspace(task_name: str) -> bool:
    """Return True if the task has a static workspace directory."""
    ws = os.path.join(TASKS_DIR, task_name, "workspace")
    return os.path.isdir(ws)


def _grade_initial_workspace(task_name: str) -> dict:
    """
    Stage the initial workspace and run the grader.
    A stub passing attestation is written so grade_run proceeds past
    the attestation check to the actual task-specific grader.
    Returns the score dict.
    """
    from harness.run_all import setup_run, grade_run

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            run_id, run_dir, task_dir = setup_run(task_name, TASKS_DIR, tmpdir, seed=0)
        except Exception as e:
            return {
                "pass": False,
                "primary": {"success": 0},
                "secondary": {},
                "failure_modes": [f"setup_error: {e}"],
            }

        # Write a stub passing attestation so the real grader runs
        submission_dir = os.path.join(run_dir, "submission")
        os.makedirs(submission_dir, exist_ok=True)
        att_path = os.path.join(submission_dir, "attestation.json")
        with open(att_path, "w") as f:
            json.dump({"task_id": task_name, "verdict": "pass", "checklist": []}, f)

        try:
            score = grade_run(task_name, task_dir, run_dir)
        except Exception as e:
            score = {
                "pass": False,
                "primary": {"success": 0},
                "secondary": {},
                "failure_modes": [f"grader_error: {e}"],
            }
        return score


# Build the parametrize list at import time for pytest collection
ALL_TASKS = _get_all_task_names()


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_initial_workspace_fails_grader(task_name: str) -> None:
    """The initial (buggy) workspace must fail grading — no false positives."""
    if not _has_static_workspace(task_name):
        pytest.skip(f"{task_name}: no static workspace to grade")

    score = _grade_initial_workspace(task_name)
    assert not score.get("pass"), (
        f"{task_name}: initial buggy workspace passed grader — possible false positive. "
        f"Score: {score}"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_score_json_schema(task_name: str) -> None:
    """Grade script must produce a score.json with the correct schema."""
    if not _has_static_workspace(task_name):
        pytest.skip(f"{task_name}: no static workspace to grade")

    score = _grade_initial_workspace(task_name)

    # Required top-level fields
    assert "pass" in score, f"{task_name}: score.json missing 'pass' field. Got: {score}"
    assert isinstance(score["pass"], bool), (
        f"{task_name}: 'pass' must be bool, got {type(score['pass'])}"
    )

    # Primary field
    assert "primary" in score, f"{task_name}: score.json missing 'primary' field"
    assert isinstance(score["primary"], dict), (
        f"{task_name}: 'primary' must be a dict, got {type(score['primary'])}"
    )
    assert "success" in score["primary"], (
        f"{task_name}: 'primary' must contain 'success' key"
    )

    # Secondary field (optional but must be dict if present)
    if "secondary" in score:
        assert isinstance(score["secondary"], dict), (
            f"{task_name}: 'secondary' must be a dict, got {type(score['secondary'])}"
        )

    # Failure modes must be a list
    assert "failure_modes" in score, f"{task_name}: score.json missing 'failure_modes' field"
    assert isinstance(score["failure_modes"], list), (
        f"{task_name}: 'failure_modes' must be a list, got {type(score['failure_modes'])}"
    )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_partial_score_in_range(task_name: str) -> None:
    """Partial score must be in [0, 1] if present."""
    if not _has_static_workspace(task_name):
        pytest.skip(f"{task_name}: no static workspace to grade")

    score = _grade_initial_workspace(task_name)
    secondary = score.get("secondary", {})
    partial_score = secondary.get("partial_score")

    if partial_score is not None:
        assert isinstance(partial_score, (int, float)), (
            f"{task_name}: partial_score must be numeric, got {type(partial_score)}"
        )
        assert 0.0 <= partial_score <= 1.0, (
            f"{task_name}: partial_score={partial_score} is out of [0, 1]"
        )


@pytest.mark.parametrize("task_name", ALL_TASKS)
def test_failure_modes_are_strings(task_name: str) -> None:
    """All entries in failure_modes must be strings."""
    if not _has_static_workspace(task_name):
        pytest.skip(f"{task_name}: no static workspace to grade")

    score = _grade_initial_workspace(task_name)
    failure_modes = score.get("failure_modes", [])

    assert isinstance(failure_modes, list), (
        f"{task_name}: failure_modes must be a list"
    )
    for i, fm in enumerate(failure_modes):
        assert isinstance(fm, str), (
            f"{task_name}: failure_modes[{i}]={fm!r} is not a string (type={type(fm)})"
        )
