# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" | head -30` — explore structure
- `ruff check /workspace --select=E,F,B 2>&1` — code issues
- `python -m py_compile` on main files — syntax validation

## Expected Findings
This task has hidden constraints that static analysis may partially surface:
- Unused imports or variables that hint at missing functionality
- Type inconsistencies that reveal edge cases
- Dead code paths that indicate unimplemented branches

## False Positives to Ignore
Focus on findings that align with requirements in spec.md. Not every lint warning is a task requirement.

## Key Insight
Read spec.md carefully — the "hidden" constraints are in the specification detail. Use static analysis to verify the implementation matches all spec constraints.
