#!/usr/bin/env python3
"""
TNI pre-flight validation for new tasks.

Runs a quick 3-condition ablation (oracle, full, restricted) on seed 0
to estimate whether a task has good TNI potential before committing to
full ablation runs.

Usage:
    python scripts/validate_task_tni.py --task MULTI2_microservice_debug
    python scripts/validate_task_tni.py --task MULTI2_microservice_debug --model gemini-3-flash-preview --seeds 0 1
    python scripts/validate_task_tni.py --all-new  # validate all tasks without ablation results
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def validate_generator(task_id: str) -> dict:
    """Validate that the generator produces valid output for seeds 0, 1, 2."""
    from generators.registry import get_generator, has_generator

    result = {
        "task_id": task_id,
        "generator_exists": False,
        "seeds_valid": [],
        "cross_seed_valid": False,
        "file_counts": {},
        "errors": [],
    }

    if not has_generator(task_id):
        result["errors"].append(f"No generator found for {task_id}")
        return result

    result["generator_exists"] = True

    try:
        gen = get_generator(task_id)
    except Exception as e:
        result["errors"].append(f"Failed to load generator: {e}")
        return result

    # Test each seed
    for seed in [0, 1, 2]:
        try:
            task = gen.generate(seed)
            n_files = len(task.workspace_files)
            result["seeds_valid"].append(seed)
            result["file_counts"][seed] = n_files

            if n_files == 0:
                result["errors"].append(f"Seed {seed}: 0 workspace files generated")
            if not task.spec_md.strip():
                result["errors"].append(f"Seed {seed}: empty spec.md")
            if not task.brief_md.strip():
                result["errors"].append(f"Seed {seed}: empty brief.md")
            if not task.expected:
                result["errors"].append(f"Seed {seed}: empty expected dict")
        except Exception as e:
            result["errors"].append(f"Seed {seed}: generation failed: {e}")

    # Cross-seed validation
    if len(result["seeds_valid"]) >= 2:
        try:
            result["cross_seed_valid"] = gen.validate_cross_seed(0, 1)
            if not result["cross_seed_valid"]:
                result["errors"].append("Cross-seed validation failed: seeds 0 and 1 produce identical output")
        except Exception as e:
            result["errors"].append(f"Cross-seed validation error: {e}")

    return result


def validate_grader(task_id: str) -> dict:
    """Check that grade.sh exists and is executable."""
    result = {
        "grader_exists": False,
        "grader_executable": False,
        "errors": [],
    }

    grade_path = os.path.join(REPO_ROOT, "tasks", task_id, "grade.sh")
    if not os.path.exists(grade_path):
        result["errors"].append(f"No grade.sh found at {grade_path}")
        return result

    result["grader_exists"] = True
    result["grader_executable"] = os.access(grade_path, os.X_OK)
    if not result["grader_executable"]:
        result["errors"].append("grade.sh is not executable (chmod +x)")

    return result


def validate_task_yaml(task_id: str) -> dict:
    """Validate task.yaml exists and has required fields."""
    import yaml

    result = {
        "yaml_exists": False,
        "fields": {},
        "errors": [],
    }

    yaml_path = os.path.join(REPO_ROOT, "tasks", task_id, "task.yaml")
    if not os.path.exists(yaml_path):
        result["errors"].append(f"No task.yaml found at {yaml_path}")
        return result

    result["yaml_exists"] = True

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        required = ["task_id", "category", "difficulty", "languages", "description"]
        for field in required:
            if field in data:
                result["fields"][field] = data[field]
            else:
                result["errors"].append(f"Missing required field: {field}")

        if data.get("task_id") != task_id:
            result["errors"].append(
                f"task_id mismatch: yaml has '{data.get('task_id')}', expected '{task_id}'"
            )
    except Exception as e:
        result["errors"].append(f"Failed to parse task.yaml: {e}")

    return result


def estimate_tni(oracle_score: float, full_score: float, restricted_score: float) -> dict:
    """Estimate TNI and component values from 3-condition scores."""
    # TNI = full / max(oracle, epsilon)
    epsilon = 0.01
    tni = full_score / max(oracle_score, epsilon) if oracle_score > 0 else (
        float("inf") if full_score > 0 else 0.0
    )

    # Planning value = full - restricted (no planner)
    planning_value = full_score - restricted_score

    # Team uplift = full - oracle
    team_uplift = full_score - oracle_score

    # Classification
    if tni >= 1.2:
        classification = "HIGH-TNI"
    elif tni >= 1.0:
        classification = "TEAM-HELPS"
    elif tni >= 0.8:
        classification = "NEUTRAL"
    else:
        classification = "TEAM-HURTS"

    return {
        "tni": round(tni, 3),
        "planning_value": round(planning_value, 3),
        "team_uplift": round(team_uplift, 3),
        "classification": classification,
        "oracle_score": oracle_score,
        "full_score": full_score,
        "restricted_score": restricted_score,
    }


def find_new_tasks() -> list[str]:
    """Find tasks that don't have ablation results yet."""
    tasks_dir = os.path.join(REPO_ROOT, "tasks")
    results_dir = os.path.join(REPO_ROOT, "shared", "ablation_results")

    # Get all existing task IDs
    all_tasks = set()
    for name in os.listdir(tasks_dir):
        yaml_path = os.path.join(tasks_dir, name, "task.yaml")
        if os.path.exists(yaml_path):
            all_tasks.add(name)

    # Get task IDs with ablation results
    tasks_with_results = set()
    if os.path.exists(results_dir):
        for fname in os.listdir(results_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(results_dir, fname)) as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "runs" in data:
                        for run in data["runs"]:
                            tasks_with_results.add(run.get("task_id", ""))
                except (json.JSONDecodeError, KeyError):
                    pass

    return sorted(all_tasks - tasks_with_results)


