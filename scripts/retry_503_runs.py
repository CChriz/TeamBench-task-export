#!/usr/bin/env python3
"""Merge a retry ablation JSON into an existing results JSON, replacing error'd runs."""
import json
import os
import sys
import argparse


def merge_results(base_file: str, retry_file: str, output_file: str | None = None):
    """
    Merge retry_file into base_file, replacing runs that had errors.
    Rewrites metrics based on merged run set.
    """
    with open(base_file) as f:
        base = json.load(f)
    with open(retry_file) as f:
        retry = json.load(f)

    base_runs = base.get("runs", [])
    retry_runs = retry.get("runs", [])

    # Index base runs by (condition, task_id, seed)
    index = {(r["condition"], r["task_id"], r["seed"]): i for i, r in enumerate(base_runs)}

    replaced = 0
    added = 0
    for r in retry_runs:
        key = (r["condition"], r["task_id"], r["seed"])
        if key in index:
            old = base_runs[index[key]]
            if old.get("error"):
                base_runs[index[key]] = r
                replaced += 1
                print(f"  Replaced {key}: error -> pass={r['pass']}, partial={r.get('partial_score',0):.2f}")
        else:
            base_runs.append(r)
            added += 1
            print(f"  Added {key}: pass={r['pass']}")

    print(f"\nReplaced {replaced} error runs, added {added} new runs.")

    # Recompute metrics
    base["runs"] = base_runs
    base = _recompute_metrics(base)

    out = output_file or base_file
    with open(out, "w") as f:
        json.dump(base, f, indent=2, default=str)
    print(f"Saved to {out}")


def _recompute_metrics(data: dict) -> dict:
    runs = data.get("runs", [])
    from collections import defaultdict
    by_cond = defaultdict(lambda: {"pass": 0, "total": 0, "partial": 0.0})
    for r in runs:
        if not r.get("error"):
            c = r["condition"]
            by_cond[c]["total"] += 1
            by_cond[c]["partial"] += r.get("partial_score", float(r.get("pass", False)))
            if r.get("pass"):
                by_cond[c]["pass"] += 1

    def rate(c):
        v = by_cond[c]
        return v["pass"] / v["total"] if v["total"] else 0.0

    def partial(c):
        v = by_cond[c]
        return v["partial"] / v["total"] if v["total"] else 0.0

    eps = 1e-6
    s_full = rate("expertise_full")
    s_no_anal = rate("expertise_no_analysis")
    s_oracle = rate("expertise_oracle")
    p_full = partial("expertise_full")
    p_no_anal = partial("expertise_no_analysis")
    p_oracle = partial("expertise_oracle")

    tni = (p_full - p_oracle) / max(eps, 1.0 - p_oracle)
    analysis_value = p_full - p_no_anal

    metrics = data.get("metrics", {})
    metrics.update({
        "s_expertise_full": round(s_full, 4),
        "s_expertise_no_analysis": round(s_no_anal, 4),
        "s_expertise_oracle": round(s_oracle, 4),
        "p_expertise_full": round(p_full, 4),
        "p_expertise_no_analysis": round(p_no_anal, 4),
        "p_expertise_oracle": round(p_oracle, 4),
        "expertise_tni": round(tni, 4),
        "analysis_value": round(analysis_value, 4),
    })
    data["metrics"] = metrics

    # Print summary
    print(f"\n  expertise_full:        {s_full*100:.1f}%  (partial={p_full*100:.1f}%)")
    print(f"  expertise_no_analysis: {s_no_anal*100:.1f}%  (partial={p_no_anal*100:.1f}%)")
    print(f"  expertise_oracle:      {s_oracle*100:.1f}%  (partial={p_oracle*100:.1f}%)")
    print(f"  TNI: {tni:.3f}")
    print(f"  Analysis Value: {analysis_value*100:+.1f}%")

    return data


def main():
    ap = argparse.ArgumentParser(description="Merge retry ablation results into base results")
    ap.add_argument("base", help="Base results JSON (will be updated in-place unless --output)")
    ap.add_argument("retry", help="Retry results JSON to merge in")
    ap.add_argument("--output", default=None, help="Output path (default: overwrite base)")
    args = ap.parse_args()
    merge_results(args.base, args.retry, args.output)


if __name__ == "__main__":
    main()
