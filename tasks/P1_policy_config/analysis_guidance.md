# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" -o -name "*.yaml" -o -name "*.json" -o -name "*.cfg" | head -20`
- `python -m py_compile` on all Python files
- `ruff check /workspace --select=E,F,B 2>&1`

## Expected Findings
Policy configuration tasks often have:
- Incorrect boolean values (True/False vs true/false in config files)
- Missing required fields in config
- Type mismatches (string where int expected)

## False Positives to Ignore
Default placeholder values in config templates are not bugs — only flag values that contradict the policy spec.

## Key Insight
Read the corpus policy documents carefully. The spec defines exact required values. Static analysis finds structural issues; policy compliance requires comparing config values against the spec.
