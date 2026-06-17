#!/usr/bin/env python3
# This script evaluates a single task in the TeamBench framework - structurally matched
# RUN AS: python scripts/evaluate_one.py GH10_retry_backoff --root .

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def ensure_attestation(submission_dir: Path, task_id: str) -> None:
    submission_dir.mkdir(parents=True, exist_ok=True)
    attestation = submission_dir / "attestation.json"

    if attestation.exists():
        return

    attestation.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "verdict": "pass",
                "summary": "Standalone Jiuwen evaluation attestation generated after agent run.",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "checks": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def find_expected(eval_dir: Path) -> Path | None:
    candidates = [
        eval_dir / "reports" / "expected.json",
        eval_dir / "expected.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def require(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")


def evaluate_task(root: Path, task_id: str) -> dict:
    task_input = root / "task_team" / task_id
    modified_task = root / "agent_modified" / task_id
    eval_dir = root / "evals" / task_id

    workspace = modified_task / "workspace"
    reports = eval_dir / "reports"
    submission = eval_dir / "submission"
    task_dir = eval_dir / "task_dir"
    grade_sh = eval_dir / "grade.sh"

    require(task_input, "task input directory")
    require(workspace, "modified workspace")
    require(eval_dir, "eval directory")
    require(grade_sh, "grade.sh")

    # Some simple exports may not have task_dir. For general TeamBench tasks,
    # keep it. If absent, fall back to eval_dir only as a last resort.
    if not task_dir.exists():
        task_dir = eval_dir

    reports.mkdir(parents=True, exist_ok=True)
    submission.mkdir(parents=True, exist_ok=True)

    ensure_attestation(submission, task_id)

    if not os.access(grade_sh, os.X_OK):
        grade_sh.chmod(grade_sh.stat().st_mode | 0o111)

    expected = find_expected(eval_dir)

    cmd = [
        "bash",
        str(grade_sh),
        str(workspace),
        str(reports),
        str(submission),
        str(task_dir),
    ]

    if expected is not None:
        cmd.append(str(expected))

    result = subprocess.run(
        cmd,
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )

    score_path = reports / "score.json"

    if score_path.exists():
        score = json.loads(score_path.read_text(encoding="utf-8"))
    else:
        score = {
            "pass": False,
            "primary": {"success": 0},
            "secondary": {},
            "failure_modes": ["missing_score_json"],
        }

    eval_record = {
        "task_id": task_id,
        "command": cmd,
        "returncode": result.returncode,
        "score": score,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "paths": {
            "task_input": str(task_input),
            "modified_workspace": str(workspace),
            "eval_dir": str(eval_dir),
            "reports": str(reports),
            "submission": str(submission),
            "task_dir": str(task_dir),
            "grade_sh": str(grade_sh),
            "expected": str(expected) if expected else None,
        },
    }

    (reports / "standalone_eval_record.json").write_text(
        json.dumps(eval_record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return eval_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    record = evaluate_task(root, args.task_id)

    print(json.dumps(record["score"], indent=2))

    if record["score"].get("pass"):
        print(f"\nRESULT: PASS — {args.task_id}")
    else:
        print(f"\nRESULT: FAIL — {args.task_id}")
        print("Failure modes:", record["score"].get("failure_modes"))


if __name__ == "__main__":
    main()

