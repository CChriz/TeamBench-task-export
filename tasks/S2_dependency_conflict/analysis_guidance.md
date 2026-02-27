# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `cat /workspace/requirements.txt 2>/dev/null || find /workspace -name "requirements*.txt"` — dependency files
- `pip check 2>&1` — detect dependency conflicts
- `ruff check /workspace --select=E,F,B 2>&1` — code issues
- `python -m py_compile` on main modules

## Expected Findings
- Dependency version conflicts in requirements.txt
- Import errors from incompatible versions
- API usage that doesn't match pinned versions

## False Positives to Ignore
Not all pip check warnings are task-relevant — focus on conflicts that cause the tests to fail.

## Key Insight
Run `pip install -r requirements.txt 2>&1` and `pytest 2>&1` to see which dependencies conflict and which tests fail.
