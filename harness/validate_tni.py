"""
TeamBench — TNI Statistical Validation.

Validates the key claims from the EA (Expertise-Asymmetry) experiments:
  1. expertise_full significantly > expertise_oracle (team beats oracle)
  2. expertise_full significantly > expertise_no_analysis (analysis adds value)

Methods:
  - Bootstrap 95% CIs on pass rates and differences
  - Permutation test (randomisation test) for each pairwise comparison
  - Power analysis: minimum N to detect observed effect at 80% power
  - Cross-model pooled analysis

Usage:
    python -m harness.validate_tni
    python -m harness.validate_tni --results-dir shared/ea_results --latex
    python -m harness.validate_tni --model gemini-2.5-flash gemini-3-flash-preview
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RunRecord:
    model: str
    task_id: str
    seed: int
    condition: str
    passed: bool
    partial_score: float


@dataclass
class ConditionStats:
    condition: str
    n: int
    passes: int
    rate: float
    ci_lo: float
    ci_hi: float


@dataclass
class ComparisonResult:
    label: str
    condition_a: str
    condition_b: str
    n_a: int
    n_b: int
    rate_a: float
    rate_b: float
    diff: float          # rate_a - rate_b
    diff_ci_lo: float
    diff_ci_hi: float
    p_value: float       # permutation test
    significant: bool    # p < 0.05
    min_n_for_power: int # runs needed per condition for 80% power


# ---------------------------------------------------------------------------
# Bootstrap utilities
# ---------------------------------------------------------------------------

def _bootstrap_rate(
    scores: list[bool],
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Returns (mean, ci_lo, ci_hi)."""
    if not scores:
        return 0.0, 0.0, 0.0
    n = len(scores)
    mean = sum(scores) / n
    rng = random.Random(seed)
    boot = sorted(
        sum(rng.choice(scores) for _ in range(n)) / n
        for _ in range(n_boot)
    )
    lo = boot[max(0, int(math.floor(alpha / 2 * n_boot)))]
    hi = boot[min(n_boot - 1, int(math.ceil((1 - alpha / 2) * n_boot)) - 1)]
    return mean, lo, hi


