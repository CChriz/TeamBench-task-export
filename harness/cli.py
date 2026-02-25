"""
TeamBench CLI — unified entry point for all benchmark operations.

Usage:
    teambench run --model gemini-2.5-flash --task S1_hidden_spec --seed 0
    teambench run --model gpt-4o --task all --seeds 0 1 2
    teambench grade --task S1_hidden_spec --run-dir shared/runs/<id>
    teambench batch --models gemini-2.5-flash gpt-4o --seeds 0 1 2
    teambench analyze --campaign shared/campaigns/campaign_XXXX/
    teambench validate --task all  # Validate graders and generators
    teambench ablation --model gemini-2.5-flash --seeds 0 1 2  # Run ablation study
"""
from __future__ import annotations

import argparse
import os
import sys


def cmd_run(args: argparse.Namespace) -> None:
    """Run agent evaluation on one or all tasks."""
    from harness.adapters import create_adapter
    from harness.run_agent import run_single_task
    from harness.run_all import discover_tasks

    tasks_dir = os.path.abspath(args.tasks_dir)
    runs_dir = os.path.abspath(args.runs_dir)

    try:
        adapter = create_adapter(model=args.model, temperature=args.temperature)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.task.lower() == "all":
        task_names = discover_tasks(tasks_dir)
    else:
        task_names = [args.task]

    seeds = args.seeds if hasattr(args, "seeds") and args.seeds else [args.seed]

    print(f"TeamBench Run")
    print(f"Model: {args.model}")
    print(f"Tasks: {task_names}")
    print(f"Seeds: {seeds}")

    all_results = []
    for task_name in task_names:
        for seed in seeds:
            try:
                result = run_single_task(
                    task_name=task_name,
                    tasks_dir=tasks_dir,
                    runs_dir=runs_dir,
                    adapter=adapter,
                    max_turns=args.max_turns,
                    max_remediation=args.max_remediation,
                )
                all_results.append(result)
            except Exception as e:
                print(f"\n  ERROR running {task_name} seed={seed}: {e}", file=sys.stderr)
                all_results.append({"task_id": task_name, "seed": seed, "error": str(e)})

    if len(all_results) > 1:
        passed = sum(1 for r in all_results if r.get("grader_verdict") == "pass")
        total = len(all_results)
        print(f"\nSummary: {passed}/{total} passed ({passed/max(1,total):.0%})")


def cmd_grade(args: argparse.Namespace) -> None:
    """Grade a completed run directory."""
    import json
    from harness.run_all import grade_run

    task_dir = os.path.abspath(os.path.join(args.tasks_dir, args.task))
    run_dir = os.path.abspath(args.run_dir)

    score = grade_run(args.task, task_dir, run_dir)
    print(json.dumps(score, indent=2))
    verdict = "PASS" if score.get("pass") else "FAIL"
    print(f"\nRESULT: {verdict}")
    if score.get("failure_modes"):
        print(f"Failure modes: {score['failure_modes']}")


