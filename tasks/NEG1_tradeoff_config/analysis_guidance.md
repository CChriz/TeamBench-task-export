# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" -o -name "*.yaml" -o -name "*.json" | head -20`
- `python -m py_compile` on Python files
- `ruff check /workspace --select=E,F,B 2>&1`
- `cat /workspace/config.* 2>/dev/null || find /workspace -name "config*"` — find config files

## Expected Findings
Negotiation/tradeoff config tasks often surface:
- Config values that are technically valid but violate the specified tradeoff constraints
- Missing parameters with required default values
- Threshold values outside the negotiated acceptable ranges

## False Positives to Ignore
Config values that are within spec — not every non-default value is wrong.

## Key Insight
This task involves configuring a system to satisfy multiple competing constraints. Read the spec's constraint table carefully. Static analysis finds structural issues; the core challenge is finding the config values that satisfy ALL constraints simultaneously.
