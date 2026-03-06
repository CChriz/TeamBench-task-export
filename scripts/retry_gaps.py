#!/usr/bin/env python3
"""Retry only missing (task, condition, seed) tuples from Phase 3 ablation."""

import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.ablation import (
    AblationCondition,
    setup_run,
    run_ablation_condition,
    grade_run,
)
from harness.adapters import create_adapter


def load_existing_scored(consolidated_path: str) -> set[tuple[str, str, int]]:
    """Load already-scored (task_id, condition, seed) tuples."""
    with open(consolidated_path) as f:
        data = json.load(f)
    scored = set()
    for r in data["runs"]:
        has_score = r.get("pass") is not None
        if has_score:
            scored.add((r["task_id"], r["condition"], r["seed"]))
    return scored


def run_gaps(
    model: str,
    gaps: list[tuple[str, str, int]],
    output_path: str,
    tasks_dir: str = "tasks",
    max_turns: int = 20,
    max_remediation: int = 2,
):
    """Run only the specified (task, condition, seed) gaps."""
    tasks_dir = os.path.abspath(tasks_dir)
    adapter = create_adapter(model=model, temperature=0.2)
    runs_base = os.path.join(os.path.dirname(os.path.abspath(output_path)), "ablation_runs")

    print(f"Retry Gaps: {len(gaps)} runs with model={model}")
    print("=" * 60)

    all_runs = []
    for i, (task_name, cond_str, seed) in enumerate(gaps, 1):
        condition = AblationCondition(cond_str)
        print(f"\n[{i}/{len(gaps)}] {cond_str} x {task_name} (seed={seed})")
        start_time = time.time()

        try:
            run_id, run_dir, task_dir = setup_run(task_name, tasks_dir, runs_base, seed=seed)

            # Store condition in run_meta.json
            meta_path = os.path.join(run_dir, "run_meta.json")
            if os.path.isfile(meta_path):
                with open(meta_path, "r") as mf:
                    meta = json.load(mf)
                meta["condition"] = cond_str
                with open(meta_path, "w") as mf:
                    json.dump(meta, mf, indent=2)

            orch_result = run_ablation_condition(
                condition=condition,
                task_dir=task_dir,
                run_dir=run_dir,
                adapter=adapter,
                max_turns=max_turns,
                max_remediation=max_remediation,
            )

            elapsed = time.time() - start_time
            score = grade_run(task_name, task_dir, run_dir)
            partial = score.get("secondary", {}).get(
                "partial_score", 1.0 if score.get("pass") else 0.0
            )
            status = "PASS" if score.get("pass") else "FAIL"
            print(f"  {status} (partial={partial:.2f}, {elapsed:.1f}s)")

            all_runs.append({
                "condition": cond_str,
                "task_id": task_name,
                "seed": seed,
                "run_id": run_id,
                "pass": score.get("pass", False),
                "secondary": {"partial_score": partial},
                "elapsed_sec": round(elapsed, 1),
            })

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ERROR: {e}")
            all_runs.append({
                "condition": cond_str,
                "task_id": task_name,
                "seed": seed,
                "pass": None,
                "error": str(e),
                "elapsed_sec": round(elapsed, 1),
            })

        # Save incrementally
        result = {"model": model, "runs": all_runs, "total": len(gaps), "scored": sum(1 for r in all_runs if r.get("pass") is not None)}
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    scored = sum(1 for r in all_runs if r.get("pass") is not None)
    passed = sum(1 for r in all_runs if r.get("pass") is True)
    print(f"\n{'='*60}")
    print(f"Done: {scored}/{len(gaps)} scored, {passed} passed")
    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Retry missing ablation gaps")
    ap.add_argument("--batch", choices=["ab", "c", "all"], default="all")
    ap.add_argument("--consolidated", default="shared/ablation_results/phase3_all_consolidated.json")
    ap.add_argument("--output-dir", default="shared/ablation_results")
    ap.add_argument("--max-turns", type=int, default=20)
    args = ap.parse_args()

    scored = load_existing_scored(args.consolidated)
    conditions = ["oracle", "restricted", "team_no_verify", "team_no_plan", "full"]
    seeds = [1, 2]

    batch_a = {"CR6_review_checklist", "DIST6_distributed_lock", "IR5_search_ranking",
               "MULTI1_fullstack_fix", "NEG2_cost_perf", "O3_log_analysis", "O4_monitoring",
               "SPEC3_data_model", "TEST1_spec_to_tests", "TEST2_regression", "TEST3_integration",
               "TEST4_property", "TEST6_property_based", "TEST9_mock_service"}
    batch_b = {"CR5_test_coverage", "CRYPTO5_tls_config", "D8_csv_cleanup", "LH2_budgeted_workflow",
               "O1_service_health", "P6_license_check", "P7_data_retention", "PIPE1_etl_fix",
               "S5_error_handling", "SEC1_vuln_patch", "SEC3_crypto_upgrade", "SEC5_secrets_rotation",
               "SPEC5_config_system", "SYNTH1_distributed_debug"}

    all_tasks = set(r[0] for r in scored)
    batch_c = all_tasks - batch_a - batch_b

    def find_gaps(tasks):
        gaps = []
        for t in sorted(tasks):
            for c in conditions:
                for s in seeds:
                    if (t, c, s) not in scored:
                        gaps.append((t, c, s))
        return gaps

    if args.batch in ("ab", "all"):
        ab_gaps = find_gaps(batch_a | batch_b)
        if ab_gaps:
            print(f"\n=== BATCH A+B: {len(ab_gaps)} gaps (gemini-3-flash-preview) ===")
            run_gaps(
                model="gemini-3-flash-preview",
                gaps=ab_gaps,
                output_path=os.path.join(args.output_dir, "phase3_batchAB_retry.json"),
                max_turns=args.max_turns,
            )

    if args.batch in ("c", "all"):
        c_gaps = find_gaps(batch_c)
        if c_gaps:
            print(f"\n=== BATCH C: {len(c_gaps)} gaps (gemini-3.1-flash-lite-preview) ===")
            run_gaps(
                model="gemini-3.1-flash-lite-preview",
                gaps=c_gaps,
                output_path=os.path.join(args.output_dir, "phase3_batchC_retry.json"),
                max_turns=args.max_turns,
            )
