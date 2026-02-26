"""
Parameterized generator for CR1: Code Review Response.

Each seed produces:
- A different Python app domain (user auth, payment processor, data pipeline,
  notification system, cache manager)
- Different variable/function names within each domain
- 4-6 code review comments covering: security fix, performance optimization,
  error handling, naming convention, dead code removal, type safety
- An app.py with working code that has the issues embedded at specific lines
- A test suite that tests the correct behavior (must pass before and after fixes)
- A review_summary.txt that states the count of comments but NOT their content

TNI driver: The Executor can only see the workspace (app.py, tests/, review_summary.txt).
The spec contains the actual review comments with line numbers and required changes.
The Planner must relay every specific fix to the Executor.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ---------------------------------------------------------------------------
# Domain definitions
# Each domain has enough variation to produce genuinely different workspaces.
# ---------------------------------------------------------------------------

DOMAINS = [
    {
        "name": "user_auth",
        "module_title": "User Authentication Module",
        "description": "handles user login, token generation, and session validation",
        "class_name": "AuthManager",
        "main_resource": "user",
        "table": "users",
        "email_field": "email",
    },
    {
        "name": "payment_processor",
        "module_title": "Payment Processing Module",
        "description": "handles payment validation, charge execution, and refund logic",
        "class_name": "PaymentProcessor",
        "main_resource": "payment",
        "table": "payments",
        "email_field": "customer_email",
    },
    {
        "name": "data_pipeline",
        "module_title": "Data Ingestion Pipeline",
        "description": "handles record ingestion, transformation, and storage",
        "class_name": "PipelineRunner",
        "main_resource": "record",
        "table": "records",
        "email_field": "contact_email",
    },
    {
        "name": "notification_system",
        "module_title": "Notification Dispatch System",
        "description": "handles notification queuing, dispatch, and delivery tracking",
        "class_name": "NotificationManager",
        "main_resource": "notification",
        "table": "notifications",
        "email_field": "recipient_email",
    },
    {
        "name": "cache_manager",
        "module_title": "Cache Management Layer",
        "description": "handles cache population, invalidation, and TTL enforcement",
        "class_name": "CacheManager",
        "main_resource": "entry",
        "table": "cache_entries",
        "email_field": "owner_email",
    },
]

# Bad function names that will be used per domain (to be renamed in review)
BAD_FUNC_NAMES = [
    ("doStuff", "process_records"),
    ("handleIt", "execute_task"),
    ("runAll", "dispatch_all"),
    ("doWork", "run_pipeline"),
    ("processData", "transform_entries"),
]

# Specific exception tuples for the error-handling fix (per domain)
EXCEPTION_PAIRS = [
    ("ValueError, KeyError", "ValueError, KeyError"),
    ("ValueError, TypeError", "ValueError, TypeError"),
    ("KeyError, AttributeError", "KeyError, AttributeError"),
    ("ValueError, RuntimeError", "ValueError, RuntimeError"),
    ("TypeError, IndexError", "TypeError, IndexError"),
]


class Generator(TaskGenerator):
    task_id = "CR1_review_respond"
    domain = "code_review"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        domain = DOMAINS[rng.randint(0, len(DOMAINS) - 1)]
        bad_func, good_func = BAD_FUNC_NAMES[rng.randint(0, len(BAD_FUNC_NAMES) - 1)]
        exc_pair, _ = EXCEPTION_PAIRS[rng.randint(0, len(EXCEPTION_PAIRS) - 1)]

        # Build the workspace files
        app_py, line_map = self._generate_app(domain, bad_func)
        test_py = self._generate_tests(domain, good_func)
        review_summary = self._generate_review_summary(domain)

        workspace_files = {
            "app.py": app_py,
            "tests/__init__.py": "",
            "tests/test_app.py": test_py,
            "review_summary.txt": review_summary,
        }

        # Ground-truth for grading
        expected = {
            "domain": domain["name"],
            "class_name": domain["class_name"],
            "table": domain["table"],
            "bad_func_name": bad_func,
            "good_func_name": good_func,
            "exception_pair": exc_pair,
            "sql_fix": "parameterized",
            "batch_fix": "IN clause",
            "rename_fix": good_func,
            "except_fix": exc_pair,
            "line_map": line_map,
        }

        spec_md = self._generate_spec(domain, bad_func, good_func, exc_pair, line_map)
        brief_md = self._generate_brief(domain)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # Workspace generation
    # ------------------------------------------------------------------

    def _generate_app(self, domain: dict, bad_func: str) -> tuple[str, dict]:
        """
        Generate app.py and return the source plus a map of issue -> line number.
        Line numbers are computed by counting lines as we build the file.
        """
        cls = domain["class_name"]
        table = domain["table"]
        email = domain["email_field"]
        resource = domain["main_resource"]
        desc = domain["description"]

        lines = []

        def L(text: str = "") -> None:
            lines.append(text)

        L(f'"""')
        L(f'{domain["module_title"]}')
        L(f'')
        L(f'This module {desc}.')
        L(f'"""')
        L(f'import sqlite3')
        L(f'import logging')
        L(f'from typing import List, Dict, Any, Optional')
        L(f'')
        L(f'logger = logging.getLogger(__name__)')
        L(f'')
        L(f'DATABASE = "app.db"')
        L(f'')
        L(f'')

        # Issue 1: SQL injection via string formatting — track line number
        sql_func_start = len(lines) + 1
        L(f'def lookup_{resource}_by_{email.replace("_email", "")}(conn: sqlite3.Connection, {email}: str) -> Optional[Dict[str, Any]]:')
        L(f'    """Fetch a {resource} record by {email}."""')
        sql_issue_line = len(lines) + 1
        L(f'    query = f"SELECT * FROM {table} WHERE {email}=\'{{{{  {email}  }}}}\'"')
        L(f'    cursor = conn.execute(query)')
        L(f'    row = cursor.fetchone()')
        L(f'    if row is None:')
        L(f'        return None')
        L(f'    return dict(row)')
        L(f'')
        L(f'')

        # Issue 2: N+1 query — track line number
        n1_func_start = len(lines) + 1
        L(f'def get_{resource}_emails(conn: sqlite3.Connection, ids: List[int]) -> List[str]:')
        L(f'    """Return the {email} for each id in the list."""')
        n1_issue_line = len(lines) + 1
        L(f'    results = []')
        L(f'    for rid in ids:')
        n1_loop_line = len(lines)  # the for-loop line
        L(f'        row = conn.execute(')
        L(f'            f"SELECT {email} FROM {table} WHERE id={{{{rid}}}}"')
        L(f'        ).fetchone()')
        L(f'        if row:')
        L(f'            results.append(row[0])')
        L(f'    return results')
        L(f'')
        L(f'')

        # Issue 3: Bad function name — track line number
        bad_func_line = len(lines) + 1
        L(f'def {bad_func}(conn: sqlite3.Connection, items: List[Dict[str, Any]]) -> int:')
        L(f'    """Process a batch of {resource} items and store them.')
        L(f'')
        L(f'    Returns the count of successfully stored items.')
        L(f'    """')
        L(f'    count = 0')
        L(f'    for item in items:')
        L(f'        try:')
        L(f'            conn.execute(')
        L(f'                "INSERT INTO {table} ({email}, status) VALUES (?, ?)",')
        L(f'                (item["{email}"], item.get("status", "pending")),')
        L(f'            )')
        L(f'            count += 1')
        L(f'        except Exception as e:')
        L(f'            logger.error("Failed to store item: %s", e)')
        L(f'    return count')
        L(f'')
        L(f'')

        # Issue 4: Bare except — track line number
        bare_func_start = len(lines) + 1
        L(f'def validate_{resource}(data: Dict[str, Any]) -> bool:')
        L(f'    """Validate a {resource} data dict.  Returns True if valid."""')
        L(f'    try:')
        L(f'        assert isinstance(data["{email}"], str), "email must be str"')
        L(f'        assert "@" in data["{email}"], "email must contain @"')
        L(f'        assert isinstance(data.get("status", "pending"), str), "status must be str"')
        L(f'        return True')
        bare_except_line = len(lines) + 1
        L(f'    except:')
        L(f'        return False')
        L(f'')
        L(f'')

        # Dead code (no review comment about it — keeps it realistic)
        L(f'def _unused_helper() -> None:')
        L(f'    """This helper is no longer used but was not flagged in the review."""')
        L(f'    pass')
        L(f'')
        L(f'')

        # A clean helper that tests call
        L(f'def create_schema(conn: sqlite3.Connection) -> None:')
        L(f'    """Create the database schema."""')
        L(f'    conn.execute(')
        L(f'        "CREATE TABLE IF NOT EXISTS {table} "')
        L(f'        "(id INTEGER PRIMARY KEY AUTOINCREMENT, {email} TEXT, status TEXT)"')
        L(f'    )')
        L(f'    conn.commit()')
        L(f'')

        source = "\n".join(lines)
        # Repair the f-string triple-brace issue in SQL line — we used {{{{ }}}} above
        # to produce {{ }} in the f-string which itself produces { } at runtime.
        # In the actual file we want a literal Python f-string with single braces:
        #   f"SELECT * FROM users WHERE email='{email}'"
        # The generator string itself used {{{{ }}}} to escape through two layers of
        # Python f-string evaluation (the outer one here, the inner one in app.py).
        # Let's just build app.py as a plain string with careful quoting instead.
        source, line_map = self._build_app_source(domain, bad_func)
        return source, line_map

    def _build_app_source(self, domain: dict, bad_func: str) -> tuple[str, dict]:
        """Build app.py source as a plain string with correct line numbers tracked."""
        cls = domain["class_name"]
        table = domain["table"]
        email = domain["email_field"]
        resource = domain["main_resource"]
        desc = domain["description"]

        parts = []
        line_no = [0]  # mutable counter

        def emit(*text_lines):
            for t in text_lines:
                parts.append(t)
                line_no[0] += 1

        def mark() -> int:
            return line_no[0] + 1  # next line number

        emit(
            f'"""',
            f'{domain["module_title"]}',
            f'',
            f'This module {desc}.',
            f'"""',
            f'import sqlite3',
            f'import logging',
            f'from typing import List, Dict, Any, Optional',
            f'',
            f'logger = logging.getLogger(__name__)',
            f'',
            f'DATABASE = "app.db"',
            f'',
            f'',
        )

        # ── Issue 1: SQL injection ────────────────────────────────────────
        emit(
            f'def lookup_{resource}_by_{email.replace("_email", "")}(',
            f'    conn: sqlite3.Connection, {email}: str',
            f') -> Optional[Dict[str, Any]]:',
            f'    """Fetch a {resource} record by {email}."""',
        )
        sql_line = mark()
        emit(
            f'    query = f"SELECT * FROM {table} WHERE {email}=\'{{{email}}}\'"',
            f'    cursor = conn.execute(query)',
            f'    row = cursor.fetchone()',
            f'    if row is None:',
            f'        return None',
            f'    return dict(row)',
            f'',
            f'',
        )

        # ── Issue 2: N+1 query ────────────────────────────────────────────
        emit(
            f'def get_{resource}_emails(conn: sqlite3.Connection, ids: List[int]) -> List[str]:',
            f'    """Return the {email} for each id in the list."""',
        )
        n1_line = mark()
        emit(
            f'    results = []',
            f'    for rid in ids:',
            f'        row = conn.execute(',
            f'            f"SELECT {email} FROM {table} WHERE id={{rid}}"',
            f'        ).fetchone()',
            f'        if row:',
            f'            results.append(row[0])',
            f'    return results',
            f'',
            f'',
        )

        # ── Issue 3: Bad function name ────────────────────────────────────
        bad_func_line = mark()
        emit(
            f'def {bad_func}(conn: sqlite3.Connection, items: List[Dict[str, Any]]) -> int:',
            f'    """Process a batch of {resource} items and store them.',
            f'',
            f'    Returns the count of successfully stored items.',
            f'    """',
            f'    count = 0',
            f'    for item in items:',
            f'        try:',
            f'            conn.execute(',
            f'                "INSERT INTO {table} ({email}, status) VALUES (?, ?)",',
            f'                (item["{email}"], item.get("status", "pending")),',
            f'            )',
            f'            count += 1',
            f'        except Exception as e:',
            f'            logger.error("Failed to store item: %s", e)',
            f'    return count',
            f'',
            f'',
        )

        # ── Issue 4: Bare except ──────────────────────────────────────────
        emit(
            f'def validate_{resource}(data: Dict[str, Any]) -> bool:',
            f'    """Validate a {resource} data dict.  Returns True if valid."""',
            f'    try:',
            f'        if not isinstance(data["{email}"], str):',
            f'            raise ValueError("email must be a string")',
            f'        if "@" not in data["{email}"]:',
            f'            raise ValueError("email must contain @")',
            f'        if not isinstance(data.get("status", "pending"), str):',
            f'            raise ValueError("status must be a string")',
            f'        return True',
        )
        bare_line = mark()
        emit(
            f'    except:',
            f'        return False',
            f'',
            f'',
        )

        # ── Dead code (not flagged in review, just realistic noise) ───────
        emit(
            f'def _unused_helper() -> None:',
            f'    """This helper is no longer used."""',
            f'    pass',
            f'',
            f'',
        )

        # ── Clean helper used by tests ────────────────────────────────────
        emit(
            f'def create_schema(conn: sqlite3.Connection) -> None:',
            f'    """Create the database schema."""',
            f'    conn.execute(',
            f'        "CREATE TABLE IF NOT EXISTS {table} "',
            f'        "(id INTEGER PRIMARY KEY AUTOINCREMENT, {email} TEXT, status TEXT)"',
            f'    )',
            f'    conn.commit()',
            f'',
        )

        source = "\n".join(parts)
        line_map = {
            "sql_injection": sql_line,
            "n_plus_one": n1_line,
            "bad_func_name": bad_func_line,
            "bare_except": bare_line,
        }
        return source, line_map

    def _generate_tests(self, domain: dict, good_func: str) -> str:
        """Generate tests that pass against the FIXED code."""
        cls = domain["class_name"]
        table = domain["table"]
        email = domain["email_field"]
        resource = domain["main_resource"]

        return f'''"""Tests for {domain["module_title"]}.

These tests are written against the FIXED version of app.py.
They must all pass after the code review changes are applied.
"""
import sqlite3
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app


@pytest.fixture
def conn():
    """In-memory SQLite connection for each test."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    app.create_schema(c)
    yield c
    c.close()


def test_validate_{resource}_valid(conn):
    """Valid {resource} data should return True."""
    data = {{"{email}": "user@example.com", "status": "active"}}
    assert app.validate_{resource}(data) is True


def test_validate_{resource}_missing_at(conn):
    """Email without @ should fail validation."""
    data = {{"{email}": "notanemail", "status": "active"}}
    assert app.validate_{resource}(data) is False


def test_validate_{resource}_wrong_type(conn):
    """Non-string email should fail validation."""
    data = {{"{email}": 12345, "status": "active"}}
    assert app.validate_{resource}(data) is False


def test_{good_func}_returns_count(conn):
    """Batch store should return count of inserted items."""
    items = [
        {{"{email}": "a@example.com", "status": "pending"}},
        {{"{email}": "b@example.com", "status": "active"}},
    ]
    count = app.{good_func}(conn, items)
    assert count == 2


def test_get_{resource}_emails_batch(conn):
    """get_{resource}_emails must return emails for given ids."""
    # Insert two rows
    conn.execute(
        "INSERT INTO {table} ({email}, status) VALUES (?, ?)",
        ("x@example.com", "pending"),
    )
    conn.execute(
        "INSERT INTO {table} ({email}, status) VALUES (?, ?)",
        ("y@example.com", "active"),
    )
    conn.commit()
    emails = app.get_{resource}_emails(conn, [1, 2])
    assert set(emails) == {{"x@example.com", "y@example.com"}}


def test_lookup_{resource}_found(conn):
    """lookup should find a record that exists."""
    conn.execute(
        "INSERT INTO {table} ({email}, status) VALUES (?, ?)",
        ("find@example.com", "active"),
    )
    conn.commit()
    result = app.lookup_{resource}_by_{email.replace("_email", "")}(conn, "find@example.com")
    assert result is not None
    assert result["{email}"] == "find@example.com"


def test_lookup_{resource}_not_found(conn):
    """lookup should return None for a record that does not exist."""
    result = app.lookup_{resource}_by_{email.replace("_email", "")}(conn, "missing@example.com")
    assert result is None


def test_create_schema(conn):
    """create_schema should create the table without error."""
    # Schema was already created by fixture; calling again should be idempotent
    app.create_schema(conn)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    assert cur.fetchone() is not None
'''

    def _generate_review_summary(self, domain: dict) -> str:
        return f"""Code Review Summary
===================

Module: {domain["module_title"]}
Reviewer: Senior Engineering Team
Review Date: 2025-01-15
Status: Changes Requested

4 review comments have been filed against this module.
All comments must be addressed before the pull request can be merged.

The detailed review comments (with line numbers and required changes)
are available in the code review system and have been shared with
the team lead. Address ALL 4 comments in full.

Do not make changes beyond what is requested in the review comments.
"""

    # ------------------------------------------------------------------
    # Spec and Brief
    # ------------------------------------------------------------------

    def _generate_spec(
        self,
        domain: dict,
        bad_func: str,
        good_func: str,
        exc_pair: str,
        line_map: dict,
    ) -> str:
        table = domain["table"]
        email = domain["email_field"]
        resource = domain["main_resource"]
        cls = domain["class_name"]
        sql_line = line_map["sql_injection"]
        n1_line = line_map["n_plus_one"]
        bf_line = line_map["bad_func_name"]
        bare_line = line_map["bare_except"]

        return f"""# CR1: Code Review Response

## Goal
Apply all code review feedback to `app.py` so the module passes the review
and all tests in `tests/test_app.py` continue to pass.

## Module Under Review
**{domain["module_title"]}** — `app.py`

This module {domain["description"]}.

---

## Review Comments

### Review Comment #1 — SECURITY (sql_injection)
**File**: `app.py`
**Line**: {sql_line}
**Category**: Security — SQL Injection

**Current code** (line {sql_line}):
```python
    query = f"SELECT * FROM {table} WHERE {email}='{{{{  {email}  }}}}'"
```

**Problem**: The `{email}` parameter is interpolated directly into the SQL
string using an f-string. An attacker can supply a value like
`' OR '1'='1` to bypass authentication or exfiltrate data from the
`{table}` table.

**Required change**: Replace the f-string query with a **parameterized query**
using the `?` placeholder. The correct form is:
```python
    query = "SELECT * FROM {table} WHERE {email}=?"
    cursor = conn.execute(query, ({email},))
```
The table name is `{table}` and the column is `{email}`.

---

### Review Comment #2 — PERFORMANCE (n_plus_one)
**File**: `app.py`
**Line**: {n1_line}
**Category**: Performance — N+1 Query

**Current code** (lines {n1_line}–{n1_line + 6}):
```python
    results = []
    for rid in ids:
        row = conn.execute(
            f"SELECT {email} FROM {table} WHERE id={{{{rid}}}}"
        ).fetchone()
        if row:
            results.append(row[0])
    return results
```

**Problem**: The function issues one SQL query per id, causing N+1 database
round-trips. For large `ids` lists this is a serious performance bottleneck.

**Required change**: Replace the loop with a single **batch SELECT using an
IN clause**. The correct form is:
```python
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT {email} FROM {table} WHERE id IN ({{{{placeholders}}}})",
        ids,
    ).fetchall()
    return [row[0] for row in rows]
```

---

### Review Comment #3 — NAMING (bad_func_name)
**File**: `app.py`
**Line**: {bf_line}
**Category**: Naming Convention

**Current code** (line {bf_line}):
```python
def {bad_func}(conn: sqlite3.Connection, items: List[Dict[str, Any]]) -> int:
```

**Problem**: The function name `{bad_func}` is a vague, non-descriptive
identifier that violates the team's naming convention (snake_case, verb +
noun describing what the function does).

**Required change**: Rename the function to `{good_func}`. Update all call
sites inside `app.py` if any exist. The signature and body remain unchanged.

---

### Review Comment #4 — ERROR HANDLING (bare_except)
**File**: `app.py`
**Line**: {bare_line}
**Category**: Error Handling

**Current code** (line {bare_line}):
```python
    except:
```

**Problem**: A bare `except:` clause catches **every** exception including
`SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`. This can hide serious
runtime failures and makes debugging extremely difficult.

**Required change**: Replace the bare `except:` with a specific exception
tuple. The correct form is:
```python
    except ({exc_pair}):
```
Only `{exc_pair}` should be caught here; all other exceptions
should propagate normally.

---

## Constraints
- Address ALL 4 review comments — do not skip any.
- Do NOT make changes to `tests/test_app.py`.
- Do NOT make changes beyond what the review comments request (no refactoring,
  no new features, no style changes outside those explicitly listed).
- The renamed function (`{good_func}`) must be callable from `tests/test_app.py`
  — the tests already reference the corrected name.
- All 4 changes are in `app.py` only.

## Deliverables
1. `app.py` with all 4 review comments addressed.
2. `tests/test_app.py` must pass without modification.
3. Verifier writes `attestation.json` with `verdict: pass` once all checks pass.
"""

    def _generate_brief(self, domain: dict) -> str:
        return f"""# CR1: Code Review Response (Brief)

## Your Task
Address all code review feedback for the **{domain["module_title"]}** (`app.py`).

A code review has been completed and **4 review comments** must be resolved
before this pull request can be merged.

## What You Know
- The module is in `app.py`.
- There are exactly **4 review comments** to address (see `review_summary.txt`).
- `review_summary.txt` confirms the count but does NOT contain the actual comments.
- The detailed review comments (line numbers, exact changes required) have been
  provided to the Planner — follow the Planner's instructions precisely.
- `tests/test_app.py` must continue to pass without any modification.

## Rules
- Do NOT modify `tests/test_app.py`.
- Do NOT make changes beyond what the review specifies.
- All changes are in `app.py` only.
"""
