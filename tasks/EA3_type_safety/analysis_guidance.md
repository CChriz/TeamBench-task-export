# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `cd /workspace && mypy app/ --ignore-missing-imports --strict 2>&1` — primary type checker
- `mypy app/ --ignore-missing-imports 2>&1` — less strict, shows same errors
- `find /workspace/app -name "*.py"` — list files

## Expected Findings (15 errors)
- `app/models.py`: 3 errors (Any type, missing return annotation, bare list)
- `app/service.py`: 5 errors (missing annotations, wrong literal type, return mismatch)
- `app/utils.py`: 4 errors (missing annotations, bare Dict)
- `app/dynamic.py`: 3 errors (dynamic dispatch, any-return, operator)

## False Positives (Errors Needing type:ignore, NOT code changes)
- `app/dynamic.py` line ~10: dynamic getattr call — add `# type: ignore[no-untyped-call]`
- `app/dynamic.py` line ~22: plugin registry return — add `# type: ignore[no-any-return]`
- `app/dynamic.py` line ~31: runtime cast — add `# type: ignore[operator]`

## Key Distinction
12 errors need real code fixes (add type annotations, fix literal types, fix return values).
3 errors in `app/dynamic.py` should get `# type: ignore` comments — NOT code changes.
