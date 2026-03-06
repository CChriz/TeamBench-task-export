# CR6: Code Review with False Positive Triage

## Goal
Review the PR diff in `pull_request.diff` and produce `review_report.json` that
correctly classifies all 12 potential issues: 8 real issues and 4 false positives.

## Review Guidelines
See `REVIEW_GUIDELINES.md` for severity definitions and false positive rules.

## Issue Breakdown
The PR contains 12 potential issues:
- **2 Critical**: Security vulnerabilities (SQL injection, missing auth, or command injection)
- **3 Major**: Reliability issues (resource leaks, race conditions, unhandled exceptions)
- **3 Minor**: Style/documentation issues (naming, unused imports, missing docstrings)
- **4 False Positives**: Patterns that look bad but are correct per REVIEW_GUIDELINES.md

## Output Format
Write `review_report.json` conforming to `expected_report_schema.json`.

## Grading Criteria
- All 8 real issues identified with correct severity
- All 4 false positives correctly dismissed
- No extra false findings (precision matters)
- Severity levels match the guidelines
- Verdict is appropriate given the findings (should be reject or request_changes)

## Deliverables
1. `review_report.json` with all 12 findings classified
2. Verifier writes `attestation.json`
