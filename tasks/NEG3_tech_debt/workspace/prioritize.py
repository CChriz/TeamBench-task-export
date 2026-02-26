"""
Tech debt prioritization script.

Edit `plan` below to declare which items you will fix and in what order.
Then run: python prioritize.py

The script validates your plan against the time budget and dependency rules.
"""
import json

# ── Your plan ─────────────────────────────────────────────────────────────────
# List the IDs of the tech debt items you will fix, in the order you will fix them.
# You may fix at most 3 items within the 6-hour time budget.
PLAN: list[str] = [
    # e.g. "TD001", "TD002", "TD003"
]

# ── Validation ────────────────────────────────────────────────────────────────

def validate_plan(plan: list[str], registry_path: str = "tech_debt.json") -> dict:
    with open(registry_path) as f:
        registry = json.load(f)

    items_by_id = {item["id"]: item for item in registry["items"]}
    budget = registry["time_budget_hours"]
    max_items = registry["max_items_to_fix"]
    dependency = registry.get("dependency")

    issues = []

    # Check: all IDs are valid
    for tid in plan:
        if tid not in items_by_id:
            issues.append(f"Unknown item ID: {tid}")

    # Check: at most max_items
    if len(plan) > max_items:
        issues.append(f"Plan selects {len(plan)} items but max is {max_items}")

    # Check: time budget
    total_hours = sum(items_by_id[tid]["fix_hours"] for tid in plan if tid in items_by_id)
    if total_hours > budget:
        issues.append(f"Plan requires {total_hours}h but budget is {budget}h")

    # Check: dependency order
    if dependency:
        blocker = dependency["blocker"]
        dependent = dependency["dependent"]
        if blocker in plan and dependent in plan:
            if plan.index(blocker) > plan.index(dependent):
                issues.append(
                    f"Dependency violation: {blocker} must come before {dependent}"
                )
        elif dependent in plan and blocker not in plan:
            issues.append(
                f"Dependency violation: {dependent} requires {blocker} to be fixed first"
            )

    # Compute value
    total_value = sum(items_by_id[tid]["value_score"] for tid in plan if tid in items_by_id)

    return {
        "plan": plan,
        "total_hours": total_hours,
        "total_value": total_value,
        "budget_hours": budget,
        "dependency": dependency,
        "issues": issues,
        "valid": len(issues) == 0,
    }


def main():
    import sys
    result = validate_plan(PLAN)

    print("=== TECH DEBT PRIORITIZATION PLAN ===")
    print(f"Items selected: {len(result['plan'])} / 3 max")
    print(f"Total hours:    {result['total_hours']} / {result['budget_hours']} budget")
    print(f"Total value:    {result['total_value']} points")
    print()

    if result["dependency"]:
        dep = result["dependency"]
        print(f"Dependency constraint: {dep['blocker']} must precede {dep['dependent']}")
    print()

    if result["issues"]:
        print("VALIDATION ISSUES:")
        for issue in result["issues"]:
            print(f"  - {issue}")
        print()
        print("PLAN INVALID")
        sys.exit(1)
    else:
        print("PLAN VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