def cmd_batch(args: argparse.Namespace) -> None:
    """Run multi-model batch evaluation."""
    # Delegate to batch_runner.main() via its argument parsing logic
    from harness.run_all import discover_tasks, setup_run, grade_run
    from harness.adapters import create_adapter
    from harness.orchestrator import TaskOrchestrator
    import json
    import time
    from datetime import datetime, timezone

    tasks_dir = os.path.abspath(args.tasks_dir)
    task_names = args.tasks or discover_tasks(tasks_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    campaign_dir = os.path.join(os.path.abspath(args.campaign_dir), f"campaign_{timestamp}")
    os.makedirs(campaign_dir, exist_ok=True)

    seeds = args.seeds
    all_results = []
    passed = 0
    total = len(args.models) * len(task_names) * len(seeds)
    i = 0

    print(f"TeamBench Batch")
    print(f"Models: {args.models}")
    print(f"Tasks: {len(task_names)}")
    print(f"Seeds: {seeds}")
    print(f"Total runs: {total}")
    print(f"Campaign: {campaign_dir}")
    print("=" * 60)

    for model in args.models:
        try:
            adapter = create_adapter(model=model, temperature=0.2)
        except ValueError as exc:
            print(f"ERROR creating adapter for {model}: {exc}", file=sys.stderr)
            continue

        for task in task_names:
            for seed in seeds:
                i += 1
                print(f"\n[{i}/{total}] {model} x {task} (seed={seed})")
                start_time = time.time()
                try:
                    runs_dir = os.path.join(campaign_dir, "runs")
                    run_id, run_dir, task_dir_abs = setup_run(task, tasks_dir, runs_dir, seed=seed)
                    orchestrator = TaskOrchestrator(
                        task_dir=task_dir_abs,
                        run_dir=run_dir,
                        adapter=adapter,
                        max_turns_per_phase=args.max_turns,
                        max_remediation_loops=args.max_remediation,
                    )
                    orch_result = orchestrator.run()
                    elapsed = time.time() - start_time
                    score = grade_run(task, task_dir_abs, run_dir)
                    usage = adapter.get_usage() if hasattr(adapter, "get_usage") else {}
                    result = {
                        "model": model,
                        "task_id": task,
                        "seed": seed,
                        "run_id": run_id,
                        "pass": score.get("pass", False),
                        "partial_score": score.get("secondary", {}).get("partial_score"),
                        "agent_verdict": orch_result.verdict,
                        "total_turns": orch_result.total_turns,
                        "remediation_loops": orch_result.remediation_loops,
                        "elapsed_sec": round(elapsed, 1),
                        "token_usage": usage,
                        "failure_modes": score.get("failure_modes", []),
                    }
                    if score.get("pass"):
                        passed += 1
                    status = "PASS" if score.get("pass") else "FAIL"
                    print(f"  {status} ({elapsed:.1f}s, {orch_result.total_turns} turns)")
                except Exception as e:
                    elapsed = time.time() - start_time
                    result = {
                        "model": model, "task_id": task, "seed": seed,
                        "pass": False, "error": str(e),
                        "elapsed_sec": round(elapsed, 1),
                    }
                    print(f"  ERROR: {e}", file=sys.stderr)
                all_results.append(result)

    final = {
        "campaign_dir": campaign_dir,
        "completed": datetime.now(timezone.utc).isoformat(),
        "total_runs": len(all_results),
        "passed": passed,
        "success_rate": round(passed / max(1, len(all_results)), 4),
        "results": all_results,
    }
    results_path = os.path.join(campaign_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(final, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"CAMPAIGN COMPLETE")
    print(f"Total: {len(all_results)} | Passed: {passed} | Rate: {passed/max(1,len(all_results)):.1%}")
    print(f"Results: {results_path}")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run post-hoc analysis on a campaign directory."""
    import harness.analysis as analysis_mod

    campaign = analysis_mod.load_campaign(args.campaign)
    results = campaign.get("results", [])

    if not results:
        print("No results found in campaign.")
        return

    output_path = args.output or os.path.join(args.campaign, "analysis.json")

    import json
    from collections import defaultdict

    analysis = {
        "campaign": args.campaign,
        "total_runs": len(results),
        "per_model": analysis_mod.per_model_stats(results),
        "per_task": analysis_mod.per_task_stats(results),
        "per_domain": analysis_mod.per_domain_stats(results),
        f"pass_at_{args.k}": analysis_mod.pass_at_k(results, k=args.k),
        "failure_taxonomy": analysis_mod.failure_taxonomy(results),
        "cross_model_matrix": analysis_mod.cross_model_matrix(results),
    }

    if args.tni_oracle and args.tni_restricted:
        with open(args.tni_oracle) as f:
            oracle = json.load(f)
        with open(args.tni_restricted) as f:
            restricted = json.load(f)
        s_full = oracle.get("success_rate", 0.0)
        s_restricted = restricted.get("success_rate", 0.0)
        s_team = sum(1 for r in results if r.get("pass")) / max(1, len(results))
        analysis["tni"] = analysis_mod.compute_tni(s_full, s_restricted, s_team)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nTeamBench Analysis Report")
    print(f"{'=' * 60}")
    print(f"\nPer-Model Results:")
    for model, stats in analysis["per_model"].items():
        print(f"  {model:30s}  {stats['passed']}/{stats['total_runs']} "
              f"({stats['success_rate']:.1%})  avg_partial={stats['avg_partial_score']:.2f}")

    print(f"\nPer-Task Difficulty Calibration:")
    for task, stats in analysis["per_task"].items():
        print(f"  {task:30s}  {stats['success_rate']:.1%}  [{stats['inferred_difficulty']}]")

    print(f"\nTop Failure Modes:")
    for fm, count in list(analysis["failure_taxonomy"].items())[:10]:
        print(f"  {fm:40s}  {count}")

    if "tni" in analysis:
        tni = analysis["tni"]
        print(f"\nTeamwork Necessity Index:")
        print(f"  S_full={tni['s_full']:.1%}  S_restricted={tni['s_restricted']:.1%}  "
              f"S_team={tni['s_team']:.1%}  TNI={tni['tni']:.4f}")

    print(f"\nFull analysis: {output_path}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate graders and generators for given tasks."""
    import json
    import subprocess
    import tempfile
    import shutil
    from harness.run_all import discover_tasks, setup_run, grade_run

    tasks_dir = os.path.abspath(args.tasks_dir)
    if args.task.lower() == "all":
        task_names = discover_tasks(tasks_dir)
    else:
        task_names = [args.task]

    print(f"Validating {len(task_names)} task(s)...")
    errors = []
    warnings = []

    for task_name in task_names:
        task_dir = os.path.join(tasks_dir, task_name)
        print(f"\n  {task_name}:")

        # Check required files
        required = ["task.yaml", "spec.md", "brief.md", "grade.sh", "setup.sh"]
        for fname in required:
            fpath = os.path.join(task_dir, fname)
            if not os.path.isfile(fpath):
                errors.append(f"{task_name}: missing {fname}")
                print(f"    ERROR: missing {fname}")
            else:
                print(f"    OK: {fname}")

        # Check workspace directory
        ws = os.path.join(task_dir, "workspace")
        if not os.path.isdir(ws):
            errors.append(f"{task_name}: missing workspace/")
            print(f"    ERROR: missing workspace/")
        else:
            print(f"    OK: workspace/")

        # Check grade.sh is executable
        grade_sh = os.path.join(task_dir, "grade.sh")
        if os.path.isfile(grade_sh) and not os.access(grade_sh, os.X_OK):
            warnings.append(f"{task_name}: grade.sh is not executable")
            print(f"    WARN: grade.sh not executable")

        # Run grade on initial (buggy) state — should FAIL
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                run_id, run_dir, task_dir_abs = setup_run(task_name, tasks_dir, tmpdir)
                # Create a stub attestation so grade_run proceeds past attestation check
                submission_dir = os.path.join(run_dir, "submission")
                att_path = os.path.join(submission_dir, "attestation.json")
                with open(att_path, "w") as f:
                    json.dump({"task_id": task_name, "verdict": "pass", "checklist": []}, f)

                score = grade_run(task_name, task_dir_abs, run_dir)
                if score.get("pass"):
                    warnings.append(f"{task_name}: initial buggy state PASSED grader (possible false positive)")
                    print(f"    WARN: initial state passed grader (expected FAIL)")
                else:
                    print(f"    OK: initial state correctly fails grader")

                # Validate score.json schema
                if "pass" not in score:
                    errors.append(f"{task_name}: score.json missing 'pass' field")
                ps = score.get("secondary", {}).get("partial_score")
                if ps is not None and not (0.0 <= ps <= 1.0):
                    errors.append(f"{task_name}: partial_score={ps} out of [0,1]")
                fm = score.get("failure_modes", [])
                if not isinstance(fm, list):
                    errors.append(f"{task_name}: failure_modes is not a list")
                elif any(not isinstance(m, str) for m in fm):
                    errors.append(f"{task_name}: failure_modes contains non-string entries")
                print(f"    OK: score.json schema valid")
            except Exception as e:
                warnings.append(f"{task_name}: grader validation error: {e}")
                print(f"    WARN: grader validation error: {e}")

    print(f"\n{'=' * 60}")
    print(f"Validation complete: {len(task_names)} tasks")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if not errors and not warnings:
        print("All checks passed.")
    elif errors:
        sys.exit(1)


def cmd_ablation(args: argparse.Namespace) -> None:
    """Run ablation study."""
    from harness.ablation import run_full_ablation

    tasks_dir = os.path.abspath(args.tasks_dir)
    output = args.output or "shared/ablation_results.json"

    run_full_ablation(
        model=args.model,
        tasks=args.tasks,
        seeds=args.seeds,
        tasks_dir=tasks_dir,
        output=output,
        max_turns=args.max_turns,
        max_remediation=args.max_remediation,
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="teambench",
        description="TeamBench — multi-agent LLM benchmark harness",
    )
    ap.add_argument("--tasks-dir", default="tasks", help="Tasks directory")
    sub = ap.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run agent evaluation on a task")
    p_run.add_argument("--task", required=True, help="Task name or 'all'")
    p_run.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    p_run.add_argument("--seed", type=int, default=0, help="Seed (single run)")
    p_run.add_argument("--seeds", nargs="*", type=int, help="Seeds (multiple runs)")
    p_run.add_argument("--runs-dir", default="shared/runs", help="Runs output directory")
    p_run.add_argument("--max-turns", type=int, default=20, help="Max turns per phase")
    p_run.add_argument("--max-remediation", type=int, default=2, help="Max remediation loops")
    p_run.add_argument("--temperature", type=float, default=0.2, help="Model temperature")

    # grade
    p_grade = sub.add_parser("grade", help="Grade a completed run")
    p_grade.add_argument("--task", required=True, help="Task name")
    p_grade.add_argument("--run-dir", required=True, help="Run directory path")
    p_grade.add_argument("--seed", type=int, default=0, help="Seed")

    # batch
    p_batch = sub.add_parser("batch", help="Run multi-model batch evaluation")
    p_batch.add_argument("--models", nargs="+", required=True, help="Model names")
    p_batch.add_argument("--tasks", nargs="*", default=None, help="Tasks (default: all)")
    p_batch.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2], help="Seeds")
    p_batch.add_argument("--campaign-dir", default="shared/campaigns", help="Campaign output directory")
    p_batch.add_argument("--max-turns", type=int, default=20, help="Max turns per phase")
    p_batch.add_argument("--max-remediation", type=int, default=2, help="Max remediation loops")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze campaign results")
    p_analyze.add_argument("--campaign", required=True, help="Campaign directory")
    p_analyze.add_argument("--output", default=None, help="Output JSON path")
    p_analyze.add_argument("--k", type=int, default=3, help="k for Pass@k")
    p_analyze.add_argument("--tni-oracle", default=None, help="Oracle results for TNI")
    p_analyze.add_argument("--tni-restricted", default=None, help="Restricted results for TNI")

    # validate
    p_validate = sub.add_parser("validate", help="Validate tasks (graders + generators)")
    p_validate.add_argument("--task", default="all", help="Task name or 'all'")

    # ablation
    p_ablation = sub.add_parser("ablation", help="Run ablation study")
    p_ablation.add_argument("--model", required=True, help="Model name")
    p_ablation.add_argument("--tasks", nargs="*", default=None, help="Tasks (default: all)")
    p_ablation.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2], help="Seeds")
    p_ablation.add_argument("--output", default=None, help="Output JSON path")
    p_ablation.add_argument("--max-turns", type=int, default=20, help="Max turns per phase")
    p_ablation.add_argument("--max-remediation", type=int, default=2, help="Max remediation loops")

    args = ap.parse_args()

    dispatch = {
        "run": cmd_run,
        "grade": cmd_grade,
        "batch": cmd_batch,
        "analyze": cmd_analyze,
        "validate": cmd_validate,
        "ablation": cmd_ablation,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
