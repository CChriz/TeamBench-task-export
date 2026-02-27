# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" | head -20` — explore codebase
- `ruff check /workspace --select=E,F,B 2>&1` — code quality issues
- `grep -rn "exception\|error\|raise\|except" /workspace 2>&1 | head -30` — error handling patterns

## Expected Findings
Static analysis of error handling code may reveal:
- Bare except clauses that swallow exceptions
- Missing error propagation
- Unhandled edge cases in the incident response code

## False Positives to Ignore
Broad exception handlers in logging infrastructure are intentional — don't flag those.

## Key Insight
This is an incident root-cause analysis task. The spec contains the incident timeline and symptoms. Use static analysis to locate relevant code sections, then trace the causal chain.
