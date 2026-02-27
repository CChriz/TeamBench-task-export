# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `cd /workspace && python -m pytest --cov=validator --cov-branch --cov-report=term-missing 2>&1` — shows exact uncovered lines
- `find /workspace -name "*.py" | head -20` — explore structure
- `python -m coverage report -m 2>&1` — detailed branch report

## Expected Findings
Coverage gaps are in 3 modules:
- `validator/core.py`: ~8 uncovered branches (boundary conditions, edge cases)
- `validator/rules.py`: ~7 uncovered branches (None values, wrong types, edge cases)
- `validator/pipeline.py`: ~5 uncovered branches (empty states, early exits)

## False Positives to Ignore
None — all coverage gaps are genuine untested paths.

## Key Insight
The coverage tool will show `-> exit` branch notation for conditions.
Write tests that exercise the ELSE branches of existing if-statements.
