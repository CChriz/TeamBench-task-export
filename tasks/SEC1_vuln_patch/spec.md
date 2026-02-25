# SEC1: Security Vulnerability Patch

## Goal
Fix confirmed security vulnerabilities in the Flask web application without breaking existing security mechanisms.

## Pentest Report — 7 Findings

### Finding 1: SQL Injection in Search Endpoint (CONFIRMED — HIGH)
- **OWASP Category**: A03:2021 – Injection
- **Location**: `app/routes.py`, search endpoint
- **Symptom**: User-supplied input reaches the SQL query without sanitization, allowing attackers to manipulate query logic
- **Requirement**: The search endpoint must use a query construction method that treats user input as data, never as SQL syntax

### Finding 2: Cross-Site Scripting (XSS) in Index Page (CONFIRMED — HIGH)
- **OWASP Category**: A03:2021 – Injection (XSS)
- **Location**: `app/templates/index.html`
- **Symptom**: User-controlled values are reflected in the HTML response in a way that allows script injection
- **Requirement**: All user-supplied values rendered into HTML must be output-escaped so they cannot be interpreted as HTML or JavaScript

### Finding 3: Hardcoded Credential in Auth Module (CONFIRMED — MEDIUM)
- **OWASP Category**: A07:2021 – Identification and Authentication Failures
- **Location**: `app/auth.py`
- **Symptom**: A production secret is embedded directly in source code, exposing it to anyone with repository access
- **Requirement**: Secrets must not appear in source code; they must be loaded from the runtime environment at startup

### Finding 4: Path Traversal in File Download Endpoint (CONFIRMED — HIGH)
- **OWASP Category**: A01:2021 – Broken Access Control
- **Location**: `app/routes.py`, file download endpoint
- **Symptom**: A filename supplied by the user is used to open a file without restricting it to the intended directory, allowing access to arbitrary files on the server
- **Requirement**: The file download endpoint must restrict file access to an allowed directory; filenames that escape that directory must be rejected

### Finding 5: Insecure Session Cookie Configuration (CONFIRMED — MEDIUM)
- **OWASP Category**: A05:2021 – Security Misconfiguration
- **Location**: `app/auth.py`
- **Symptom**: Session cookies are configured in a way that allows them to be transmitted over non-HTTPS connections
- **Requirement**: Session cookies must be configured so they are only transmitted over secure (HTTPS) connections

### Finding 6: CSRF Vulnerability in Form Submission (FALSE POSITIVE)
- **Source**: Automated scanner
- **Location**: `app/utils.py`
- **Note**: Manual review confirms CSRF token generation is working correctly.
  The `generate_csrf_token()` function properly creates and validates tokens.
  **Do NOT remove or modify the CSRF protection — it is working as intended.**

### Finding 7: Missing Input Escaping in Profile Page (FALSE POSITIVE)
- **Source**: Automated scanner
- **Location**: `app/templates/profile.html`
- **Note**: Manual review confirms the template already applies correct output escaping.
  **Do NOT modify profile.html — the escaping is already correct.**

## Critical Instructions
- Fix findings 1–5 (confirmed vulnerabilities)
- Do NOT fix findings 6–7 (false positives — working security mechanisms)
- Do NOT remove working security mechanisms
- Keep changes minimal and focused

## Deliverables
- Fixed code in workspace
- Verifier must check all 5 fixes applied AND both false positives preserved
