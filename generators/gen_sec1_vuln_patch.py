"""
Parameterized generator for SEC1: Security Vulnerability Patch.

Each seed produces:
- A different app domain (user profiles, blog posts, product catalog, order management, support tickets)
- Different route names and URL patterns
- Same 5 confirmed OWASP vulnerability categories + 2 false positives, but in different locations
- Different template file names
- Different hardcoded secret patterns
- Different SQL table/field names

The grade.sh checks the same structural patterns regardless of domain, so the workspace
code must always satisfy the same static analysis checks.
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# App domains with their specific resource names, route names, table/column names
DOMAINS = [
    {
        "name": "user_profiles",
        "resource": "users",
        "table": "users",
        "search_field": "name",
        "search_param": "name",
        "search_route": "/search",
        "download_route": "/download/<filename>",
        "index_var": "user_input",
        "profile_var": "username",
        "item_label": "user",
    },
    {
        "name": "blog_posts",
        "resource": "posts",
        "table": "posts",
        "search_field": "title",
        "search_param": "title",
        "search_route": "/search",
        "download_route": "/attachment/<filename>",
        "index_var": "search_query",
        "profile_var": "author",
        "item_label": "post",
    },
    {
        "name": "product_catalog",
        "resource": "products",
        "table": "products",
        "search_field": "name",
        "search_param": "q",
        "search_route": "/search",
        "download_route": "/asset/<filename>",
        "index_var": "query",
        "profile_var": "product_name",
        "item_label": "product",
    },
    {
        "name": "order_management",
        "resource": "orders",
        "table": "orders",
        "search_field": "customer",
        "search_param": "customer",
        "search_route": "/search",
        "download_route": "/invoice/<filename>",
        "index_var": "filter_text",
        "profile_var": "order_id",
        "item_label": "order",
    },
    {
        "name": "support_tickets",
        "resource": "tickets",
        "table": "tickets",
        "search_field": "subject",
        "search_param": "subject",
        "search_route": "/search",
        "download_route": "/export/<filename>",
        "index_var": "search_term",
        "profile_var": "ticket_id",
        "item_label": "ticket",
    },
]

# Hardcoded secret patterns (API key prefix + content + suffix)
SECRET_PATTERNS = [
    ("sk-prod-", "abc123def456ghi789jkl012mno345", "SECRET_KEY"),
    ("api-live-", "xyz789pqr456stu123vwx012yza678", "API_KEY"),
    ("tok-prod-", "mno345def456ghi789jkl012abc123", "ACCESS_TOKEN"),
    ("key-live-", "pqr789abc456def123ghi789jkl012", "PRIVATE_KEY"),
    ("sec-prod-", "uvw567xyz890abc123def456ghi789", "SERVICE_KEY"),
]


class Generator(TaskGenerator):
    task_id = "SEC1_vuln_patch"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick domain
        domain = DOMAINS[rng.randint(0, len(DOMAINS) - 1)]

        # Pick secret pattern
        secret_idx = rng.randint(0, len(SECRET_PATTERNS) - 1)
        secret_prefix, secret_value, secret_env_name = SECRET_PATTERNS[secret_idx]
        full_secret = secret_prefix + secret_value

        expected = {
            "domain": domain["name"],
            "confirmed_vulns": [
                "sql_injection",
                "xss",
                "hardcoded_secret",
                "path_traversal",
                "insecure_session",
            ],
            "false_positives": ["csrf_token_generation", "profile_template_escaping"],
            "secret_pattern": secret_prefix,
            "secret_env_name": secret_env_name,
            "table": domain["table"],
            "search_param": domain["search_param"],
            "index_var": domain["index_var"],
        }

        # Generate workspace files
        routes_py = self._generate_routes(domain, full_secret)
        auth_py = self._generate_auth(full_secret, secret_env_name)
        utils_py = self._generate_utils()
        models_py = self._generate_models(domain)
        config_py = self._generate_config(domain)
        index_html = self._generate_index_html(domain)
        profile_html = self._generate_profile_html(domain)
        init_py = self._generate_init()

        workspace_files = {
            "app/__init__.py": init_py,
            "app/routes.py": routes_py,
            "app/auth.py": auth_py,
            "app/utils.py": utils_py,
            "app/models.py": models_py,
            "app/config.py": config_py,
            "app/templates/index.html": index_html,
            "app/templates/profile.html": profile_html,
        }

        spec_md = self._generate_spec(domain, full_secret, secret_prefix)
        brief_md = self._generate_brief(domain)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_routes(self, domain: dict, full_secret: str) -> str:
        resource = domain["resource"]
        table = domain["table"]
        search_param = domain["search_param"]
        search_field = domain["search_field"]
        index_var = domain["index_var"]
        profile_var = domain["profile_var"]
        download_route = domain["download_route"]
        # Extract filename param from route pattern like "/download/<filename>"
        dl_path = download_route.replace("<filename>", "{filename}")
        dl_path_flask = download_route

        # Determine download function name from route
        if "attachment" in download_route:
            dl_func = "attachment"
        elif "asset" in download_route:
            dl_func = "asset"
        elif "invoice" in download_route:
            dl_func = "invoice"
        elif "export" in download_route:
            dl_func = "export_file"
        else:
            dl_func = "download"

        return f'''"""Application routes."""
import os
import sqlite3
from flask import Blueprint, request, jsonify, send_file, render_template

bp = Blueprint("main", __name__)

DATABASE = "app.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@bp.route("/")
def index():
    {index_var} = request.args.get("q", "")
    return render_template("index.html", {index_var}={index_var})


@bp.route("/profile")
def profile():
    username = request.args.get("name", "Guest")
    return render_template("profile.html", username=username)


@bp.route("/search")
def search():
    {search_param} = request.args.get("{search_param}", "")
    db = get_db()
    # Build query to find {resource} by {search_field}
    query = f"SELECT * FROM {table} WHERE {search_field}=\'{{{search_param}}}\'"
    try:
        results = db.execute(query).fetchall()
        return jsonify([dict(r) for r in results])
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500
    finally:
        db.close()


@bp.route("{dl_path_flask}")
def {dl_func}(filename):
    """Serve a file from the uploads directory."""
    filepath = os.path.join("uploads", filename)
    try:
        return send_file(filepath)
    except FileNotFoundError:
        return jsonify({{"error": "not found"}}), 404
'''

    def _generate_auth(self, full_secret: str, secret_env_name: str) -> str:
        return f'''"""Authentication and session configuration."""

{secret_env_name} = "{full_secret}"


def init_auth(app):
    """Initialize authentication settings."""
    app.secret_key = "change-me-in-production"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def verify_api_key(provided_key):
    """Verify the provided API key."""
    return provided_key == {secret_env_name}
'''

    def _generate_utils(self) -> str:
        return '''"""Utility functions including CSRF protection."""
import hashlib
import secrets
import time


def generate_csrf_token():
    """Generate a secure CSRF token."""
    raw = f"{secrets.token_hex(32)}{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_csrf_token(token, stored_token):
    """Validate CSRF token matches stored value."""
    if not token or not stored_token:
        return False
    return secrets.compare_digest(token, stored_token)
'''

    def _generate_models(self, domain: dict) -> str:
        resource = domain["resource"]
        item_label = domain["item_label"]
        resource_class = item_label.capitalize()
        return f'''"""Data models — clean, no vulnerabilities."""


class {resource_class}:
    def __init__(self, id, name, status):
        self.id = id
        self.name = name
        self.status = status

    def to_dict(self):
        return {{"id": self.id, "name": self.name, "status": self.status}}


class Session:
    def __init__(self, user_id, token):
        self.user_id = user_id
        self.token = token
'''

    def _generate_config(self, domain: dict) -> str:
        return f'''"""Application configuration."""

DOMAIN = "{domain["name"]}"
DATABASE = "app.db"
UPLOAD_DIR = "uploads"
DEBUG = False
'''

    def _generate_index_html(self, domain: dict) -> str:
        index_var = domain["index_var"]
        resource = domain["resource"]
        search_param = domain["search_param"]
        return f'''<!DOCTYPE html>
<html>
<head><title>Search {resource.capitalize()}</title></head>
<body>
  <h1>Search Results</h1>
  <p>You searched for: {{{{ {index_var} }}}}</p>
  <form action="/search" method="get">
    <input type="text" name="{search_param}" placeholder="Search {resource}...">
    <button type="submit">Search</button>
  </form>
</body>
</html>
'''

    def _generate_profile_html(self, domain: dict) -> str:
        item_label = domain["item_label"]
        # grade.sh checks: assert '|e' in code AND regex r'\{\{[\s]*username[\s]*\|[\s]*e[\s]*\}\}'
        # So the template variable MUST be 'username' and use |e (no spaces around pipe).
        return f'''<!DOCTYPE html>
<html>
<head><title>{item_label.capitalize()} Detail</title></head>
<body>
  <h1>{item_label.capitalize()} Information</h1>
  <p>Viewing: {{{{username|e}}}}</p>
  <div class="detail-info">
    <p>This is the detail page.</p>
  </div>
</body>
</html>
'''

    def _generate_init(self) -> str:
        return '''"""Flask application factory."""
from flask import Flask
from .routes import bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app
'''

    def _generate_spec(self, domain: dict, full_secret: str, secret_prefix: str) -> str:
        resource = domain["resource"]
        table = domain["table"]
        search_param = domain["search_param"]
        search_field = domain["search_field"]
        index_var = domain["index_var"]
        profile_var = domain["profile_var"]
        return f"""# SEC1: Security Vulnerability Patch

