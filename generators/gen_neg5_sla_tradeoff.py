"""
Parameterized generator for NEG5: SLA Tradeoff.

Each seed produces:
  - Different tier names and specific numeric values
  - Different latency/availability thresholds
  - Same 3 bug types: impossible latency+consistency, impossible availability+consistency,
    impossible latency+availability

The 3 buggy tiers always violate CAP-inspired constraints:
  1. Premium: strong consistency + too-low latency
  2. Enterprise: strong consistency + too-high availability
  3. Realtime: low latency + too-high availability
"""
from __future__ import annotations

import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

TIER_CONFIGS = [
    {
        "names": ["basic", "standard", "premium", "enterprise", "realtime"],
        "min_latency_strong": 50, "max_avail_strong": 99.9,
        "min_latency_high_avail": 100, "high_avail_threshold": 99.99,
        "premium_bad_latency": 20, "enterprise_bad_avail": 99.999,
        "realtime_bad_avail": 99.99, "realtime_latency": 10,
    },
    {
        "names": ["free", "starter", "premium", "enterprise", "realtime"],
        "min_latency_strong": 60, "max_avail_strong": 99.9,
        "min_latency_high_avail": 120, "high_avail_threshold": 99.99,
        "premium_bad_latency": 25, "enterprise_bad_avail": 99.999,
        "realtime_bad_avail": 99.99, "realtime_latency": 15,
    },
    {
        "names": ["bronze", "silver", "premium", "enterprise", "realtime"],
        "min_latency_strong": 50, "max_avail_strong": 99.9,
        "min_latency_high_avail": 100, "high_avail_threshold": 99.99,
        "premium_bad_latency": 30, "enterprise_bad_avail": 99.99,
        "realtime_bad_avail": 99.99, "realtime_latency": 5,
    },
    {
        "names": ["dev", "team", "premium", "enterprise", "realtime"],
        "min_latency_strong": 55, "max_avail_strong": 99.9,
        "min_latency_high_avail": 110, "high_avail_threshold": 99.99,
        "premium_bad_latency": 15, "enterprise_bad_avail": 99.999,
        "realtime_bad_avail": 99.99, "realtime_latency": 8,
    },
    {
        "names": ["hobby", "pro", "premium", "enterprise", "realtime"],
        "min_latency_strong": 50, "max_avail_strong": 99.9,
        "min_latency_high_avail": 100, "high_avail_threshold": 99.99,
        "premium_bad_latency": 10, "enterprise_bad_avail": 99.999,
        "realtime_bad_avail": 99.99, "realtime_latency": 12,
    },
]


