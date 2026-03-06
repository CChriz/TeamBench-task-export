#!/usr/bin/env python3
"""Check progress of cross-model ablation runs.

Usage: python scripts/check_crossmodel.py
"""
import json, os, glob, sys
from datetime import datetime

RESULTS_DIR = "shared/ablation_results"
RUNS_DIR = os.path.join(RESULTS_DIR, "ablation_runs")
MODELS = {
    "gpt-5-nano": "crossmodel_gpt5nano_seed0.json",
    "gpt-5-mini": "crossmodel_gpt5mini_seed0.json",
    "g3.1-flash-lite": "crossmodel_g31lite_seed0.json",
    "g3-flash": "crossmodel_g3flash_seed0.json",
}
TOTAL_RUNS = 140  # 28 tasks × 5 conditions


def check_from_json():
    """Check completed results from JSON files."""
    print(f"\n{'='*60}")
    print(f"Cross-Model Ablation Progress  [{datetime.now().strftime('%H:%M:%S')}]")
    print(f"{'='*60}")

    for label, fname in MODELS.items():
        path = os.path.join(RESULTS_DIR, fname)
        if not os.path.exists(path):
            print(f"  {label:25s}: not started / no results yet")
            continue
        try:
            d = json.load(open(path))
            runs = d.get("runs", [])
            scored = sum(1 for r in runs if r.get("score") is not None)
            passed = sum(1 for r in runs if r.get("score") == 1.0)
            errs = sum(1 for r in runs if r.get("error"))
            total = d.get("total_runs", len(runs))
            pct = scored / total * 100 if total else 0
            print(f"  {label:25s}: {scored:3d}/{total} scored ({pct:.0f}%), "
                  f"{passed:2d} passed, {errs:3d} errors")
        except Exception as e:
            print(f"  {label:25s}: error reading: {e}")


def check_from_runs():
    """Check in-progress runs from the runs directory."""
    if not os.path.exists(RUNS_DIR):
        return

    print(f"\n{'='*60}")
    print(f"Active Run Directories (last 10 minutes)")
    print(f"{'='*60}")

    import time
    cutoff = time.time() - 600

    tasks = {}
    for task_dir in glob.glob(os.path.join(RUNS_DIR, "*")):
        task_name = os.path.basename(task_dir)
        run_dirs = glob.glob(os.path.join(task_dir, "2026*"))
        recent = [d for d in run_dirs if os.path.getmtime(d) > cutoff]
        if recent:
            tasks[task_name] = len(recent)

    if tasks:
        print(f"  Active tasks ({len(tasks)}): ", end="")
        print(", ".join(f"{t}({n})" for t, n in sorted(tasks.items())[:10]))
    else:
        print("  No active runs in the last 10 minutes")


def main():
    check_from_json()
    check_from_runs()

    # Summary
    print(f"\n{'='*60}")
    print(f"Estimated time: ~{TOTAL_RUNS * 4 / 60:.0f} min per model, "
          f"4 models running in parallel")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
