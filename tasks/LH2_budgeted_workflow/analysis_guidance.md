# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" | head -20`
- `ruff check /workspace --select=E,F,B 2>&1`
- `python -m py_compile` on workflow scripts
- `grep -n "budget\|cost\|limit\|constraint" /workspace/*.py 2>&1 | head -20`

## Expected Findings
Long-horizon workflow tasks often have:
- Missing budget enforcement in loop termination conditions
- Off-by-one errors in resource counting
- Missing rollback on budget exceeded

## False Positives to Ignore
None specific — evaluate each finding against the budget constraints in spec.md.

## Key Insight
This is a multi-step workflow with budget constraints. Check that every step that consumes resources correctly checks and updates the budget counter.
