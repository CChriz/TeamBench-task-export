"""
Statistical utilities for TeamBench analysis.

Provides bootstrap confidence intervals, significance tests,
and sample size calculations for reliable model comparisons.
"""
from __future__ import annotations

import math
import random
from typing import Sequence


def bootstrap_ci(
    scores: Sequence[bool],
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap confidence interval for a binary pass/fail score list.

    Args:
        scores: Sequence of bool (True = pass, False = fail)
        n_bootstrap: number of bootstrap resamples
        alpha: significance level (e.g., 0.05 for 95% CI)
        seed: random seed for reproducibility

    Returns:
        (mean, lower_bound, upper_bound) where bounds form a (1-alpha) CI
    """
    if not scores:
        return (0.0, 0.0, 0.0)

    scores_list = [float(s) for s in scores]
    n = len(scores_list)
    mean = sum(scores_list) / n

    rng = random.Random(seed)
    boot_means: list[float] = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(scores_list) for _ in range(n)]
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    lower_idx = int(math.floor((alpha / 2) * n_bootstrap))
    upper_idx = int(math.ceil((1 - alpha / 2) * n_bootstrap)) - 1
    lower_idx = max(0, lower_idx)
    upper_idx = min(n_bootstrap - 1, upper_idx)

    return (mean, boot_means[lower_idx], boot_means[upper_idx])


def bootstrap_ci_difference(
    scores_a: Sequence[bool],
    scores_b: Sequence[bool],
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap confidence interval on the difference in pass rates between two models.

    Computes CI for (mean_a - mean_b).

    Args:
        scores_a: pass/fail list for model A
        scores_b: pass/fail list for model B
        n_bootstrap: number of bootstrap resamples
        alpha: significance level
        seed: random seed

    Returns:
        (observed_diff, lower_bound, upper_bound)
        Positive values indicate A outperforms B.
    """
    if not scores_a or not scores_b:
        return (0.0, 0.0, 0.0)

    a = [float(s) for s in scores_a]
    b = [float(s) for s in scores_b]
    n_a, n_b = len(a), len(b)
    observed_diff = sum(a) / n_a - sum(b) / n_b

    rng = random.Random(seed)
    boot_diffs: list[float] = []
    for _ in range(n_bootstrap):
        sample_a = [rng.choice(a) for _ in range(n_a)]
        sample_b = [rng.choice(b) for _ in range(n_b)]
        boot_diffs.append(sum(sample_a) / n_a - sum(sample_b) / n_b)

    boot_diffs.sort()
    lower_idx = int(math.floor((alpha / 2) * n_bootstrap))
    upper_idx = int(math.ceil((1 - alpha / 2) * n_bootstrap)) - 1
    lower_idx = max(0, lower_idx)
    upper_idx = min(n_bootstrap - 1, upper_idx)

    return (observed_diff, boot_diffs[lower_idx], boot_diffs[upper_idx])


def mcnemar_test(
    scores_a: Sequence[bool],
    scores_b: Sequence[bool],
) -> tuple[float, float]:
    """
    McNemar's paired test for comparing two models on the same set of instances.

    Both sequences must be aligned (same order of instances).

    The test focuses on discordant pairs:
      - b01: A fails, B passes
      - b10: A passes, B fails

    Uses the continuity-corrected statistic for small samples.

    Args:
        scores_a: pass/fail list for model A (aligned with B)
        scores_b: pass/fail list for model B (aligned with A)

    Returns:
        (statistic, p_value) — chi-squared statistic and two-tailed p-value
        Raises ValueError if lists are different lengths or both are empty.
    """
    if len(scores_a) != len(scores_b):
        raise ValueError(
            f"scores_a and scores_b must have equal length, "
            f"got {len(scores_a)} and {len(scores_b)}"
        )
    if not scores_a:
        raise ValueError("scores_a and scores_b must not be empty")

    b01 = sum(1 for a, b in zip(scores_a, scores_b) if not a and b)   # A fail, B pass
    b10 = sum(1 for a, b in zip(scores_a, scores_b) if a and not b)   # A pass, B fail

    discordant = b01 + b10
    if discordant == 0:
        # No discordant pairs — models agree on all instances
        return (0.0, 1.0)

    # Continuity-corrected McNemar statistic
    statistic = (abs(b10 - b01) - 1) ** 2 / discordant

    # p-value from chi-squared(1) distribution
    p_value = _chi2_sf(statistic, df=1)

    return (statistic, p_value)


def _chi2_sf(x: float, df: int = 1) -> float:
    """
    Survival function (1 - CDF) of the chi-squared distribution.

    Implemented for df=1 using the relationship:
        chi2_sf(x, 1) = erfc(sqrt(x/2))
    """
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2))
    # For df > 1, use regularized incomplete gamma function approximation
    # For typical use (df=1), the above is exact.
    return _regularized_upper_gamma(df / 2, x / 2)


