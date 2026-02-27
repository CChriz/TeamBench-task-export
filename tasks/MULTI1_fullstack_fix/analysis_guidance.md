# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `cd /workspace && python -m py_compile app.py 2>&1` — syntax check backend
- `ruff check /workspace --select=E,F,B 2>&1` — detect code issues
- `grep -n "request\.\|json\|query" /workspace/app.py 2>&1` — find API issues
- `find /workspace -name "*.js" -o -name "*.html" | head -10` — frontend files

## Expected Findings
ruff/grep will reveal:
- `app.py`: request data source mismatch (form vs json), wrong SQL column reference
- `app.py`: query result ordering (ASC vs DESC for newest-first)
- `app.js`: frontend API call issues
- `deploy.sh`: shell script bugs

## False Positives to Ignore
None — all 6 bugs are real.

## Key Insight
The app has bugs in 3 layers: Python backend (app.py), JavaScript frontend (app.js), and bash deploy script. Run `python3 test_app.py 2>&1` to see which tests fail.
