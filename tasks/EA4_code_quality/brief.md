# EA4: Code Quality (Brief)

A Python module has code quality issues. The Planner will run ruff and pylint to identify violations.

Fix the lint violations to achieve:
- `ruff check app/` reports 0 errors
- `pylint app/` score ≥ 9.0/10

Some violations are intentional style choices that must be preserved — the Planner will specify which.
