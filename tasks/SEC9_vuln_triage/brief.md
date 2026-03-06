# SEC9: Vulnerability Triage (Brief)

A security audit found 15 findings in a Flask app. Triage them:
- 5 are REAL vulnerabilities — fix them (SQL injection, path traversal, SSRF, insecure deserialization, hardcoded secret)
- 5 are MITIGATED by existing middleware — do NOT modify
- 5 are FALSE POSITIVES — do NOT modify

See `security_audit.json` for finding details. Check `middleware/` for existing controls.
Fix only the real vulnerabilities. Preserve all existing security middleware.