def _bootstrap_diff(
    a: list[bool],
    b: list[bool],
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap CI on difference (mean_a - mean_b). Returns (diff, ci_lo, ci_hi)."""
    if not a or not b:
        return 0.0, 0.0, 0.0
    na, nb = len(a), len(b)
    diff = sum(a) / na - sum(b) / nb
    rng = random.Random(seed)
    boot = sorted(
        sum(rng.choice(a) for _ in range(na)) / na
        - sum(rng.choice(b) for _ in range(nb)) / nb
        for _ in range(n_boot)
    )
    lo = boot[max(0, int(math.floor(alpha / 2 * n_boot)))]
    hi = boot[min(n_boot - 1, int(math.ceil((1 - alpha / 2) * n_boot)) - 1)]
    return diff, lo, hi


def _permutation_test(
    a: list[bool],
    b: list[bool],
    n_perm: int = 10_000,
    seed: int = 42,
) -> float:
    """
    One-sided permutation test: P(observed diff >= diff under H0: a and b same dist).
    H0: labels (a/b) are exchangeable.
    """
    if not a or not b:
        return 1.0
    na, nb = len(a), len(b)
    observed = sum(a) / na - sum(b) / nb
    combined = [float(x) for x in a + b]
    rng = random.Random(seed)
    count_ge = 0
    for _ in range(n_perm):
        rng.shuffle(combined)
        perm_diff = sum(combined[:na]) / na - sum(combined[na:]) / nb
        if perm_diff >= observed:
            count_ge += 1
    return (count_ge + 1) / (n_perm + 1)  # +1 for continuity correction


def _min_n_for_power(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """
    Minimum N per group to detect difference |p1-p2| with given alpha and power.
    Uses normal approximation for two-proportion z-test.
    """
    if abs(p1 - p2) < 1e-9:
        return 9999
    # z critical values
    def z_from_p(p: float) -> float:
        if p <= 0 or p >= 1:
            return 3.0
        t = math.sqrt(-2 * math.log(min(p, 1 - p)))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        z = t - (c0 + c1 * t + c2 * t**2) / (1 + d1 * t + d2 * t**2 + d3 * t**3)
        return z if p <= 0.5 else -z

    z_a = abs(z_from_p(alpha))       # one-tailed (directional hypothesis)
    z_b = abs(z_from_p(1 - power))
    p_bar = (p1 + p2) / 2
    n = ((z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(
        p1 * (1 - p1) + p2 * (1 - p2)
    )) / (p1 - p2)) ** 2
    return max(1, math.ceil(abs(n)))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_results(results_dir: str, models: Optional[list[str]] = None) -> list[RunRecord]:
    """Load all EA result JSON files from results_dir."""
    records: list[RunRecord] = []
    results_path = Path(results_dir)

    ea_conditions = {
        "expertise_full", "expertise_no_analysis",
        "expertise_no_test", "expertise_oracle",
    }

    for fpath in sorted(results_path.glob("*.json")):
        # Skip "missing" fill-in files and non-EA files
        name = fpath.stem
        if "missing" in name or "ablation" in name:
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        model = data.get("model", name)
        if models and model not in models:
            continue

        runs = data.get("runs", [])
        if not any(r.get("condition", "") in ea_conditions for r in runs):
            continue

        for r in runs:
            cond = r.get("condition", "")
            if cond not in ea_conditions:
                continue
            records.append(RunRecord(
                model=model,
                task_id=r["task_id"],
                seed=r.get("seed", 0),
                condition=cond,
                passed=bool(r.get("pass", False)),
                partial_score=float(r.get("partial_score", 0.0)),
            ))

    return records


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def condition_stats(records: list[RunRecord], condition: str) -> ConditionStats:
    subset = [r.passed for r in records if r.condition == condition]
    n = len(subset)
    passes = sum(subset)
    rate, lo, hi = _bootstrap_rate(subset)
    return ConditionStats(condition, n, passes, rate, lo, hi)


def compare_conditions(
    records: list[RunRecord],
    cond_a: str,
    cond_b: str,
    label: str,
) -> ComparisonResult:
    a = [r.passed for r in records if r.condition == cond_a]
    b = [r.passed for r in records if r.condition == cond_b]
    diff, lo, hi = _bootstrap_diff(a, b)
    p = _permutation_test(a, b)
    ra = sum(a) / max(1, len(a))
    rb = sum(b) / max(1, len(b))
    min_n = _min_n_for_power(ra, rb)
    return ComparisonResult(
        label=label,
        condition_a=cond_a, condition_b=cond_b,
        n_a=len(a), n_b=len(b),
        rate_a=ra, rate_b=rb,
        diff=diff, diff_ci_lo=lo, diff_ci_hi=hi,
        p_value=p, significant=p < 0.05,
        min_n_for_power=min_n,
    )


def expertise_tni_with_ci(
    records: list[RunRecord],
    n_boot: int = 10_000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap CI on expertise_tni = (full - oracle) / max(eps, max_possible - oracle).

    Since oracle is the single-agent baseline and full is the team,
    we use: tni = full_rate / max(eps, oracle_rate) - but our actual formula is:
        expertise_tni = (p_full - p_oracle) / max(eps, 1.0 - p_oracle)
    which measures how much of the remaining gap the team closes.
    """
    full_scores = [r.passed for r in records if r.condition == "expertise_full"]
    oracle_scores = [r.passed for r in records if r.condition == "expertise_oracle"]
    if not full_scores or not oracle_scores:
        return float("nan"), float("nan"), float("nan")

    def _tni(f: list, o: list) -> float:
        pf = sum(f) / len(f)
        po = sum(o) / len(o)
        denom = max(0.01, 1.0 - po)
        return (pf - po) / denom

    observed = _tni(full_scores, oracle_scores)
    rng = random.Random(seed)
    nf, no = len(full_scores), len(oracle_scores)
    boot = sorted(
        _tni(
            [rng.choice(full_scores) for _ in range(nf)],
            [rng.choice(oracle_scores) for _ in range(no)],
        )
        for _ in range(n_boot)
    )
    lo = boot[max(0, int(math.floor(0.025 * n_boot)))]
    hi = boot[min(n_boot - 1, int(math.ceil(0.975 * n_boot)) - 1)]
    return observed, lo, hi


def per_task_analysis(records: list[RunRecord]) -> dict[str, dict]:
    """Per-task pass rates and analysis value across all models."""
    tasks = sorted({r.task_id for r in records})
    result = {}
    for task in tasks:
        task_recs = [r for r in records if r.task_id == task]
        full = [r.passed for r in task_recs if r.condition == "expertise_full"]
        oracle = [r.passed for r in task_recs if r.condition == "expertise_oracle"]
        no_anal = [r.passed for r in task_recs if r.condition == "expertise_no_analysis"]
        result[task] = {
            "full_rate": sum(full) / max(1, len(full)),
            "oracle_rate": sum(oracle) / max(1, len(oracle)),
            "no_analysis_rate": sum(no_anal) / max(1, len(no_anal)),
            "n_full": len(full),
            "analysis_value": sum(full) / max(1, len(full)) - sum(no_anal) / max(1, len(no_anal)),
        }
    return result


def per_model_analysis(records: list[RunRecord]) -> dict[str, dict]:
    """Per-model pass rates and comparisons."""
    models = sorted({r.model for r in records})
    result = {}
    for model in models:
        mrecs = [r for r in records if r.model == model]
        full = [r.passed for r in mrecs if r.condition == "expertise_full"]
        oracle = [r.passed for r in mrecs if r.condition == "expertise_oracle"]
        no_anal = [r.passed for r in mrecs if r.condition == "expertise_no_analysis"]
        if not full:
            continue
        tni, tni_lo, tni_hi = expertise_tni_with_ci(mrecs)
        full_rate, full_lo, full_hi = _bootstrap_rate(full)
        oracle_rate, oracle_lo, oracle_hi = _bootstrap_rate(oracle)
        no_anal_rate, _, _ = _bootstrap_rate(no_anal) if no_anal else (0.0, 0.0, 0.0)
        result[model] = {
            "n": len(full),
            "full_rate": full_rate,
            "full_ci": (full_lo, full_hi),
            "oracle_rate": oracle_rate,
            "oracle_ci": (oracle_lo, oracle_hi),
            "no_analysis_rate": no_anal_rate,
            "tni": tni,
            "tni_ci": (tni_lo, tni_hi),
            "analysis_value": full_rate - no_anal_rate,
            "p_full_vs_oracle": _permutation_test(full, oracle),
            "p_full_vs_no_anal": _permutation_test(full, no_anal) if no_anal else 1.0,
        }
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _sig_stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."


def print_report(records: list[RunRecord]) -> None:
    models = sorted({r.model for r in records})
    print("\n" + "=" * 80)
    print("TeamBench EA — TNI Statistical Validation Report")
    print("=" * 80)
    print(f"Total runs loaded: {len(records)}")
    print(f"Models: {', '.join(models)}")
    print(f"Tasks: {sorted({r.task_id for r in records})}")
    print()

    # --- Per-model table ---
    print("─" * 80)
    print("Per-Model Results (95% Bootstrap CI)")
    print("─" * 80)
    fmt = "{:<30} {:>6} {:>16} {:>16} {:>10} {:>14} {:>6} {:>6}"
    print(fmt.format("Model", "N", "Full (CI)", "Oracle (CI)", "AnalVal", "TNI (CI)", "p(F>O)", "p(F>A)"))
    print("─" * 80)

    model_data = per_model_analysis(records)
    for model, d in model_data.items():
        full_s = f"{d['full_rate']*100:.1f} [{d['full_ci'][0]*100:.1f},{d['full_ci'][1]*100:.1f}]%"
        ora_s = f"{d['oracle_rate']*100:.1f} [{d['oracle_ci'][0]*100:.1f},{d['oracle_ci'][1]*100:.1f}]%"
        tni_s = f"{d['tni']:.2f} [{d['tni_ci'][0]:.2f},{d['tni_ci'][1]:.2f}]" if not math.isnan(d['tni']) else "N/A"
        print(fmt.format(
            model[:30], d["n"],
            full_s, ora_s,
            f"+{d['analysis_value']*100:.1f}%",
            tni_s,
            f"{d['p_full_vs_oracle']:.3f}{_sig_stars(d['p_full_vs_oracle'])}",
            f"{d['p_full_vs_no_anal']:.3f}{_sig_stars(d['p_full_vs_no_anal'])}",
        ))
    print()

    # --- Pooled analysis (capable models only) ---
    capable_models = [m for m, d in model_data.items()
                      if d["full_rate"] > 0.05]  # exclude clearly incapable models
    pool = [r for r in records if r.model in capable_models]
    if pool:
        print("─" * 80)
        print(f"Pooled Analysis — Capable Models Only ({', '.join(capable_models)})")
        print("─" * 80)

        full_pool = [r.passed for r in pool if r.condition == "expertise_full"]
        ora_pool = [r.passed for r in pool if r.condition == "expertise_oracle"]
        no_anal_pool = [r.passed for r in pool if r.condition == "expertise_no_analysis"]

        for cond, scores in [
            ("expertise_full", full_pool),
            ("expertise_no_analysis", no_anal_pool),
            ("expertise_oracle", ora_pool),
        ]:
            rate, lo, hi = _bootstrap_rate(scores)
            print(f"  {cond:<30}: {rate*100:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]  (N={len(scores)})")

        print()

        # Key comparisons
        comps = [
            compare_conditions(pool, "expertise_full", "expertise_oracle", "Team vs Oracle"),
            compare_conditions(pool, "expertise_full", "expertise_no_analysis", "Team vs No-Analysis"),
            compare_conditions(pool, "expertise_no_analysis", "expertise_oracle", "No-Analysis vs Oracle"),
        ]
        tni, tni_lo, tni_hi = expertise_tni_with_ci(pool)

        print("  Pairwise Comparisons (pooled):")
        for c in comps:
            sig = _sig_stars(c.p_value)
            print(f"  {c.label:<30}: diff={c.diff*100:+.1f}% "
                  f"[{c.diff_ci_lo*100:+.1f}%, {c.diff_ci_hi*100:+.1f}%] "
                  f"p={c.p_value:.3f}{sig}  "
                  f"(need N={c.min_n_for_power} per cond for 80% power)")
        print(f"\n  Pooled TNI: {tni:.3f} [{tni_lo:.3f}, {tni_hi:.3f}]")

        # Is the CI on TNI entirely above 0?
        if tni_lo > 0:
            print("  ✓ Pooled TNI CI entirely above 0 — team benefit is significant")
        else:
            print("  ✗ Pooled TNI CI includes 0 — result is not conclusive with current N")
        print()

    # --- Per-task breakdown ---
    print("─" * 80)
    print("Per-Task Analysis (across all capable models)")
    print("─" * 80)
    task_data = per_task_analysis([r for r in records if r.model in capable_models] if capable_models else records)
    print(f"{'Task':<30} {'Full':>7} {'Oracle':>7} {'NoAnal':>7} {'AnalVal':>9} {'N':>4}")
    print("─" * 80)
    for task, d in task_data.items():
        print(f"{task:<30} {d['full_rate']*100:>6.1f}% {d['oracle_rate']*100:>6.1f}% "
              f"{d['no_analysis_rate']*100:>6.1f}% {d['analysis_value']*100:>+8.1f}%  {d['n_full']:>3}")
    print()

    # --- Sample size guidance ---
    print("─" * 80)
    print("Statistical Power Analysis")
    print("─" * 80)
    if pool:
        pf = sum(r.passed for r in pool if r.condition == "expertise_full") / max(1, len([r for r in pool if r.condition == "expertise_full"]))
        po = sum(r.passed for r in pool if r.condition == "expertise_oracle") / max(1, len([r for r in pool if r.condition == "expertise_oracle"]))
        pa = sum(r.passed for r in pool if r.condition == "expertise_no_analysis") / max(1, len([r for r in pool if r.condition == "expertise_no_analysis"]))
        n_fo = _min_n_for_power(pf, po)
        n_fa = _min_n_for_power(pf, pa)
        print(f"  Current N per condition (pooled): {len(full_pool)}")
        print(f"  Observed full={pf*100:.1f}%, oracle={po*100:.1f}%, no-analysis={pa*100:.1f}%")
        print(f"  Min N to detect full>oracle diff at α=0.05, power=0.80: {n_fo}")
        print(f"  Min N to detect full>no-analysis diff at α=0.05, power=0.80: {n_fa}")
        if len(full_pool) >= n_fo:
            print(f"  ✓ Adequately powered to detect full>oracle difference")
        else:
            print(f"  ✗ Underpowered for full>oracle (have {len(full_pool)}, need {n_fo})")
        if len(full_pool) >= n_fa:
            print(f"  ✓ Adequately powered to detect full>no-analysis difference")
        else:
            print(f"  ✗ Underpowered for full>no-analysis (have {len(full_pool)}, need {n_fa})")
    print()


def latex_table(records: list[RunRecord]) -> str:
    """Generate LaTeX table for paper."""
    model_data = per_model_analysis(records)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{EA Experiment Results: Expertise-Asymmetry Team vs.\ Single Agent (95\% CI).}",
        r"\label{tab:ea-results}",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"Model & Full Team & Oracle & No-Analysis & $\Delta_{\text{anal}}$ & TNI \\",
        r"\midrule",
    ]
    for model, d in model_data.items():
        short = model.replace("gemini-", "G-").replace("-preview", "")
        sig_fo = _sig_stars(d["p_full_vs_oracle"])
        tni_s = (f"{d['tni']:.2f} [{d['tni_ci'][0]:.2f},{d['tni_ci'][1]:.2f}]"
                 if not math.isnan(d["tni"]) else "--")
        lines.append(
            f"{short} & "
            f"{d['full_rate']*100:.1f}\\% [{d['full_ci'][0]*100:.0f},{d['full_ci'][1]*100:.0f}] & "
            f"{d['oracle_rate']*100:.1f}\\%$^{{{sig_fo}}}$ & "
            f"{d['no_analysis_rate']*100:.1f}\\% & "
            f"{d['analysis_value']*100:+.1f}pp & "
            f"{tni_s} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\multicolumn{6}{l}{\small $^*p<0.05$, $^{**}p<0.01$, $^{***}p<0.001$ (permutation test, one-sided).}\\",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="TeamBench TNI Statistical Validation")
    ap.add_argument("--results-dir", default="shared/ea_results",
                    help="Directory containing EA result JSON files")
    ap.add_argument("--model", nargs="*", dest="models",
                    help="Filter to specific models (default: all)")
    ap.add_argument("--latex", action="store_true",
                    help="Print LaTeX table for paper")
    ap.add_argument("--output", help="Write JSON validation report to file")
    ap.add_argument("--n-boot", type=int, default=10_000,
                    help="Bootstrap resamples (default: 10000)")
    args = ap.parse_args()

    records = load_results(args.results_dir, args.models)
    if not records:
        print(f"No EA results found in {args.results_dir}")
        return

    print_report(records)

    if args.latex:
        print("\n" + "=" * 80)
        print("LaTeX Table")
        print("=" * 80)
        print(latex_table(records))

    if args.output:
        model_data = per_model_analysis(records)
        capable = [m for m, d in model_data.items() if d["full_rate"] > 0.05]
        pool = [r for r in records if r.model in capable]
        tni, tni_lo, tni_hi = expertise_tni_with_ci(pool)

        out = {
            "n_records": len(records),
            "models": list(model_data.keys()),
            "capable_models": capable,
            "per_model": {
                m: {k: v for k, v in d.items() if not isinstance(v, tuple)}
                | {"full_ci": list(d["full_ci"]), "oracle_ci": list(d["oracle_ci"]),
                   "tni_ci": list(d["tni_ci"])}
                for m, d in model_data.items()
            },
            "pooled": {
                "n_full": sum(1 for r in pool if r.condition == "expertise_full"),
                "tni": tni,
                "tni_ci": [tni_lo, tni_hi],
                "tni_significant": tni_lo > 0,
            },
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nJSON report written to {args.output}")


if __name__ == "__main__":
    main()
