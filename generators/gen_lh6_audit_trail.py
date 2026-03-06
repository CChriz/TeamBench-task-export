"""
Parameterized generator for LH6: Audit Trail Bug Fixes.

Each seed produces:
- A Python web app with 5 bugs (SQL injection, XSS, missing auth, pagination, CSV)
- An AUDIT_LOG.md template
- Different app domain (blog/store/forum), bug locations, field names per seed
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-variant pools ───────────────────────────────────────────────────────

APP_DOMAINS = [
    {
        "name": "blog",
        "entity": "post",
        "entities": "posts",
        "search_field": "query",
        "title_field": "title",
        "content_field": "body",
        "author_field": "author",
        "table_name": "posts",
        "admin_action": "delete_post",
        "csv_fields": ["id", "title", "author", "created_at"],
    },
    {
        "name": "store",
        "entity": "product",
        "entities": "products",
        "search_field": "term",
        "title_field": "name",
        "content_field": "description",
        "author_field": "vendor",
        "table_name": "products",
        "admin_action": "remove_product",
        "csv_fields": ["id", "name", "price", "vendor"],
    },
    {
        "name": "forum",
        "entity": "thread",
        "entities": "threads",
        "search_field": "keyword",
        "title_field": "subject",
        "content_field": "message",
        "author_field": "poster",
        "table_name": "threads",
        "admin_action": "lock_thread",
        "csv_fields": ["id", "subject", "poster", "replies"],
    },
]

# Per-page size variants
PER_PAGE_VALUES = [10, 20, 25]


class Generator(TaskGenerator):
    task_id = "LH6_audit_trail"
    domain = "long_horizon"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(APP_DOMAINS)

        domain = APP_DOMAINS[idx]
        per_page = PER_PAGE_VALUES[idx]

        workspace_files = self._make_workspace(domain, per_page)

        expected = {
            "seed": seed,
            "app_domain": domain["name"],
            "entity": domain["entity"],
            "search_field": domain["search_field"],
            "table_name": domain["table_name"],
            "db_file": f"app/db.py",
            "views_file": f"app/views.py",
            "per_page": per_page,
            "bugs": [
                "sql_injection_in_search",
                "xss_in_template",
                "missing_auth_check",
                "pagination_off_by_one",
                "broken_csv_export",
            ],
            "bug_count": 5,
            "required_fixes": 4,
            "required_audit_entries": 4,
        }

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "LH6_audit_trail"
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
            metadata={"difficulty": "hard", "category": "Long-Horizon"},
        )

    def _make_workspace(self, domain: dict, per_page: int) -> dict:
        files = {}

        name = domain["name"]
        entity = domain["entity"]
        entities = domain["entities"]
        sf = domain["search_field"]
        tf = domain["title_field"]
        cf = domain["content_field"]
        af = domain["author_field"]
        table = domain["table_name"]
        admin_action = domain["admin_action"]
        csv_fields = domain["csv_fields"]
        csv_header = ",".join(csv_fields)

        # ── app/__init__.py ──────────────────────────────────────────────────
        files["app/__init__.py"] = f'''"""
{name.title()} application — a simple Python web app.
"""
'''

        # ── app/db.py (Bug 1: SQL injection) ─────────────────────────────────
        files["app/db.py"] = f'''"""
Database access layer for {name} app.
"""
import sqlite3


DB_PATH = "{name}.db"


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {tf} TEXT NOT NULL,
            {cf} TEXT,
            {af} TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def search_{entities}({sf}):
    """
    Search {entities} by {sf}.
    BUG: SQL injection — user input is concatenated directly into query.
    """
    conn = get_connection()
    # VULNERABLE: direct string formatting in SQL query
    sql = f"SELECT * FROM {table} WHERE {tf} LIKE '%{{{sf}}}%' OR {cf} LIKE '%{{{sf}}}%'"
    cursor = conn.execute(sql)
    results = cursor.fetchall()
    conn.close()
    return results


def get_{entity}(item_id):
    """Get a single {entity} by ID."""
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM {table} WHERE id = ?", (item_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def create_{entity}({tf}, {cf}, {af}):
    """Create a new {entity}."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO {table} ({tf}, {cf}, {af}) VALUES (?, ?, ?)",
        ({tf}, {cf}, {af}),
    )
    conn.commit()
    conn.close()


