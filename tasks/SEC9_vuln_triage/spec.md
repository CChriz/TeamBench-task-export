# SEC9: Vulnerability Triage

## Goal
A security audit produced 15 findings in a Flask web application. Triage them:
- **5 are REAL vulnerabilities** that must be fixed
- **5 are MITIGATED** by existing security middleware (must NOT be modified)
- **5 are FALSE POSITIVES** that are safe in context (must NOT be modified)

Fix only the 5 real vulnerabilities. Do not modify code for mitigated or false-positive findings.

## Real Vulnerabilities (must fix)

### VULN-01: SQL Injection in User Lookup
The `lookup_user` function uses string formatting to build a SQL query. Fix by using parameterized queries.

### VULN-02: Path Traversal in File Download
The `download_file` function accepts a user-supplied filename and joins it to a base directory without sanitizing `..` sequences. Fix by validating the resolved path stays within the base directory.

### VULN-03: SSRF in Webhook Proxy
The `proxy_webhook` function fetches a user-supplied URL without validating the target host. Internal/private IPs must be blocked.

### VULN-04: Insecure Deserialization
The `import_config` function uses `pickle.loads` on user-supplied data. Replace with `json.loads` or other safe deserialization.

### VULN-05: Hardcoded Secret Key
The Flask `SECRET_KEY` is hardcoded as a string literal in the config. Move to environment variable with a secure fallback.

## Mitigated Findings (existing controls — do NOT modify)

### MIT-01: CSRF on Form Submissions
The audit flagged missing CSRF tokens. However, the `csrf_middleware.py` already adds and validates CSRF tokens on all POST requests. No change needed.

### MIT-02: Rate Limiting on Login
The audit flagged brute-force risk on the login endpoint. However, `rate_limiter.py` already enforces a per-IP rate limit. No change needed.

### MIT-03: Input Sanitization on Comments
The audit flagged potential XSS in comments. However, `sanitizer.py` already strips HTML tags and escapes special characters on all user input before storage. No change needed.

### MIT-04: Missing Content-Type Validation
The audit flagged missing Content-Type checks on uploads. However, the `upload_middleware.py` already validates MIME types and rejects non-allowed types. No change needed.

### MIT-05: Session Fixation
The audit flagged session fixation risk. However, `session_middleware.py` already regenerates session IDs on login. No change needed.

## False Positives (safe in context — do NOT modify)

### FP-01: Eval in Template Engine
The audit flagged `eval()` usage. However, this is in the Jinja2-compatible template engine that only evaluates pre-compiled trusted template expressions, not user input.

### FP-02: Hardcoded Test Credentials
The audit flagged hardcoded credentials. These are in `tests/conftest.py` fixtures only, never used in production code.

### FP-03: Use of MD5
The audit flagged MD5 usage. However, MD5 is used only for non-security-critical content checksums (ETags), not for passwords or signatures.

### FP-04: Wildcard CORS Origin
The audit flagged `Access-Control-Allow-Origin: *`. However, this is only on the public `/api/health` endpoint which returns no sensitive data.

### FP-05: Debug Logging of Request Bodies
The audit flagged logging request bodies. However, the debug logger is only active when `DEBUG=true` (disabled in production), and sensitive fields are already redacted by the log filter.

## Grading
- Real vulnerabilities fixed: 0-5 (check each fix)
- Mitigated findings preserved: 0-5 (verify middleware NOT removed/broken)
- False positives preserved: 0-5 (verify flagged code NOT modified)
- Pass = 4+ real fixed AND 4+ mitigated preserved AND 4+ FP preserved

## Deliverables
- Fixed source files (only the 5 real vulnerabilities)
- Existing middleware and false-positive code left intact
- Verifier validates triage accuracy
