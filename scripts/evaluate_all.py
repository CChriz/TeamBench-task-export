#!/usr/bin/env python3
# This script evaluates all tasks with both agent_modified and task_team workspaces
# and writes a summary JSON file with the results.
# RUN AS: python scripts/evaluate_all.py --root .
# OR SELECTED TASKS - e.g. 
# python scripts/evaluate_all.py \
#   --root . \
#   --tasks GH10_retry_backoff DIST1_queue_race

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_one import evaluate_task


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", default="eval_results.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    if args.tasks:
        task_ids = args.tasks
    else:
        modified_root = root / "agent_modified"
        task_ids = sorted(
            p.name
            for p in modified_root.iterdir()
            if (p / "workspace").exists()
        )

    records = []
    for task_id in task_ids:
        print(f"\n=== Evaluating {task_id} ===")
        try:
            record = evaluate_task(root, task_id)
            records.append(record)
            print(json.dumps(record["score"], indent=2))
        except Exception as exc:
            record = {
                "task_id": task_id,
                "score": {
                    "pass": False,
                    "primary": {"success": 0},
                    "secondary": {},
                    "failure_modes": ["evaluator_exception"],
                },
                "error": repr(exc),
            }
            records.append(record)
            print(f"ERROR: {exc}")

    summary = {
        "total": len(records),
        "passed": sum(1 for r in records if r["score"].get("pass")),
        "failed": sum(1 for r in records if not r["score"].get("pass")),
        "results": records,
    }

    out_path = root / args.out
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {out_path}")
    print(f"Passed {summary['passed']} / {summary['total']}")


if __name__ == "__main__":
    main()