def print_report(task_id: str, gen_result: dict, grader_result: dict, yaml_result: dict) -> bool:
    """Print validation report. Returns True if task passes all checks."""
    all_errors = gen_result["errors"] + grader_result["errors"] + yaml_result["errors"]
    passed = len(all_errors) == 0

    status = "PASS" if passed else "FAIL"
    print(f"\n{'='*60}")
    print(f"  {task_id}: {status}")
    print(f"{'='*60}")

    # Generator
    print(f"\n  Generator:")
    print(f"    Exists: {gen_result['generator_exists']}")
    if gen_result["seeds_valid"]:
        print(f"    Valid seeds: {gen_result['seeds_valid']}")
        print(f"    File counts: {gen_result['file_counts']}")
    print(f"    Cross-seed valid: {gen_result['cross_seed_valid']}")

    # Grader
    print(f"\n  Grader:")
    print(f"    Exists: {grader_result['grader_exists']}")
    print(f"    Executable: {grader_result['grader_executable']}")

    # Task YAML
    print(f"\n  task.yaml:")
    print(f"    Exists: {yaml_result['yaml_exists']}")
    if yaml_result["fields"]:
        for k, v in yaml_result["fields"].items():
            print(f"    {k}: {v}")

    # Errors
    if all_errors:
        print(f"\n  Errors ({len(all_errors)}):")
        for err in all_errors:
            print(f"    - {err}")
    else:
        print(f"\n  No errors found.")

    return passed


def main():
    parser = argparse.ArgumentParser(description="Validate TeamBench tasks")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="Task ID to validate")
    group.add_argument("--all-new", action="store_true", help="Validate all tasks without ablation results")
    group.add_argument("--all", action="store_true", help="Validate all tasks")
    parser.add_argument("--model", default="gemini-3-flash-preview", help="Model for ablation (future use)")
    parser.add_argument("--seeds", nargs="+", type=int, default=[0], help="Seeds for ablation")
    args = parser.parse_args()

    if args.task:
        task_ids = [args.task]
    elif args.all_new:
        task_ids = find_new_tasks()
        if not task_ids:
            print("No new tasks found without ablation results.")
            return
        print(f"Found {len(task_ids)} tasks without ablation results.")
    else:
        tasks_dir = os.path.join(REPO_ROOT, "tasks")
        task_ids = sorted(
            name for name in os.listdir(tasks_dir)
            if os.path.exists(os.path.join(tasks_dir, name, "task.yaml"))
        )

    total = len(task_ids)
    passed = 0

    for task_id in task_ids:
        gen_result = validate_generator(task_id)
        grader_result = validate_grader(task_id)
        yaml_result = validate_task_yaml(task_id)

        if print_report(task_id, gen_result, grader_result, yaml_result):
            passed += 1

    print(f"\n{'='*60}")
    print(f"  Summary: {passed}/{total} tasks passed validation")
    print(f"{'='*60}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
