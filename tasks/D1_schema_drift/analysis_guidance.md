# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" -o -name "*.sql" -o -name "*.json" | head -20`
- `ruff check /workspace --select=E,F,B 2>&1`
- `python -m py_compile` on all Python files
- `grep -n "schema\|column\|field\|ALTER\|CREATE" /workspace 2>&1 | head -30`

## Expected Findings
Schema drift tasks typically have:
- Migration scripts with wrong column types
- Missing NOT NULL constraints
- Schema version mismatches
- Data transformation bugs (wrong field mapping)

## False Positives to Ignore
Intentional schema evolution steps that are part of the migration plan.

## Key Insight
Run the migration scripts and check that the resulting schema matches the target schema in spec.md exactly (column names, types, constraints).
