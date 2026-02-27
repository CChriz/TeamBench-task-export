# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" | head -20` — explore structure first
- `python -m py_compile /workspace/*.py 2>&1` — syntax validation on all Python files
- `ruff check /workspace --select=E,F,B 2>&1` — detect code-level bugs
- `grep -rn "schema\|dtype\|type\|convert\|cast\|null\|None" /workspace 2>&1 | head -30` — find type conversion issues
- `python pipeline.py 2>&1` — run the ETL to observe runtime failures

## Expected Findings
This is a schema-mapping and type-conversion ETL pipeline (JSON input). Tools will reveal:
- Type coercion errors: fields read as strings that need int/float conversion
- Schema mapping mismatches: input field names that don't match expected output field names
- Null/None handling: missing null checks before transformations
- JSON structure assumptions: wrong nesting level or missing keys that cause KeyError at runtime

## False Positives to Ignore
- Ruff style warnings (E501 line-length, W291 trailing whitespace) are not task bugs
- Type annotations that look wrong but are intentionally broad (e.g., `Any`) are not bugs

## Key Insight
Run the pipeline end-to-end first to observe which stage fails. The ETL has distinct extract, transform, and load steps — isolate which step produces incorrect output by comparing intermediate data against the schema contract in task.yaml. Focus on the 4 workspace files and the ~50 lines that need changing.
