# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" | head -20`
- `ruff check /workspace --select=E,F,B 2>&1`
- `grep -rn "timeout\|retry\|circuit\|fallback\|except" /workspace 2>&1 | head -30`
- `python -m py_compile` on all Python files

## Expected Findings
Cascade failure tasks often reveal:
- Missing timeout configurations
- No circuit breaker implementation
- Exception swallowing that masks downstream failures
- Missing retry logic with backoff

## False Positives to Ignore
Intentional fire-and-forget patterns documented in the architecture spec.

## Key Insight
The spec describes a cascade failure scenario. Find the missing circuit breakers, timeouts, or retry logic that would have prevented the cascade. Each missing safeguard is a separate fix.