def delete_{entity}(item_id):
    """Delete a {entity} by ID."""
    conn = get_connection()
    conn.execute("DELETE FROM {table} WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def list_{entities}(offset=0, limit={per_page}):
    """List {entities} with pagination."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM {table} ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    )
    results = cursor.fetchall()
    conn.close()
    return results


def count_{entities}():
    """Count total {entities}."""
    conn = get_connection()
    cursor = conn.execute("SELECT COUNT(*) as cnt FROM {table}")
    result = cursor.fetchone()
    conn.close()
    return result["cnt"]
'''

        # ── app/views.py (Bugs 2-5) ─────────────────────────────────────────
        files["app/views.py"] = f'''"""
View handlers for {name} app.
Contains rendering, admin actions, pagination, and export logic.
"""
import html as html_module
from app import db


PER_PAGE = {per_page}


# ── Rendering (Bug 2: XSS) ──────────────────────────────────────────────

def render_{entity}_card({entity}):
    """
    Render a {entity} as an HTML card.
    BUG: XSS — user content is inserted without HTML escaping.
    """
    {tf} = {entity}["{tf}"]
    {cf} = {entity}["{cf}"]
    {af} = {entity}["{af}"]
    # VULNERABLE: no HTML escaping on user-supplied content
    return f"""
    <div class="card">
        <h2>{{{tf}}}</h2>
        <p>{{{cf}}}</p>
        <span class="author">By {{{af}}}</span>
    </div>
    """


def render_{entity}_list({entities}):
    """Render a list of {entities} as HTML."""
    cards = [render_{entity}_card(p) for p in {entities}]
    return "<div class=\\"{entities}-list\\">" + "\\n".join(cards) + "</div>"


# ── Admin Actions (Bug 3: Missing auth check) ───────────────────────────

def {admin_action}(user, {entity}_id):
    """
    Admin action to {admin_action.replace('_', ' ')}.
    BUG: Missing authentication check — any user can execute this.
    """
    # MISSING: should check user["role"] == "admin" and return 403 if not
    db.delete_{entity}({entity}_id)
    return {{"status": "ok", "message": "{entity} removed"}}


def list_users(user):
    """List all users. Requires admin role."""
    if user.get("role") != "admin":
        return {{"status": "error", "code": 403, "message": "Forbidden"}}
    return {{"status": "ok", "users": []}}


# ── Pagination (Bug 4: Off-by-one) ──────────────────────────────────────

def get_{entities}_page(page=1):
    """
    Get a page of {entities}.
    BUG: Off-by-one — offset calculation causes first item to duplicate.
    """
    # BUGGY: should be (page - 1) * PER_PAGE, not page * PER_PAGE
    offset = page * PER_PAGE
    items = db.list_{entities}(offset=offset, limit=PER_PAGE)
    total = db.count_{entities}()
    total_pages = (total + PER_PAGE - 1) // PER_PAGE
    return {{
        "items": items,
        "page": page,
        "per_page": PER_PAGE,
        "total": total,
        "total_pages": total_pages,
    }}


# ── CSV Export (Bug 5: Broken quoting) ──────────────────────────────────

def export_{entities}_csv({entities}):
    """
    Export {entities} as CSV string.
    BUG: Does not properly escape fields containing commas or quotes.
    """
    lines = ["{csv_header}"]
    for item in {entities}:
        # BUGGY: no quoting/escaping — commas in fields break CSV
        fields = [{", ".join(f'str(item.get("{f}", ""))' for f in csv_fields)}]
        lines.append(",".join(fields))
    return "\\n".join(lines)
'''

        # ── app/auth.py ──────────────────────────────────────────────────────
        files["app/auth.py"] = f'''"""
Authentication helpers for {name} app.
"""


def is_admin(user):
    """Check if user has admin role."""
    return user.get("role") == "admin"


def require_admin(user):
    """Raise if user is not admin. Returns error dict."""
    if not is_admin(user):
        return {{"status": "error", "code": 403, "message": "Forbidden"}}
    return None
'''

        # ── AUDIT_LOG.md (template) ──────────────────────────────────────────
        files["AUDIT_LOG.md"] = f"""# Audit Log — {name.title()} Application

All code changes must be documented below with structured entries.
Each fix must include: File, Bug description, Fix description, Risk level.

---

"""

        # ── tests/__init__.py ────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_app.py ────────────────────────────────────────────────
        files["tests/test_app.py"] = f'''"""
Basic tests for the {name} application.
"""
import pytest


def test_audit_log_exists():
    """AUDIT_LOG.md must exist."""
    import os
    assert os.path.exists("AUDIT_LOG.md"), "AUDIT_LOG.md is missing"


def test_audit_log_has_header():
    """AUDIT_LOG.md must have the header."""
    with open("AUDIT_LOG.md") as f:
        content = f.read()
    assert "# Audit Log" in content


def test_db_module_imports():
    """Database module must be importable."""
    from app import db
    assert hasattr(db, "search_{entities}")
    assert hasattr(db, "get_{entity}")


def test_views_module_imports():
    """Views module must be importable."""
    from app import views
    assert hasattr(views, "render_{entity}_card")
    assert hasattr(views, "export_{entities}_csv")
'''

        # ── requirements.txt ─────────────────────────────────────────────────
        files["requirements.txt"] = "pytest\n"

        return files