def _regularized_upper_gamma(a: float, x: float) -> float:
    """Regularized upper incomplete gamma function Q(a, x) via series expansion."""
    if x < 0:
        return 1.0
    if x == 0:
        return 1.0
    # Use continued fraction representation for large x, series for small x
    if x < a + 1:
        # Series representation
        term = 1.0 / a
        total = term
        for n in range(1, 300):
            term *= x / (a + n)
            total += term
            if abs(term) < 1e-12 * abs(total):
                break
        return 1.0 - total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    else:
        # Lentz's continued fraction
        fpmin = 1e-300
        b = x + 1 - a
        c = 1 / fpmin
        d = 1 / b
        h = d
        for i in range(1, 300):
            an = -i * (i - a)
            b += 2
            d = an * d + b
            if abs(d) < fpmin:
                d = fpmin
            c = b + an / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1 / d
            delta = d * c
            h *= delta
            if abs(delta - 1) < 1e-12:
                break
        return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def required_sample_size(
    effect_size: float = 0.05,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """
    Estimate the minimum number of task instances needed to detect a given effect.

    Uses a normal-approximation formula for two-proportion z-test.

    Args:
        effect_size: minimum detectable difference in pass rates (e.g., 0.05 = 5pp)
        alpha: significance level (Type I error rate)
        power: desired statistical power (1 - Type II error rate)

    Returns:
        Minimum number of instances per model (integer, >= 1)
    """
    if effect_size <= 0:
        raise ValueError("effect_size must be positive")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    if not (0 < power < 1):
        raise ValueError("power must be in (0, 1)")

    # z critical values via inverse normal approximation
    z_alpha = _z_from_p(alpha / 2)   # two-tailed
    z_beta = _z_from_p(1 - power)

    # Assume base rate p = 0.5 (most conservative estimate of variance)
    p = 0.5
    n = (z_alpha + z_beta) ** 2 * 2 * p * (1 - p) / (effect_size ** 2)
    return max(1, math.ceil(n))


def _z_from_p(p: float) -> float:
    """Approximate inverse normal CDF (probit) for p in (0, 1)."""
    # Rational approximation (Abramowitz & Stegun 26.2.23)
    if p <= 0 or p >= 1:
        raise ValueError(f"p must be in (0, 1), got {p}")
    if p > 0.5:
        return -_z_from_p(1 - p)
    t = math.sqrt(-2 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    z = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
    return z


def pass_at_k_with_ci(
    n_correct: int,
    n_total: int,
    k: int,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """
    Estimate Pass@k with a Wilson score confidence interval on the underlying pass rate.

    Pass@k = 1 - (1 - p)^k where p = n_correct / n_total.

    The CI is computed on p using the Wilson interval, then transformed
    via the monotone mapping x -> 1 - (1-x)^k.

    Args:
        n_correct: number of successful attempts
        n_total: total number of attempts
        k: number of independent attempts per instance
        alpha: significance level for the CI

    Returns:
        (pass_at_k, lower_bound, upper_bound)
        All values are in [0, 1].

    Raises:
        ValueError if n_total <= 0 or n_correct > n_total or k < 1.
    """
    if n_total <= 0:
        raise ValueError("n_total must be positive")
    if n_correct < 0 or n_correct > n_total:
        raise ValueError("n_correct must be in [0, n_total]")
    if k < 1:
        raise ValueError("k must be >= 1")

    p_hat = n_correct / n_total
    pass_k = 1.0 - (1.0 - p_hat) ** k

    # Wilson score interval on p_hat
    z = _z_from_p(alpha / 2)  # e.g., 1.96 for alpha=0.05
    denom = 1 + z ** 2 / n_total
    centre = (p_hat + z ** 2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p_hat * (1 - p_hat) / n_total + z ** 2 / (4 * n_total ** 2)) / denom

    p_lower = max(0.0, centre - margin)
    p_upper = min(1.0, centre + margin)

    # Transform CI bounds via 1 - (1-p)^k (monotone, so bounds preserve order)
    lower = 1.0 - (1.0 - p_lower) ** k
    upper = 1.0 - (1.0 - p_upper) ** k

    return (pass_k, lower, upper)
