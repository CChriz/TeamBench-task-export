"""
Parameterized generator for SEC9: Vulnerability Triage.

Each seed produces:
- A Flask app with 15 security findings in security_audit.json
- 5 real vulnerabilities in app code
- 5 mitigated findings with existing middleware
- 5 false positives that are safe in context
- Different app names, vulnerability types shuffle, finding IDs per seed
"""
from __future__ import annotations

import json
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-variant pools ───────────────────────────────────────────────────────

APP_CONFIGS = [
    {
        "app_name": "webapp",
        "module_name": "inventory_app",
        "user_table": "users",
        "lookup_field": "username",
        "upload_dir": "/var/data/files",
        "secret_key_value": "super-secret-key-12345",
    },
    {
        "app_name": "portalapi",
        "module_name": "portal_api",
        "user_table": "accounts",
        "lookup_field": "email",
        "upload_dir": "/srv/uploads",
        "secret_key_value": "my-insecure-flask-key-abc",
    },
    {
        "app_name": "dataservice",
        "module_name": "data_service",
        "user_table": "members",
        "lookup_field": "login_id",
        "upload_dir": "/opt/storage/docs",
        "secret_key_value": "hardcoded-dev-secret-999",
    },
]

# Finding ID prefixes per seed
FINDING_PREFIXES = ["SA", "AUDIT", "SCAN"]


