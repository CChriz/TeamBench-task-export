#!/usr/bin/env python3
"""
Task design pattern effectiveness analysis for TeamBench paper (Table 6).

Analyzes which TNI design patterns (A-F) produce the strongest teamwork signal,
based on ablation results across tasks grouped by their tni_pattern field.

Usage:
    python scripts/design_pattern_analysis.py --dir shared/ablation_results/
    python scripts/design_pattern_analysis.py --files shared/ablation_results/gpt4o_16task.json shared/ablation_results/crypto_dist_g3flash.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from harness.benchmark_stats import load_all_tasks, _parse_simple_yaml

# TNI pattern descriptions
PATTERN_NAMES = {
    "A": "Hidden Constraints",
    "B": "Adversarial Traps",
    "C": "Multi-Criteria Opt.",
    "D": "Cross-System Contract",
    "E": "Compliance Rules",
    "F": "Ordered Dependencies",
}


def load_task_patterns(tasks_dir: str = "tasks") -> dict[str, str]:
    """Load tni_pattern from task.yaml for each task."""
    patterns = {}
    tasks_path = Path(tasks_dir)
    if not tasks_path.is_dir():
        return patterns
    for task_dir in sorted(tasks_path.iterdir()):
        yaml_path = task_dir / "task.yaml"
        if yaml_path.is_file():
            cfg = _parse_simple_yaml(yaml_path.read_text(encoding="utf-8"))
            task_id = cfg.get("task_id", task_dir.name)
            pattern = str(cfg.get("tni_pattern", ""))
            if pattern:
                patterns[task_id] = pattern
    return patterns


def load_ablation_runs(paths: list[str]) -> list[dict]:
    """Load and merge runs from ablation JSON files."""
    seen = set()
    runs = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        for run in data.get("runs", []):
            key = (run["task_id"], run["condition"], run.get("seed", 0))
            if key not in seen:
                seen.add(key)
                runs.append(run)
    return runs


def compute_pattern_metrics(
    runs: list[dict], task_patterns: dict[str, str]
) -> dict[str, dict]:
    """Compute per-pattern aggregate metrics."""
    # Group scores by task and condition
    task_cond: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for run in runs:
        tid = run["task_id"]
        cond = run["condition"]
        score = run.get("partial_score", 1.0 if run.get("pass") else 0.0)
        task_cond[tid][cond].append(float(score))

    # Compute per-task metrics
    task_metrics = {}
    for tid, scores in task_cond.items():
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0.0

        oracle = avg(scores.get("oracle", []))
        full = avg(scores.get("full", []))
        restricted = avg(scores.get("restricted", []))
        no_verify = avg(scores.get("team_no_verify", []))
        no_plan = avg(scores.get("team_no_plan", []))

        tni = full / max(oracle, 0.01) if oracle > 0 else (
            float("inf") if full > 0 else 0.0
        )
        uplift = full - oracle
        plan_val = full - no_plan if no_plan > 0 or full > 0 else 0.0
        verify_val = full - no_verify if no_verify > 0 or full > 0 else 0.0

        task_metrics[tid] = {
            "oracle": oracle,
            "full": full,
            "restricted": restricted,
            "tni": tni,
            "uplift": uplift,
            "planning_value": plan_val,
            "verification_value": verify_val,
            "team_gt_oracle": full > oracle,
        }

    # Build case-insensitive lookup for task_metrics
    metrics_lower = {tid.lower(): tid for tid in task_metrics}

    # Aggregate by pattern
    pattern_agg: dict[str, dict] = {}
    for pattern_code in sorted(PATTERN_NAMES.keys()):
        tasks_in_pattern = []
        for tid, p in task_patterns.items():
            if p != pattern_code:
                continue
            # Try exact match first, then case-insensitive
            if tid in task_metrics:
                tasks_in_pattern.append(tid)
            elif tid.lower() in metrics_lower:
                tasks_in_pattern.append(metrics_lower[tid.lower()])

        if not tasks_in_pattern:
            continue

        metrics = [task_metrics[tid] for tid in tasks_in_pattern]
        n = len(metrics)

        avg_tni = sum(m["tni"] for m in metrics) / n
        avg_uplift = sum(m["uplift"] for m in metrics) / n
        avg_plan = sum(m["planning_value"] for m in metrics) / n
        avg_verify = sum(m["verification_value"] for m in metrics) / n
        team_gt_oracle_count = sum(1 for m in metrics if m["team_gt_oracle"])
        avg_oracle = sum(m["oracle"] for m in metrics) / n
        avg_full = sum(m["full"] for m in metrics) / n

        pattern_agg[pattern_code] = {
            "name": PATTERN_NAMES[pattern_code],
            "n_tasks": n,
            "tasks": sorted(tasks_in_pattern),
            "avg_tni": round(avg_tni, 3),
            "avg_uplift": round(avg_uplift, 3),
            "avg_planning_value": round(avg_plan, 3),
            "avg_verification_value": round(avg_verify, 3),
            "team_gt_oracle": team_gt_oracle_count,
            "team_gt_oracle_pct": round(team_gt_oracle_count / n, 2),
            "avg_oracle_score": round(avg_oracle, 3),
            "avg_full_score": round(avg_full, 3),
        }

    return pattern_agg


def generate_latex_table(pattern_agg: dict[str, dict]) -> str:
    """Generate LaTeX Table 6: Design pattern effectiveness."""
    lines = [
        "% Auto-generated by scripts/design_pattern_analysis.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Task design pattern effectiveness. Patterns are ranked by average TNI.",
        "Team $>$ Oracle shows the fraction of tasks where the full team outperforms a single oracle agent.}",
        "\\label{tab:design-patterns}",
        "\\small",
        "\\begin{tabular}{llcccccc}",
        "\\toprule",
        "Pattern & Description & $n$ & Avg TNI & Uplift & Plan Val & Verify Val & Team$>$Oracle \\\\",
        "\\midrule",
    ]

    # Sort by avg TNI descending
    sorted_patterns = sorted(
        pattern_agg.items(), key=lambda x: -x[1]["avg_tni"]
    )

    for code, m in sorted_patterns:
        uplift_sign = "+" if m["avg_uplift"] >= 0 else ""
        plan_sign = "+" if m["avg_planning_value"] >= 0 else ""
        verify_sign = "+" if m["avg_verification_value"] >= 0 else ""
        lines.append(
            f"{code} & {m['name']} & {m['n_tasks']} & "
            f"{m['avg_tni']:.2f} & "
            f"{uplift_sign}{m['avg_uplift']:.2f} & "
            f"{plan_sign}{m['avg_planning_value']:.2f} & "
            f"{verify_sign}{m['avg_verification_value']:.2f} & "
            f"{m['team_gt_oracle']}/{m['n_tasks']} ({m['team_gt_oracle_pct']:.0%}) \\\\"
        )

    # Totals
    all_tasks = sum(m["n_tasks"] for m in pattern_agg.values())
    all_tni = sum(m["avg_tni"] * m["n_tasks"] for m in pattern_agg.values()) / max(all_tasks, 1)
    all_uplift = sum(m["avg_uplift"] * m["n_tasks"] for m in pattern_agg.values()) / max(all_tasks, 1)
    all_tgo = sum(m["team_gt_oracle"] for m in pattern_agg.values())

    lines.extend([
        "\\midrule",
        f"\\textbf{{All}} & & {all_tasks} & "
        f"{all_tni:.2f} & "
        f"{'+'if all_uplift>=0 else ''}{all_uplift:.2f} & "
        f"& & {all_tgo}/{all_tasks} ({all_tgo/max(all_tasks,1):.0%}) \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze TNI design pattern effectiveness"
    )
    parser.add_argument("--files", nargs="+", help="Ablation JSON files")
    parser.add_argument("--dir", help="Directory of ablation JSON files")
    parser.add_argument("--tasks-dir", default="tasks", help="Tasks directory")
    parser.add_argument("--output-dir", default="shared/paper", help="Output directory")
    args = parser.parse_args()

    # Collect ablation files
    paths = []
    if args.files:
        paths = args.files
    elif args.dir:
        d = Path(args.dir)
        paths = sorted(str(f) for f in d.glob("*.json"))
    else:
        # Default: shared/ablation_results/
        d = Path("shared/ablation_results")
        if d.is_dir():
            paths = sorted(str(f) for f in d.glob("*.json"))

    if not paths:
        print("No ablation files found.")
        return

    # Load data
    task_patterns = load_task_patterns(args.tasks_dir)
    print(f"Loaded TNI patterns for {len(task_patterns)} tasks")

    runs = load_ablation_runs(paths)
    print(f"Loaded {len(runs)} ablation runs from {len(paths)} files")

    # Compute metrics
    pattern_agg = compute_pattern_metrics(runs, task_patterns)

    if not pattern_agg:
        print("No matching tasks with both patterns and ablation data.")
        return

    # Print summary
    print(f"\n{'='*70}")
    print("Design Pattern Effectiveness Analysis")
    print(f"{'='*70}")
    for code, m in sorted(pattern_agg.items(), key=lambda x: -x[1]["avg_tni"]):
        print(
            f"  {code} ({m['name']:<24}): "
            f"n={m['n_tasks']:>2}, "
            f"TNI={m['avg_tni']:.3f}, "
            f"uplift={m['avg_uplift']:+.3f}, "
            f"team>oracle={m['team_gt_oracle']}/{m['n_tasks']}"
        )

    # Generate outputs
    os.makedirs(args.output_dir, exist_ok=True)

    # LaTeX table
    latex = generate_latex_table(pattern_agg)
    tex_path = os.path.join(args.output_dir, "table_design_patterns.tex")
    with open(tex_path, "w") as f:
        f.write(latex)
    print(f"\nLaTeX table: {tex_path}")

    # JSON stats
    json_path = os.path.join(args.output_dir, "design_pattern_stats.json")
    with open(json_path, "w") as f:
        json.dump(pattern_agg, f, indent=2)
    print(f"JSON stats: {json_path}")


if __name__ == "__main__":
    main()