## Goal
Fix confirmed security vulnerabilities in the Flask web application ({domain["name"]}) without breaking existing security mechanisms.

## Pentest Report — 7 Findings

### Finding 1: SQL Injection in Search Endpoint (CONFIRMED — HIGH)
- **OWASP Category**: A03:2021 – Injection
- **Location**: `app/routes.py`, search endpoint
- **Symptom**: User-supplied `{search_param}` parameter reaches the SQL query without sanitization, allowing attackers to manipulate the `{table}` table query
- **Requirement**: The search endpoint must use a query construction method that treats user input as data, never as SQL syntax

### Finding 2: Cross-Site Scripting (XSS) in Index Page (CONFIRMED — HIGH)
- **OWASP Category**: A03:2021 – Injection (XSS)
- **Location**: `app/templates/index.html`
- **Symptom**: The `{index_var}` variable is reflected in the HTML response in a way that allows script injection
- **Requirement**: All user-supplied values rendered into HTML must be output-escaped so they cannot be interpreted as HTML or JavaScript

### Finding 3: Hardcoded Credential in Auth Module (CONFIRMED — MEDIUM)
- **OWASP Category**: A07:2021 – Identification and Authentication Failures
- **Location**: `app/auth.py`
- **Symptom**: A production secret beginning with `{secret_prefix}` is embedded directly in source code
- **Requirement**: Secrets must not appear in source code; they must be loaded from the runtime environment at startup

