"""
Parameterized generator for NEG4: Resource Allocation.

Each seed produces:
  - Different team names and priorities
  - Different budget amounts and quotas
  - Same 3 bug types: priority inversion, starvation, wrong quota calc

The 3 bugs are always:
  1. Sort teams by priority ascending (should be descending)
  2. Only allocate to first team (should distribute to all)
  3. Use integer division // (should use round())
"""
from __future__ import annotations

import json
import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

TEAM_POOLS = [
    [("alpha", 10, 20, 60), ("beta", 7, 15, 50), ("gamma", 3, 10, 40)],
    [("frontend", 9, 25, 70), ("backend", 6, 20, 55), ("infra", 4, 15, 45)],
    [("ml_team", 8, 30, 80), ("data_eng", 5, 20, 60), ("analytics", 3, 10, 40)],
    [("search", 10, 25, 65), ("ads", 7, 20, 55), ("platform", 4, 15, 45)],
    [("core", 9, 30, 75), ("growth", 6, 20, 50), ("ops", 3, 10, 35)],
]

BUDGETS = [100, 120, 150, 130, 110]


class Generator(TaskGenerator):
    task_id = "NEG4_resource_allocation"
    domain = "operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        teams = TEAM_POOLS[seed % len(TEAM_POOLS)]
        total_budget = BUDGETS[seed % len(BUDGETS)]

        team_defs = []
        for name, prio, min_q, max_q in teams:
            team_defs.append({
                "name": name,
                "priority": prio,
                "min_quota": min_q,
                "max_quota": max_q,
                "requested": max_q,
            })

        workspace_files = {
            "allocator.py": self._gen_allocator(team_defs, total_budget),
            "budget.yaml": self._gen_budget_yaml(team_defs, total_budget),
            "test_allocator.py": self._gen_tests(team_defs, total_budget),
        }

        expected = {
            "seed": seed,
            "total_budget": total_budget,
            "teams": [{"name": t["name"], "priority": t["priority"],
                        "min_quota": t["min_quota"], "max_quota": t["max_quota"]}
                       for t in team_defs],
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

    def _gen_allocator(self, team_defs, total_budget):
        teams_repr = ",\n        ".join(
            f'{{"name": "{t["name"]}", "priority": {t["priority"]}, '
            f'"min_quota": {t["min_quota"]}, "max_quota": {t["max_quota"]}, '
            f'"requested": {t["requested"]}}}'
            for t in team_defs
        )
        return f'''"""Resource allocation algorithm for shared compute budget."""
import yaml
import os


def load_budget(path="budget.yaml"):
    """Load budget configuration from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def allocate(budget_path="budget.yaml"):
    """Allocate compute resources to teams based on priority and quotas.

    Returns dict mapping team name -> allocated units.
    """
    budget = load_budget(budget_path)
    total = budget["total_budget"]
    teams = budget["teams"]

    # Sort by priority (BUG: ascending instead of descending)
    teams_sorted = sorted(teams, key=lambda t: t["priority"])

    result = {{}}
    remaining = total

    # BUG: only allocate to the first team, skip the rest
    if teams_sorted:
        team = teams_sorted[0]
        alloc = min(team["requested"], team["max_quota"], remaining)
        # BUG: integer division truncates fractional units
        share = remaining // len(teams_sorted)
        alloc = min(share, team["max_quota"])
        result[team["name"]] = alloc
        remaining -= alloc

    return result
'''

    def _gen_budget_yaml(self, team_defs, total_budget):
        lines = [f"total_budget: {total_budget}", "teams:"]
        for t in team_defs:
            lines.append(f"  - name: {t['name']}")
            lines.append(f"    priority: {t['priority']}")
            lines.append(f"    min_quota: {t['min_quota']}")
            lines.append(f"    max_quota: {t['max_quota']}")
            lines.append(f"    requested: {t['requested']}")
        return "\n".join(lines) + "\n"

    def _gen_tests(self, team_defs, total_budget):
        team_names = [t["name"] for t in team_defs]
        highest_prio_team = max(team_defs, key=lambda t: t["priority"])
        lowest_prio_team = min(team_defs, key=lambda t: t["priority"])

        return f'''"""
Test suite for NEG4_resource_allocation. Do NOT modify.
"""
import unittest


class AllocatorTestCase(unittest.TestCase):

    def test_imports(self):
        from allocator import allocate, load_budget

    def test_all_teams_get_allocation(self):
        from allocator import allocate
        result = allocate()
        for name in {team_names!r}:
            self.assertIn(name, result, f"{{name}} missing from allocation")
            self.assertGreater(result[name], 0, f"{{name}} got 0")

    def test_priority_order(self):
        from allocator import allocate, load_budget
        budget = load_budget()
        result = allocate()
        teams_by_prio = sorted(budget["teams"], key=lambda t: t["priority"], reverse=True)
        # Highest priority team must get >= lowest priority team
        high = result[teams_by_prio[0]["name"]]
        low = result[teams_by_prio[-1]["name"]]
        self.assertGreaterEqual(high, low,
                                msg=f"Priority inversion: {{teams_by_prio[0]['name']}}={{high}} < {{teams_by_prio[-1]['name']}}={{low}}")

    def test_min_quota_respected(self):
        from allocator import allocate, load_budget
        budget = load_budget()
        result = allocate()
        for team in budget["teams"]:
            self.assertGreaterEqual(result[team["name"]], team["min_quota"],
                                    msg=f"{{team['name']}} below min_quota")

    def test_max_quota_respected(self):
        from allocator import allocate, load_budget
        budget = load_budget()
        result = allocate()
        for team in budget["teams"]:
            self.assertLessEqual(result[team["name"]], team["max_quota"],
                                 msg=f"{{team['name']}} exceeds max_quota")

    def test_total_matches_budget(self):
        from allocator import allocate, load_budget
        budget = load_budget()
        result = allocate()
        total = sum(result.values())
        self.assertAlmostEqual(total, budget["total_budget"], delta=1,
                               msg=f"Total {{total}} != budget {{budget['total_budget']}}")

    def test_no_starvation(self):
        from allocator import allocate
        result = allocate()
        self.assertEqual(len(result), {len(team_defs)},
                         msg=f"Expected {len(team_defs)} teams, got {{len(result)}}")

    def test_highest_priority_gets_fair_share(self):
        from allocator import allocate
        result = allocate()
        highest = result["{highest_prio_team['name']}"]
        self.assertGreaterEqual(highest, {highest_prio_team['min_quota']})


if __name__ == "__main__":
    unittest.main()
'''