class Generator(TaskGenerator):
    task_id = "NEG5_sla_tradeoff"
    domain = "operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = TIER_CONFIGS[seed % len(TIER_CONFIGS)]

        workspace_files = {
            "tiers.py": self._gen_tiers(cfg),
            "constraints.py": self._gen_constraints(cfg),
            "test_tiers.py": self._gen_tests(cfg),
        }

        expected = {
            "seed": seed,
            "tier_names": cfg["names"],
            "min_latency_strong": cfg["min_latency_strong"],
            "max_avail_strong": cfg["max_avail_strong"],
            "min_latency_high_avail": cfg["min_latency_high_avail"],
            "fixes": {
                "premium": f"latency_ms from {cfg['premium_bad_latency']} to {cfg['min_latency_strong']}",
                "enterprise": f"availability from {cfg['enterprise_bad_avail']} to {cfg['max_avail_strong']}",
                "realtime": f"availability from {cfg['realtime_bad_avail']} to {cfg['max_avail_strong']}",
            },
        }

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Negotiation"},
        )

    def _gen_tiers(self, cfg):
        names = cfg["names"]
        return f'''"""Service tier definitions with SLA targets."""

TIERS = {{
    "{names[0]}": {{
        "latency_ms": 500,
        "consistency": "eventual",
        "availability_pct": 99.0,
    }},
    "{names[1]}": {{
        "latency_ms": 200,
        "consistency": "eventual",
        "availability_pct": 99.5,
    }},
    "premium": {{
        "latency_ms": {cfg["premium_bad_latency"]},
        "consistency": "strong",
        "availability_pct": 99.5,
    }},
    "enterprise": {{
        "latency_ms": 100,
        "consistency": "strong",
        "availability_pct": {cfg["enterprise_bad_avail"]},
    }},
    "realtime": {{
        "latency_ms": {cfg["realtime_latency"]},
        "consistency": "eventual",
        "availability_pct": {cfg["realtime_bad_avail"]},
    }},
}}
'''

    def _gen_constraints(self, cfg):
        return f'''"""SLA constraint checker. Do NOT modify."""


def check_tier(tier):
    """Check if a tier definition is physically achievable.

    Returns list of constraint violations (empty = valid).
    """
    errors = []

    latency = tier.get("latency_ms", 0)
    consistency = tier.get("consistency", "eventual")
    availability = tier.get("availability_pct", 0)

    # Constraint 1: Strong consistency requires minimum latency
    if consistency == "strong" and latency < {cfg["min_latency_strong"]}:
        errors.append(
            f"strong consistency requires latency >= {cfg['min_latency_strong']}ms, got {{latency}}ms"
        )

    # Constraint 2: Strong consistency limits max availability
    if consistency == "strong" and availability > {cfg["max_avail_strong"]}:
        errors.append(
            f"strong consistency limits availability to {cfg['max_avail_strong']}%, got {{availability}}%"
        )

    # Constraint 3: High availability requires minimum latency
    if availability >= {cfg["high_avail_threshold"]} and latency < {cfg["min_latency_high_avail"]}:
        errors.append(
            f"availability >= {cfg['high_avail_threshold']}% requires latency >= {cfg['min_latency_high_avail']}ms, got {{latency}}ms"
        )

    return errors
'''

    def _gen_tests(self, cfg):
        names = cfg["names"]
        return f'''"""
Test suite for NEG5_sla_tradeoff. Do NOT modify.
"""
import unittest


class TierTestCase(unittest.TestCase):

    def test_import(self):
        from tiers import TIERS
        from constraints import check_tier

    def test_five_tiers(self):
        from tiers import TIERS
        self.assertEqual(len(TIERS), 5)

    def test_all_tiers_valid(self):
        from tiers import TIERS
        from constraints import check_tier
        for name, tier in TIERS.items():
            errors = check_tier(tier)
            self.assertEqual(errors, [], msg=f"{{name}}: {{errors}}")

    def test_premium_strong_consistency(self):
        from tiers import TIERS
        self.assertEqual(TIERS["premium"]["consistency"], "strong")

    def test_premium_achievable_latency(self):
        from tiers import TIERS
        self.assertGreaterEqual(TIERS["premium"]["latency_ms"], {cfg["min_latency_strong"]})

    def test_enterprise_strong_consistency(self):
        from tiers import TIERS
        self.assertEqual(TIERS["enterprise"]["consistency"], "strong")

    def test_enterprise_achievable_availability(self):
        from tiers import TIERS
        self.assertLessEqual(TIERS["enterprise"]["availability_pct"], {cfg["max_avail_strong"]})

    def test_realtime_low_latency(self):
        from tiers import TIERS
        self.assertLessEqual(TIERS["realtime"]["latency_ms"], {cfg["min_latency_strong"]})

    def test_realtime_achievable_availability(self):
        from tiers import TIERS
        self.assertLess(TIERS["realtime"]["availability_pct"], {cfg["high_avail_threshold"]})

    def test_basic_tiers_unchanged(self):
        from tiers import TIERS
        self.assertIn("{names[0]}", TIERS)
        self.assertIn("{names[1]}", TIERS)


if __name__ == "__main__":
    unittest.main()
'''
