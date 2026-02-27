# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `find /workspace -name "*.py" -o -name "*.md" -o -name "*.txt" | head -20`
- `python -m py_compile` on Python files
- `grep -rn "source\|citation\|reference\|claim" /workspace 2>&1 | head -20`

## Expected Findings
Information retrieval QA tasks may have:
- Missing source citations
- Contradictory claims across documents
- Temporal inconsistencies in the evidence chain

## False Positives to Ignore
Not all inconsistencies are task-relevant — focus on what spec.md identifies as the key claims to verify.

## Key Insight
This is an evidence quality assessment task. Read the corpus documents first, then use grep patterns to trace specific claims across sources. The spec defines what constitutes a valid vs. invalid evidence chain.
