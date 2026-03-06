#!/usr/bin/env python3
"""
TeamBench leaderboard runner.

Runs all 5 ablation conditions for a given model across all tasks (or a
subset), then writes a standardized leaderboard JSON file that aggregates:
  - Per-task scores for each condition
  - Aggregate TNI, team uplift, planning/verification value
  - Per-category breakdown
  - Model metadata

The leaderboard JSON is designed to be consumed by a leaderboard display
or merged with results from other models via cross_model_analysis.py.

Usage:
    # Run all tasks, seeds [0,1,2], write to shared/leaderboard/
    python scripts/run_leaderboard.py --model gemini-3-flash-preview

    # Quick run: 3 tasks, seed 0 only
    python scripts/run_leaderboard.py --model gpt-4o \\
        --tasks S1_hidden_spec D1_data_drift O2_on_call \\
        --seeds 0

    # Run only specific conditions (skip expertise variants)
    python scripts/run_leaderboard.py --model gpt-4o \\
        --conditions oracle restricted full team_no_plan team_no_verify

    # Dry-run: grade workspace as-is (no agent execution)
    python scripts/run_leaderboard.py --model baseline --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

# Allow running as a script from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.run_all import discover_tasks, setup_run, grade_run
from harness.ablation import AblationCondition, run_ablation_condition
from harness.compute_tni import TaskMetrics
from harness.paper_tables import CATEGORY_MAP, runs_to_task_metrics


# -----------------------------------------------------------------------
# Category helper (mirrors paper_tables._task_category)
# -----------------------------------------------------------------------

def _task_category(task_id: str) -> str:
    prefix = ""
    first_part = task_id.split("_")[0] if "_" in task_id else task_id
    for ch in first_part:
        if ch.isalpha():
            prefix += ch
        else:
            break
    return CATEGORY_MAP.get(prefix.upper(), prefix.upper())


# -----------------------------------------------------------------------
# .env loader
# -----------------------------------------------------------------------

def _load_dotenv(repo_root: str) -> None:
    env_path = os.path.join(repo_root, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


# -----------------------------------------------------------------------
# TNI helpers (reuse TaskMetrics properties)
# -----------------------------------------------------------------------

def _tni_val(m: TaskMetrics) -> float | None:
    if math.isnan(m.tni) or abs(m.necessity_gap) <= 0.05:
        return None
    return m.tni


# -----------------------------------------------------------------------
# Leaderboard JSON builders
# -----------------------------------------------------------------------

def build_per_task_entry(task_id: str, runs: list[dict]) -> dict:
    """Build per-task leaderboard entry from raw run records."""
    cond_scores: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        if r["task_id"] != task_id:
            continue
        partial = float(r.get("partial_score", 1.0 if r.get("pass") else 0.0))
        cond_scores[r["condition"]].append(partial)

    def avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    # Build TaskMetrics to reuse TNI logic
    m = TaskMetrics(
        task_id=task_id,
        oracle_partial=avg(cond_scores.get("oracle", [])),
        restricted_partial=avg(cond_scores.get("restricted", [])),
        team_partial=avg(cond_scores.get("full", [])),
        no_plan_partial=avg(cond_scores.get("team_no_plan", [])),
        no_verify_partial=avg(cond_scores.get("team_no_verify", [])),
        expertise_partial=avg(cond_scores.get("expertise_full", [])),
        expertise_no_analysis_partial=avg(cond_scores.get("expertise_no_analysis", [])),
        expertise_no_test_partial=avg(cond_scores.get("expertise_no_test", [])),
        expertise_oracle_partial=avg(cond_scores.get("expertise_oracle", [])),
    )

    tni_v = _tni_val(m)
    pv = m.planning_value if not math.isnan(m.planning_value) else None
    vv = m.verification_value if not math.isnan(m.verification_value) else None

    return {
        "task_id": task_id,
        "category": _task_category(task_id),
        "n_seeds": max(len(v) for v in cond_scores.values()) if cond_scores else 0,
        "conditions": {
            cond: round(avg(vals), 4)
            for cond, vals in sorted(cond_scores.items())
        },
        "oracle": round(m.oracle_partial, 4),
        "restricted": round(m.restricted_partial, 4),
        "team": round(m.team_partial, 4),
        "no_plan": round(m.no_plan_partial, 4),
        "no_verify": round(m.no_verify_partial, 4),
        "necessity_gap": round(m.necessity_gap, 4),
        "tni": round(tni_v, 4) if tni_v is not None else None,
        "team_uplift": round(m.team_uplift, 4),
        "collab_efficiency": round(m.collab_efficiency, 4),
        "planning_value": round(pv, 4) if pv is not None else None,
        "verification_value": round(vv, 4) if vv is not None else None,
        "classification": m.classification,
    }


def build_leaderboard_json(
    model: str,
    all_runs: list[dict],
    task_names: list[str],
    conditions: list[AblationCondition],
    seeds: list[int],
    elapsed_sec: float,
) -> dict:
    """Build the full standardized leaderboard JSON."""
    # Per-task entries
    per_task = [build_per_task_entry(t, all_runs) for t in task_names]

    # Aggregate TNI
    metrics_list = runs_to_task_metrics(all_runs)
    valid_tni = [_tni_val(m) for m in metrics_list if _tni_val(m) is not None]
    all_uplifts = [m.team_uplift for m in metrics_list]
    valid_pv = [m.planning_value for m in metrics_list if not math.isnan(m.planning_value)]
    valid_vv = [m.verification_value for m in metrics_list if not math.isnan(m.verification_value)]

    avg_tni = sum(valid_tni) / len(valid_tni) if valid_tni else None
    avg_uplift = sum(all_uplifts) / len(all_uplifts) if all_uplifts else 0.0
    avg_pv = sum(valid_pv) / len(valid_pv) if valid_pv else None
    avg_vv = sum(valid_vv) / len(valid_vv) if valid_vv else None
    team_wins = sum(1 for m in metrics_list if m.team_uplift > 0.01)

    aggregate = {
        "task_count": len(task_names),
        "run_count": len(all_runs),
        "seeds": seeds,
        "conditions": [c.value for c in conditions],
        "avg_oracle": round(
            sum(m.oracle_partial for m in metrics_list) / max(1, len(metrics_list)), 4
        ),
        "avg_restricted": round(
            sum(m.restricted_partial for m in metrics_list) / max(1, len(metrics_list)), 4
        ),
        "avg_team": round(
            sum(m.team_partial for m in metrics_list) / max(1, len(metrics_list)), 4
        ),
        "avg_tni": round(avg_tni, 4) if avg_tni is not None else None,
        "valid_tni_count": len(valid_tni),
        "avg_team_uplift": round(avg_uplift, 4),
        "avg_planning_value": round(avg_pv, 4) if avg_pv is not None else None,
        "avg_verification_value": round(avg_vv, 4) if avg_vv is not None else None,
        "team_helps_count": team_wins,
        "team_helps_pct": round(team_wins / max(1, len(metrics_list)), 4),
        "team_outperforms_oracle": [
            m.task_id for m in metrics_list if m.team_uplift > 0.01
        ],
    }

    # Per-category breakdown
    cat_tasks: dict[str, list[TaskMetrics]] = defaultdict(list)
    for m in metrics_list:
        cat_tasks[_task_category(m.task_id)].append(m)

    per_category = {}
    for cat in sorted(cat_tasks):
        ms = cat_tasks[cat]
        n = len(ms)
        cat_valid_tni = [_tni_val(m) for m in ms if _tni_val(m) is not None]
        per_category[cat] = {
            "task_count": n,
            "avg_oracle": round(sum(m.oracle_partial for m in ms) / n, 4),
            "avg_restricted": round(sum(m.restricted_partial for m in ms) / n, 4),
            "avg_team": round(sum(m.team_partial for m in ms) / n, 4),
            "avg_uplift": round(sum(m.team_uplift for m in ms) / n, 4),
            "avg_tni": round(
                sum(cat_valid_tni) / len(cat_valid_tni), 4
            ) if cat_valid_tni else None,
            "team_wins": sum(1 for m in ms if m.team_uplift > 0.01),
        }

    # Classification histogram
    class_counts: dict[str, int] = defaultdict(int)
    for entry in per_task:
        class_counts[entry["classification"]] += 1

    return {
        "schema_version": "1.0",
        "model": model,
        "completed": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(elapsed_sec, 1),
        "aggregate": aggregate,
        "per_category": per_category,
        "classification_histogram": dict(class_counts),
        "per_task": per_task,
        "raw_runs": all_runs,
    }


# -----------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------

def run_leaderboard(
    model: str,
    task_names: list[str],
    seeds: list[int],
    tasks_dir: str,
    output_dir: str,
    conditions: list[AblationCondition],
    max_turns: int,
    max_remediation: int,
    dry_run: bool,
) -> dict:
    from harness.adapters import create_adapter

    runs_base = os.path.join(output_dir, "leaderboard_runs")
    os.makedirs(output_dir, exist_ok=True)

    if not dry_run:
        adapter = create_adapter(model=model, temperature=0.2)
    else:
        from harness.adapters.mock_adapter import MockAdapter
        adapter = MockAdapter()  # type: ignore[assignment]

    total = len(conditions) * len(task_names) * len(seeds)
    print(f"TeamBench Leaderboard Runner")
    print(f"  Model:      {model}")
    print(f"  Tasks:      {len(task_names)}")
    print(f"  Seeds:      {seeds}")
    print(f"  Conditions: {[c.value for c in conditions]}")
    print(f"  Total runs: {total}")
    print(f"  Dry-run:    {dry_run}")
    print("=" * 60)

    all_runs: list[dict] = []
    global_start = time.time()
    i = 0

    for condition in conditions:
        for task_name in task_names:
            for seed in seeds:
                i += 1
                print(f"\n[{i}/{total}] {condition.value} x {task_name} (seed={seed})")
                t0 = time.time()
                error_msg = None
                score: dict = {}

                try:
                    run_id, run_dir, task_dir = setup_run(
                        task_name, tasks_dir, runs_base, seed=seed
                    )

                    # Tag the run with condition for post-hoc analysis
                    meta_path = os.path.join(run_dir, "run_meta.json")
                    if os.path.isfile(meta_path):
                        with open(meta_path) as mf:
                            meta = json.load(mf)
                        meta["condition"] = condition.value
                        with open(meta_path, "w") as mf:
                            json.dump(meta, mf, indent=2)

                    if not dry_run:
                        run_ablation_condition(
                            condition=condition,
                            task_dir=task_dir,
                            run_dir=run_dir,
                            adapter=adapter,
                            max_turns=max_turns,
                            max_remediation=max_remediation,
                        )

                    score = grade_run(task_name, task_dir, run_dir)

                except Exception as e:
                    error_msg = str(e)
                    score = {
                        "pass": False,
                        "secondary": {"partial_score": 0.0},
                        "failure_modes": ["runner_error"],
                    }
                    print(f"  ERROR: {e}")

                elapsed = round(time.time() - t0, 1)
                partial = float(
                    score.get("secondary", {}).get(
                        "partial_score", 1.0 if score.get("pass") else 0.0
                    )
                )
                status = "PASS" if score.get("pass") else "FAIL"
                print(f"  {status} partial={partial:.2f} ({elapsed}s)")

                all_runs.append({
                    "condition": condition.value,
                    "task_id": task_name,
                    "seed": seed,
                    "pass": bool(score.get("pass", False)),
                    "partial_score": partial,
                    "elapsed_sec": elapsed,
                    "failure_modes": score.get("failure_modes", []),
                    "error": error_msg,
                })

    elapsed_total = time.time() - global_start
    leaderboard = build_leaderboard_json(
        model=model,
        all_runs=all_runs,
        task_names=task_names,
        conditions=conditions,
        seeds=seeds,
        elapsed_sec=elapsed_total,
    )

    # Write output
    safe_model = model.replace("/", "_").replace(":", "_")
    out_path = os.path.join(output_dir, f"leaderboard_{safe_model}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2, ensure_ascii=False)

    # Print summary
    agg = leaderboard["aggregate"]
    print(f"\n{'=' * 60}")
    print(f"LEADERBOARD COMPLETE — {model}")
    print(f"{'=' * 60}")
    print(f"  Tasks:            {agg['task_count']}")
    print(f"  Total runs:       {agg['run_count']}")
    print(f"  Avg Oracle:       {agg['avg_oracle']:.3f}")
    print(f"  Avg Team (Full):  {agg['avg_team']:.3f}")
    print(f"  Avg Uplift:       {agg['avg_team_uplift']:+.3f}")
    tni_s = f"{agg['avg_tni']:.3f}" if agg.get("avg_tni") is not None else "N/A"
    print(f"  Avg TNI:          {tni_s} (valid on {agg['valid_tni_count']} tasks)")
    pv_s = f"{agg['avg_planning_value']:+.3f}" if agg.get("avg_planning_value") is not None else "N/A"
    vv_s = f"{agg['avg_verification_value']:+.3f}" if agg.get("avg_verification_value") is not None else "N/A"
    print(f"  Avg Plan. Value:  {pv_s}")
    print(f"  Avg Verif. Value: {vv_s}")
    print(f"  Team > Oracle:    {agg['team_helps_count']}/{agg['task_count']}")
    print(f"  Elapsed:          {elapsed_total:.0f}s")
    print(f"\n  Output: {out_path}")

    if leaderboard["per_category"]:
        print(f"\n  Per-category:")
        for cat, cs in sorted(leaderboard["per_category"].items()):
            tni_c = f"{cs['avg_tni']:.3f}" if cs.get("avg_tni") is not None else " N/A"
            print(
                f"    {cat:<22} n={cs['task_count']}  "
                f"oracle={cs['avg_oracle']:.2f}  team={cs['avg_team']:.2f}  "
                f"uplift={cs['avg_uplift']:+.2f}  TNI={tni_c}"
            )

    return leaderboard


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="TeamBench leaderboard runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--model", required=True, help="Model name (e.g. gpt-4o, gemini-3-flash-preview)")
    ap.add_argument("--tasks", nargs="*", default=None, help="Tasks to run (default: all)")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2], help="Seeds (default: 0 1 2)")
    ap.add_argument("--tasks-dir", default="tasks", help="Tasks directory (default: tasks)")
    ap.add_argument(
        "--output-dir", default="shared/leaderboard",
        help="Output directory for leaderboard JSON (default: shared/leaderboard)",
    )
    ap.add_argument("--max-turns", type=int, default=20, help="Max turns per agent phase")
    ap.add_argument("--max-remediation", type=int, default=2, help="Max remediation loops")
    ap.add_argument(
        "--conditions", nargs="+",
        default=["oracle", "restricted", "full", "team_no_plan", "team_no_verify"],
        choices=[c.value for c in AblationCondition],
        help="Ablation conditions to run (default: 5 standard conditions)",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Skip agent execution; grade initial workspace state only (for testing)",
    )
    args = ap.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Load .env
    env_path = os.path.join(repo_root, ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    tasks_dir = os.path.abspath(args.tasks_dir)
    task_names = args.tasks or discover_tasks(tasks_dir)
    if not task_names:
        print(f"No tasks found in {tasks_dir}", file=sys.stderr)
        sys.exit(1)

    conditions = [AblationCondition(c) for c in args.conditions]
    output_dir = os.path.abspath(args.output_dir)

    run_leaderboard(
        model=args.model,
        task_names=task_names,
        seeds=args.seeds,
        tasks_dir=tasks_dir,
        output_dir=output_dir,
        conditions=conditions,
        max_turns=args.max_turns,
        max_remediation=args.max_remediation,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