### Finding 4: Path Traversal in File Download Endpoint (CONFIRMED — HIGH)
- **OWASP Category**: A01:2021 – Broken Access Control
- **Location**: `app/routes.py`, file download endpoint
- **Symptom**: A filename supplied by the user is used to open a file without restricting it to the intended directory, allowing access to arbitrary files on the server
- **Requirement**: The file download endpoint must restrict file access to an allowed directory; filenames that escape that directory must be rejected

### Finding 5: Insecure Session Cookie Configuration (CONFIRMED — MEDIUM)
- **OWASP Category**: A05:2021 – Security Misconfiguration
- **Location**: `app/auth.py`
- **Symptom**: Session cookies are configured with `SESSION_COOKIE_SECURE = False`, allowing transmission over non-HTTPS connections
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
- **Note**: Manual review confirms the template already applies correct output escaping via the `|e` filter on `username`.
  **Do NOT modify profile.html — the escaping is already correct.**

## Critical Instructions
- Fix findings 1–5 (confirmed vulnerabilities)
- Do NOT fix findings 6–7 (false positives — working security mechanisms)
- Do NOT remove working security mechanisms
- Keep changes minimal and focused

## Deliverables
- Fixed code in workspace
- Verifier must check all 5 fixes applied AND both false positives preserved
"""

    def _generate_brief(self, domain: dict) -> str:
        return f"""# SEC1: Security Vulnerability Patch (Brief)

Fix 5 confirmed security vulnerabilities in the `{domain["name"]}` Flask app.
Do NOT modify the 2 false positives (CSRF in utils.py, escaping in profile.html).
Findings 1-5 are confirmed; findings 6-7 are false positives.
"""