class Generator(TaskGenerator):
    task_id = "SEC9_vuln_triage"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(APP_CONFIGS)

        config = APP_CONFIGS[idx]
        prefix = FINDING_PREFIXES[idx]

        workspace_files = self._make_workspace(config, prefix, rng)

        expected = {
            "seed": seed,
            "app_name": config["app_name"],
            "finding_prefix": prefix,
            "real_vulns": [f"{prefix}-{i:03d}" for i in range(1, 6)],
            "mitigated": [f"{prefix}-{i:03d}" for i in range(6, 11)],
            "false_positives": [f"{prefix}-{i:03d}" for i in range(11, 16)],
            "required_fixes": 4,
            "required_preserved_mitigated": 4,
            "required_preserved_fp": 4,
        }

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "SEC9_vuln_triage"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(self, config: dict, prefix: str, rng: SeededRandom) -> dict:
        files = {}

        app_name = config["app_name"]
        mod = config["module_name"]
        user_table = config["user_table"]
        lookup_field = config["lookup_field"]
        upload_dir = config["upload_dir"]
        secret_key = config["secret_key_value"]

        # ── security_audit.json ──────────────────────────────────────────────
        findings = []
        # Real vulns (1-5)
        findings.append({
            "id": f"{prefix}-001", "severity": "critical",
            "title": "SQL Injection in User Lookup",
            "description": f"The lookup_user function in app/routes.py uses string formatting to build SQL query for {user_table} table.",
            "file": "app/routes.py", "line": 15, "category": "REAL",
        })
        findings.append({
            "id": f"{prefix}-002", "severity": "high",
            "title": "Path Traversal in File Download",
            "description": f"The download_file function in app/routes.py joins user input to {upload_dir} without sanitizing .. sequences.",
            "file": "app/routes.py", "line": 30, "category": "REAL",
        })
        findings.append({
            "id": f"{prefix}-003", "severity": "high",
            "title": "Server-Side Request Forgery in Webhook Proxy",
            "description": "The proxy_webhook function fetches a user-supplied URL without validating the target host.",
            "file": "app/routes.py", "line": 45, "category": "REAL",
        })
        findings.append({
            "id": f"{prefix}-004", "severity": "critical",
            "title": "Insecure Deserialization",
            "description": "The import_config function uses pickle.loads on user-supplied data.",
            "file": "app/routes.py", "line": 60, "category": "REAL",
        })
        findings.append({
            "id": f"{prefix}-005", "severity": "medium",
            "title": "Hardcoded Secret Key",
            "description": f"Flask SECRET_KEY is hardcoded as '{secret_key}' in app/config.py.",
            "file": "app/config.py", "line": 5, "category": "REAL",
        })
        # Mitigated (6-10)
        findings.append({
            "id": f"{prefix}-006", "severity": "medium",
            "title": "Missing CSRF Protection on Forms",
            "description": "POST endpoints lack CSRF token validation.",
            "file": "app/routes.py", "line": 80, "category": "MITIGATED",
            "mitigation": "csrf_middleware.py handles CSRF validation globally",
        })
        findings.append({
            "id": f"{prefix}-007", "severity": "medium",
            "title": "Brute-Force Risk on Login",
            "description": "Login endpoint has no rate limiting.",
            "file": "app/routes.py", "line": 90, "category": "MITIGATED",
            "mitigation": "rate_limiter.py enforces per-IP rate limits",
        })
        findings.append({
            "id": f"{prefix}-008", "severity": "medium",
            "title": "XSS in User Comments",
            "description": "User comments displayed without sanitization.",
            "file": "app/routes.py", "line": 100, "category": "MITIGATED",
            "mitigation": "sanitizer.py strips HTML and escapes on all input",
        })
        findings.append({
            "id": f"{prefix}-009", "severity": "low",
            "title": "Missing Content-Type Validation on Uploads",
            "description": "File upload accepts any content type.",
            "file": "app/routes.py", "line": 110, "category": "MITIGATED",
            "mitigation": "upload_middleware.py validates MIME types",
        })
        findings.append({
            "id": f"{prefix}-010", "severity": "medium",
            "title": "Session Fixation Risk",
            "description": "Session ID not regenerated after login.",
            "file": "app/routes.py", "line": 120, "category": "MITIGATED",
            "mitigation": "session_middleware.py regenerates session on auth",
        })
        # False positives (11-15)
        findings.append({
            "id": f"{prefix}-011", "severity": "high",
            "title": "Use of eval() Function",
            "description": "eval() call found in template engine.",
            "file": "app/template_engine.py", "line": 25, "category": "FALSE_POSITIVE",
            "reason": "Only evaluates pre-compiled trusted template expressions",
        })
        findings.append({
            "id": f"{prefix}-012", "severity": "medium",
            "title": "Hardcoded Test Credentials",
            "description": "Password literals found in test fixtures.",
            "file": "tests/conftest.py", "line": 10, "category": "FALSE_POSITIVE",
            "reason": "Test fixtures only, never used in production",
        })
        findings.append({
            "id": f"{prefix}-013", "severity": "low",
            "title": "Use of MD5 Hash Algorithm",
            "description": "MD5 hash usage detected.",
            "file": "app/utils.py", "line": 15, "category": "FALSE_POSITIVE",
            "reason": "Used for content checksums (ETags), not cryptographic purposes",
        })
        findings.append({
            "id": f"{prefix}-014", "severity": "low",
            "title": "Wildcard CORS Origin",
            "description": "Access-Control-Allow-Origin: * header set.",
            "file": "app/routes.py", "line": 5, "category": "FALSE_POSITIVE",
            "reason": "Only on /api/health endpoint which returns no sensitive data",
        })
        findings.append({
            "id": f"{prefix}-015", "severity": "low",
            "title": "Debug Logging of Request Bodies",
            "description": "Request bodies logged at DEBUG level.",
            "file": "app/logging_config.py", "line": 20, "category": "FALSE_POSITIVE",
            "reason": "Debug logger disabled in production; sensitive fields redacted",
        })

        files["security_audit.json"] = json.dumps(findings, indent=2)

        # ── app/__init__.py ──────────────────────────────────────────────────
        files["app/__init__.py"] = f'''"""
{mod} — Flask application.
"""
from flask import Flask


def create_app():
    from app.config import Config
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.routes import bp
    app.register_blueprint(bp)

    # Register middleware
    from middleware.csrf_middleware import init_csrf
    from middleware.rate_limiter import init_rate_limiter
    from middleware.sanitizer import init_sanitizer
    from middleware.upload_middleware import init_upload_validation
    from middleware.session_middleware import init_session_management

    init_csrf(app)
    init_rate_limiter(app)
    init_sanitizer(app)
    init_upload_validation(app)
    init_session_management(app)

    return app
'''

        # ── app/config.py (VULN-05: hardcoded secret) ────────────────────────
        files["app/config.py"] = f'''"""Application configuration."""
import os


class Config:
    # VULNERABLE: hardcoded secret key
    SECRET_KEY = "{secret_key}"
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///app.db")
    UPLOAD_DIR = "{upload_dir}"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
'''

        # ── app/routes.py (VULN-01 to VULN-04 + FP-04 CORS) ─────────────────
        files["app/routes.py"] = f'''"""
Route handlers for {mod}.
"""
import os
import pickle
import sqlite3
import urllib.request
from flask import Blueprint, request, jsonify, send_file

bp = Blueprint("api", __name__)

# FP-04: Wildcard CORS only on health endpoint (safe — no sensitive data)
@bp.after_request
def add_cors_headers(response):
    if request.path == "/api/health":
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@bp.route("/api/health")
def health():
    return jsonify({{"status": "ok"}})


# ── VULN-01: SQL Injection in lookup_user ────────────────────────────────

@bp.route("/api/users/lookup")
def lookup_user():
    """Look up a user by {lookup_field}. VULNERABLE: SQL injection."""
    value = request.args.get("{lookup_field}", "")
    conn = sqlite3.connect("app.db")
    # VULNERABLE: string formatting in SQL query
    query = f"SELECT * FROM {user_table} WHERE {lookup_field} = '{{value}}'"
    cursor = conn.execute(query)
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({{"user": list(user)}})
    return jsonify({{"error": "not found"}}), 404


# ── VULN-02: Path Traversal in download_file ─────────────────────────────

@bp.route("/api/files/download")
def download_file():
    """Download a file. VULNERABLE: path traversal."""
    filename = request.args.get("name", "")
    # VULNERABLE: no sanitization of .. sequences
    filepath = os.path.join("{upload_dir}", filename)
    if not os.path.exists(filepath):
        return jsonify({{"error": "file not found"}}), 404
    return send_file(filepath)


# ── VULN-03: SSRF in proxy_webhook ───────────────────────────────────────

@bp.route("/api/webhook/proxy", methods=["POST"])
def proxy_webhook():
    """Proxy a webhook to a target URL. VULNERABLE: SSRF."""
    data = request.get_json(silent=True) or {{}}
    target_url = data.get("url", "")
    if not target_url:
        return jsonify({{"error": "url required"}}), 400
    # VULNERABLE: fetches any URL including internal/private IPs
    try:
        resp = urllib.request.urlopen(target_url, timeout=5)
        body = resp.read().decode("utf-8", errors="replace")
        return jsonify({{"status": resp.status, "body": body[:1000]}})
    except Exception as e:
        return jsonify({{"error": str(e)}}), 502


# ── VULN-04: Insecure Deserialization ────────────────────────────────────

@bp.route("/api/config/import", methods=["POST"])
def import_config():
    """Import configuration. VULNERABLE: pickle deserialization."""
    raw = request.get_data()
    if not raw:
        return jsonify({{"error": "no data"}}), 400
    # VULNERABLE: uses pickle on untrusted input
    try:
        config = pickle.loads(raw)
        return jsonify({{"status": "imported", "keys": list(config.keys())}})
    except Exception as e:
        return jsonify({{"error": str(e)}}), 400


# ── Other endpoints (login, comments, upload, admin — mitigated) ─────────

@bp.route("/api/login", methods=["POST"])
def login():
    """Login endpoint. Rate limiting handled by middleware."""
    data = request.get_json(silent=True) or {{}}
    return jsonify({{"status": "ok", "token": "dummy-token"}})


@bp.route("/api/comments", methods=["POST"])
def post_comment():
    """Post a comment. Sanitization handled by middleware."""
    data = request.get_json(silent=True) or {{}}
    return jsonify({{"status": "ok", "comment_id": 1}})


@bp.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload a file. MIME validation handled by middleware."""
    return jsonify({{"status": "ok"}})


@bp.route("/api/admin/action", methods=["POST"])
def admin_action():
    """Admin action. Session management handled by middleware."""
    return jsonify({{"status": "ok"}})
'''

        # ── app/template_engine.py (FP-01: eval is safe here) ────────────────
        files["app/template_engine.py"] = f'''"""
Simple template engine for {mod}.
Uses eval() ONLY on pre-compiled trusted template expressions.
This is NOT user input — templates are loaded from trusted filesystem paths.
"""


class TemplateEngine:
    """Minimal template engine that evaluates compiled expressions."""

    def __init__(self):
        self._compiled_cache = {{}}

    def compile_template(self, template_path: str) -> str:
        """Compile a template file into an expression string."""
        with open(template_path) as f:
            raw = f.read()
        # Only compile simple {{{{ var }}}} patterns into f-string-like expressions
        compiled = raw.replace("{{{{", "{{").replace("}}}}", "}}")
        self._compiled_cache[template_path] = compiled
        return compiled

    def render(self, template_path: str, context: dict) -> str:
        """Render a compiled template with the given context."""
        if template_path not in self._compiled_cache:
            self.compile_template(template_path)
        expr = self._compiled_cache[template_path]
        # eval() is safe here: only evaluates trusted compiled template expressions
        # Template files are loaded from disk, not from user input
        result = eval(f\'f"""{{expr}}"""\', {{"__builtins__": {{}}}}, context)
        return result
'''

        # ── app/utils.py (FP-03: MD5 for checksums) ─────────────────────────
        files["app/utils.py"] = f'''"""
Utility functions for {mod}.
"""
import hashlib


def compute_etag(content: bytes) -> str:
    """
    Compute an ETag for HTTP caching.
    Uses MD5 for content checksums only — NOT for security purposes.
    MD5 is appropriate here because:
    - ETags are not security-critical
    - MD5 is fast and widely supported for content fingerprinting
    - Collision resistance is not required for cache invalidation
    """
    return hashlib.md5(content).hexdigest()


def generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())
'''

        # ── app/logging_config.py (FP-05: debug logging) ────────────────────
        files["app/logging_config.py"] = f'''"""
Logging configuration for {mod}.
Debug logging of request bodies is SAFE because:
- DEBUG level is disabled in production (LOG_LEVEL=INFO)
- Sensitive fields (password, token, secret) are redacted by the filter
"""
import logging
import os


SENSITIVE_FIELDS = ["password", "token", "secret", "api_key", "authorization"]


class SensitiveFilter(logging.Filter):
    """Redact sensitive fields from log records."""

    def filter(self, record):
        msg = str(record.msg)
        for field in SENSITIVE_FIELDS:
            if field in msg.lower():
                record.msg = msg.replace(field, "[REDACTED]")
        return True


def setup_logging():
    """Configure application logging."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger("{mod}")
    logger.setLevel(getattr(logging, level, logging.INFO))

    handler = logging.StreamHandler()
    handler.addFilter(SensitiveFilter())
    logger.addHandler(handler)

    # Debug-level request body logging (disabled in production)
    debug_logger = logging.getLogger("{mod}.debug")
    debug_logger.setLevel(logging.DEBUG)
    return logger
'''

        # ── middleware/csrf_middleware.py (MIT-01) ────────────────────────────
        files["middleware/__init__.py"] = ""

        files["middleware/csrf_middleware.py"] = f'''"""
CSRF protection middleware for {mod}.
Validates CSRF tokens on all POST/PUT/DELETE requests.
"""
import hashlib
import hmac
import os
from functools import wraps


_CSRF_SECRET = os.urandom(32)


def generate_csrf_token(session_id: str) -> str:
    """Generate a CSRF token tied to the session."""
    return hmac.new(_CSRF_SECRET, session_id.encode(), hashlib.sha256).hexdigest()


def validate_csrf_token(session_id: str, token: str) -> bool:
    """Validate that the CSRF token matches the session."""
    expected = generate_csrf_token(session_id)
    return hmac.compare_digest(expected, token)


def init_csrf(app):
    """Register CSRF validation as a before_request hook."""
    @app.before_request
    def csrf_check():
        from flask import request, abort
        if request.method in ("POST", "PUT", "DELETE"):
            token = request.headers.get("X-CSRF-Token", "")
            session_id = request.cookies.get("session_id", "anonymous")
            # In test mode, skip CSRF check
            if app.config.get("TESTING"):
                return
            if not validate_csrf_token(session_id, token):
                abort(403)
'''

        # ── middleware/rate_limiter.py (MIT-02) ──────────────────────────────
        files["middleware/rate_limiter.py"] = f'''"""
Rate limiting middleware for {mod}.
Enforces per-IP rate limits on authentication endpoints.
"""
import time
from collections import defaultdict


_RATE_STORE = defaultdict(list)
_MAX_REQUESTS = 5
_WINDOW_SECONDS = 60


def is_rate_limited(ip: str) -> bool:
    """Check if an IP has exceeded the rate limit."""
    now = time.time()
    # Clean old entries
    _RATE_STORE[ip] = [t for t in _RATE_STORE[ip] if now - t < _WINDOW_SECONDS]
    if len(_RATE_STORE[ip]) >= _MAX_REQUESTS:
        return True
    _RATE_STORE[ip].append(now)
    return False


def init_rate_limiter(app):
    """Register rate limiting as a before_request hook."""
    @app.before_request
    def rate_limit_check():
        from flask import request, abort
        rate_limited_paths = ["/api/login", "/api/auth", "/api/token"]
        if request.path in rate_limited_paths:
            ip = request.remote_addr or "unknown"
            if is_rate_limited(ip):
                abort(429)
'''

        # ── middleware/sanitizer.py (MIT-03) ──────────────────────────────────
        files["middleware/sanitizer.py"] = f'''"""
Input sanitization middleware for {mod}.
Strips HTML tags and escapes special characters on all user text input.
"""
import html
import re


def sanitize_string(value: str) -> str:
    """Strip HTML tags and escape special characters."""
    # Remove all HTML tags
    stripped = re.sub(r"<[^>]+>", "", value)
    # Escape remaining special characters
    return html.escape(stripped)


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize all string values in a dict."""
    result = {{}}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_string(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        else:
            result[key] = value
    return result


def init_sanitizer(app):
    """Register input sanitization as a before_request hook."""
    @app.before_request
    def sanitize_input():
        from flask import request
        if request.is_json and request.method in ("POST", "PUT"):
            data = request.get_json(silent=True)
            if isinstance(data, dict):
                # Store sanitized data for route handlers
                request._sanitized_data = sanitize_dict(data)
'''

        # ── middleware/upload_middleware.py (MIT-04) ──────────────────────────
        files["middleware/upload_middleware.py"] = f'''"""
Upload validation middleware for {mod}.
Validates MIME types and rejects non-allowed file types on upload.
"""

ALLOWED_MIME_TYPES = [
    "image/jpeg", "image/png", "image/gif",
    "application/pdf", "text/plain", "text/csv",
]


def is_allowed_content_type(content_type: str) -> bool:
    """Check if the content type is in the allow list."""
    return content_type in ALLOWED_MIME_TYPES


def init_upload_validation(app):
    """Register upload validation as a before_request hook."""
    @app.before_request
    def validate_upload():
        from flask import request, abort
        if request.path == "/api/upload" and request.method == "POST":
            ct = request.content_type or ""
            # Allow multipart form data
            if ct.startswith("multipart/form-data"):
                return
            if not is_allowed_content_type(ct):
                abort(415)
'''

        # ── middleware/session_middleware.py (MIT-05) ─────────────────────────
        files["middleware/session_middleware.py"] = f'''"""
Session management middleware for {mod}.
Regenerates session IDs on login to prevent session fixation.
"""
import os
import hashlib


def generate_session_id() -> str:
    """Generate a cryptographically random session ID."""
    return hashlib.sha256(os.urandom(32)).hexdigest()


def regenerate_session(response, old_session_id: str):
    """Regenerate session ID and set new cookie."""
    new_id = generate_session_id()
    response.set_cookie("session_id", new_id, httponly=True, secure=True, samesite="Lax")
    return new_id


def init_session_management(app):
    """Register session regeneration after successful login."""
    @app.after_request
    def session_regen(response):
        from flask import request
        if request.path == "/api/login" and response.status_code == 200:
            old_id = request.cookies.get("session_id", "")
            regenerate_session(response, old_id)
        return response
'''

        # ── tests/__init__.py ────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/conftest.py (FP-02: test credentials) ─────────────────────
        files["tests/conftest.py"] = f'''"""
Test fixtures for {mod}.
These credentials are for testing only — never used in production.
"""
import pytest


@pytest.fixture
def test_admin():
    """Admin user fixture for testing."""
    return {{
        "username": "test_admin",
        "password": "admin_test_password_123",
        "role": "admin",
    }}


@pytest.fixture
def test_user():
    """Regular user fixture for testing."""
    return {{
        "username": "test_user",
        "password": "user_test_password_456",
        "role": "user",
    }}


@pytest.fixture
def api_token():
    """API token fixture for testing."""
    return "test-bearer-token-xyz-789"
'''

        files["requirements.txt"] = "flask\npytest\n"

        return files
