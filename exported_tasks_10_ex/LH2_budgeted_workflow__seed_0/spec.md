# LH2: Budgeted Workflow

## Goal
Complete a multi-step task within a strict command execution budget.

## Hard Requirements

1. Run `python budgeted_task.py` to process data files.
2. The task requires finding and fixing 3 broken data files in `data/`.
3. **Budget**: Maximum 28 command executions total.
4. All 3 data files must be fixed. Each file contains a data quality defect that prevents it from passing validation:
   - `data/file_a.json`: contains a field named `ver` whose name does not match the required schema field name `version`.
   - `data/file_b.json`: contains a datetime field (`2025-07-04T15:00:00`) whose value is missing required timezone information.
   - `data/file_c.json`: contains an array field with case-insensitive duplicate entries ["OPEN", "open", "resolved", "Close", "close"] that must be deduplicated, retaining only the lowercase form of each duplicate group.
5. After fixing, run `python validate_all.py` which checks all files.
6. Final output: `output/budget_report.json`
7. `budget_used` must be <= 28.

## Deliverables
- Fixed data files + `output/budget_report.json`.
- Verifier must confirm budget compliance and produce attestation.
