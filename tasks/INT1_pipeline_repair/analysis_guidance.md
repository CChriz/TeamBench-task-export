# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `cd /workspace && python -m py_compile collector/collector.py processor/processor.py reporter/reporter.py pipeline.py 2>&1` — syntax check
- `find /workspace -name "*.py" | xargs grep -l "json\|csv" 2>&1` — find relevant files
- `ruff check /workspace --select=E,F,B 2>&1` — detect obvious bugs

## Expected Findings
ruff/ast analysis will reveal:
- JSON array format mismatch between collector output and processor input
- Field naming inconsistency (`name` vs `full_name`)
- Missing error logging for invalid records
- Sort order issue in reporter

## False Positives to Ignore
None — all findings are real pipeline bugs.

## Key Insight
Run `python pipeline.py 2>&1` to see actual runtime errors. The spec contracts are precise about field names, formats, and record counts.
