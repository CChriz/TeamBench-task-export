"""
Parameterized generator for MULTI1: Fullstack Bug Fix.

Each seed produces:
  - Different entity name (notes/tasks/bookmarks/snippets/reminders)
  - Different field names (title/content vary per seed)
  - Different URL prefix (/api/<entity>)
  - Different deploy script wrong app name
  - Different wrong Content-Type in JS (text/plain / text/html / application/xml)
  - Same 6 bug TYPES but variable/field names change per seed

The 6 bugs are always:
  1. POST reads from request.args instead of request.get_json()
  2. GET returns items oldest-first instead of newest-first
  3. DELETE uses undefined variable (note_id) instead of route param (id)
  4. JS fetch POST uses wrong Content-Type header
  5. JS delete URL uses wrong variable (note.id instead of noteId param)
  6. deploy.sh FLASK_APP points to wrong file (application.py instead of app.py)
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Pool of entity configurations: (entity_name, singular, field1, field2)
ENTITY_CONFIGS = [
    ("notes",     "note",     "title",       "content"),
    ("tasks",     "task",     "title",       "description"),
    ("bookmarks", "bookmark", "title",       "url"),
    ("snippets",  "snippet",  "name",        "code"),
    ("reminders", "reminder", "title",       "message"),
]

# Wrong FLASK_APP values for deploy.sh bug
WRONG_APP_NAMES = [
    "application.py",
    "server.py",
    "main.py",
    "run.py",
    "wsgi.py",
]

# Wrong Content-Type values for JS bug
WRONG_CONTENT_TYPES = [
    "text/plain",
    "text/html",
    "application/xml",
    "application/x-www-form-urlencoded",
    "text/json",
]

# Ports to vary
PORTS = [5000, 5001, 8000, 8080, 4000]


class Generator(TaskGenerator):
    task_id = "MULTI1_fullstack_fix"
    domain = "fullstack"
    difficulty = "medium"
    languages = ["python", "javascript", "bash"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        entity_cfg = rng.choice(ENTITY_CONFIGS)
        entity_name, singular, field1, field2 = entity_cfg

        wrong_app = rng.choice(WRONG_APP_NAMES)
        wrong_ct = rng.choice(WRONG_CONTENT_TYPES)
        port = rng.choice(PORTS)

        # Generate workspace files
        app_py = self._gen_app_py(entity_name, singular, field1, field2, port)
        app_js = self._gen_app_js(entity_name, singular, field1, field2, wrong_ct)
        deploy_sh = self._gen_deploy_sh(wrong_app, port)
        test_py = self._gen_test_py(entity_name, singular, field1, field2, wrong_app, wrong_ct)
        index_html = self._gen_index_html(entity_name, singular, field1, field2)

        workspace_files = {
            "app.py": app_py,
            "static/app.js": app_js,
            "static/index.html": index_html,
            "deploy.sh": deploy_sh,
            "test_app.py": test_py,
        }

        expected = {
            "entity_name": entity_name,
            "singular": singular,
            "field1": field1,
            "field2": field2,
            "url_prefix": f"/api/{entity_name}",
            "wrong_app_name": wrong_app,
            "correct_app_name": "app.py",
            "wrong_content_type": wrong_ct,
            "correct_content_type": "application/json",
            "port": port,
            "bug_count": 6,
            "bugs": [
                f"POST /api/{entity_name} reads from request.args instead of request.get_json()",
                f"GET /api/{entity_name} returns {entity_name} oldest-first (missing ORDER BY id DESC)",
                f"DELETE /api/{entity_name}/<int:id> uses undefined variable {singular}_id instead of id",
                f"static/app.js fetch POST uses Content-Type: {wrong_ct} instead of application/json",
                f"static/app.js deleteNote URL uses {singular}.id instead of {singular}Id parameter",
                f"deploy.sh FLASK_APP={wrong_app} should be FLASK_APP=app.py",
            ],
        }

        spec_md = self._gen_spec(entity_name, singular, field1, field2, port)
        brief_md = self._gen_brief(entity_name, singular, field1, field2)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── File generators ────────────────────────────────────────────────────

    def _gen_app_py(self, entity: str, singular: str, f1: str, f2: str, port: int) -> str:
        entity_upper = entity.capitalize()
        return f'''"""
{entity_upper} web application — Flask backend.
WARNING: This file contains intentional bugs for the TeamBench exercise.
"""

import sqlite3
from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder="static")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return a connection to the in-memory SQLite database attached to app."""
    if not hasattr(app, "_db"):
        app._db = sqlite3.connect(":memory:", check_same_thread=False)
        app._db.row_factory = sqlite3.Row
        _init_db(app._db)
    return app._db


def _init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS {entity} (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            {f1}       TEXT NOT NULL,
            {f2}       TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime(\'now\'))
        )
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/{entity}", methods=["GET"])
def get_{entity}():
    """Return all {entity} as a JSON list, newest first."""
    db = get_db()
    rows = db.execute("SELECT id, {f1}, {f2}, created_at FROM {entity} ORDER BY id").fetchall()
    {entity} = [dict(row) for row in rows]
    return jsonify({entity}), 200


@app.route("/api/{entity}", methods=["POST"])
def create_{singular}():
    """Create a new {singular} from JSON body."""
    {f1} = request.args.get("{f1}", "")
    {f2} = request.args.get("{f2}", "")

    if not {f1}:
        return jsonify({{"error": "{f1} is required"}}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO {entity} ({f1}, {f2}) VALUES (?, ?)",
        ({f1}, {f2}),
    )
    db.commit()
    {singular}_id = cur.lastrowid
    row = db.execute(
        "SELECT id, {f1}, {f2}, created_at FROM {entity} WHERE id = ?",
        ({singular}_id,),
    ).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/{entity}/<int:id>", methods=["DELETE"])
def delete_{singular}(id):
    """Delete a {singular} by id."""
    db = get_db()
    db.execute("DELETE FROM {entity} WHERE id = ?", ({singular}_id,))
    db.commit()
    return jsonify({{"deleted": id}}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, port={port})
'''

    def _gen_app_js(self, entity: str, singular: str, f1: str, f2: str, wrong_ct: str) -> str:
        return f'''/**
 * {entity.capitalize()} app — frontend JavaScript.
 * WARNING: This file contains intentional bugs for the TeamBench exercise.
 */

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function load{entity.capitalize()}() {{
  const res = await fetch("/api/{entity}");
  if (!res.ok) {{
    console.error("Failed to load {entity}:", res.status);
    return;
  }}
  const {entity} = await res.json();
  render{entity.capitalize()}({entity});
}}

async function add{singular.capitalize()}({f1}, {f2}) {{
  const res = await fetch("/api/{entity}", {{
    method: "POST",
    headers: {{
      "Content-Type": "{wrong_ct}",
    }},
    body: JSON.stringify({{ {f1}, {f2} }}),
  }});
  if (!res.ok) {{
    const err = await res.json().catch(() => ({{}}));
    console.error("Failed to add {singular}:", err);
    return;
  }}
  await load{entity.capitalize()}();
}}

async function delete{singular.capitalize()}({singular}Id) {{
  const res = await fetch(`/api/{entity}/${{{singular}.id}}`, {{
    method: "DELETE",
  }});
  if (!res.ok) {{
    console.error("Failed to delete {singular}:", res.status);
    return;
  }}
  await load{entity.capitalize()}();
}}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function render{entity.capitalize()}({entity}) {{
  const container = document.getElementById("{entity}-list");
  if (!{entity} || {entity}.length === 0) {{
    container.innerHTML = "<p>No {entity} yet. Add one above!</p>";
    return;
  }}
  container.innerHTML = {entity}
    .map(
      ({singular}) => `
      <div class="{singular}" data-id="${{{singular}.id}}">
        <button class="delete-btn" data-{singular}-id="${{{singular}.id}}">Delete</button>
        <h3>${{escapeHtml({singular}.{f1})}}</h3>
        <p>${{escapeHtml({singular}.{f2})}}</p>
        <small>${{{singular}.created_at}}</small>
      </div>`
    )
    .join("");

  container.querySelectorAll(".delete-btn").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const {singular}Id = parseInt(btn.dataset.{singular}Id, 10);
      delete{singular.capitalize()}({singular}Id);
    }});
  }});
}}

function escapeHtml(str) {{
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {{
  load{entity.capitalize()}();

  const form = document.getElementById("{singular}-form");
  form.addEventListener("submit", async (e) => {{
    e.preventDefault();
    const {f1} = document.getElementById("{singular}-{f1}").value.trim();
    const {f2} = document.getElementById("{singular}-{f2}").value.trim();
    if (!{f1}) return;
    await add{singular.capitalize()}({f1}, {f2});
    form.reset();
  }});
}});
'''

    def _gen_deploy_sh(self, wrong_app: str, port: int) -> str:
        return f'''#!/usr/bin/env bash
set -euo pipefail

export FLASK_APP={wrong_app}
export FLASK_ENV=production

echo "Deploying {{}}-taking app..."
echo "FLASK_APP=${{FLASK_APP}}"
echo "FLASK_ENV=${{FLASK_ENV}}"

flask run --host=0.0.0.0 --port={port}
'''

    def _gen_test_py(self, entity: str, singular: str, f1: str, f2: str,
                     wrong_app: str, wrong_ct: str) -> str:
        return f'''"""
Test suite for MULTI1_fullstack_fix.
Uses Flask\'s built-in test client — no live server required.
Do NOT modify this file.
"""

import json
import os
import re
import unittest


# ---------------------------------------------------------------------------
# Flask test client setup
# ---------------------------------------------------------------------------

class {entity.capitalize()}AppTestCase(unittest.TestCase):

    def setUp(self):
        """Create a fresh app and in-memory database for each test."""
        import importlib
        import app as app_module
        importlib.reload(app_module)
        self.app_module = app_module
        self.client = app_module.app.test_client()
        app_module.app.testing = True

    # ------------------------------------------------------------------
    # Test 1: Create a {singular} — expects 201 and JSON body with correct fields
    # ------------------------------------------------------------------
    def test_create_{singular}(self):
        """POST /api/{entity} with JSON body should return 201 and the new {singular}."""
        res = self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{f1}": "Hello", "{f2}": "World"}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201, msg=f"Expected 201, got {{res.status_code}}")
        data = json.loads(res.data)
        self.assertEqual(data["{f1}"], "Hello", msg=f"{f1} mismatch: {{data}}")
        self.assertEqual(data["{f2}"], "World", msg=f"{f2} mismatch: {{data}}")
        self.assertIn("id", data)
        self.assertIn("created_at", data)

    # ------------------------------------------------------------------
    # Test 2: Get {entity} — expects 200 and a JSON list
    # ------------------------------------------------------------------
    def test_get_{entity}(self):
        """GET /api/{entity} should return 200 and a JSON list."""
        self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{f1}": "A", "{f2}": "B"}}),
            content_type="application/json",
        )
        res = self.client.get("/api/{entity}")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsInstance(data, list, msg="Expected a list of {entity}")
        self.assertGreater(len(data), 0, msg="Expected at least one {singular}")

    # ------------------------------------------------------------------
    # Test 3: {entity.capitalize()} sorted newest-first
    # ------------------------------------------------------------------
    def test_{entity}_sorted(self):
        """GET /api/{entity} should return {entity} sorted by created_at DESC."""
        import time

        self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{f1}": "First", "{f2}": "oldest"}}),
            content_type="application/json",
        )
        time.sleep(0.05)
        self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{f1}": "Second", "{f2}": "newest"}}),
            content_type="application/json",
        )

        res = self.client.get("/api/{entity}")
        data = json.loads(res.data)
        self.assertGreaterEqual(len(data), 2, msg="Expected at least 2 {entity}")
        self.assertEqual(
            data[0]["{f1}"],
            "Second",
            msg=f"Expected newest {singular} first, got: {{[n['{f1}'] for n in data]}}",
        )

    # ------------------------------------------------------------------
    # Test 4: Delete a {singular} — expects 200
    # ------------------------------------------------------------------
    def test_delete_{singular}(self):
        """DELETE /api/{entity}/<id> should return 200 and remove the {singular}."""
        res = self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{f1}": "ToDelete", "{f2}": "bye"}}),
            content_type="application/json",
        )
        {singular} = json.loads(res.data)
        {singular}_id = {singular}["id"]

        del_res = self.client.delete(f"/api/{entity}/{{{singular}_id}}")
        self.assertEqual(del_res.status_code, 200, msg=f"Expected 200, got {{del_res.status_code}}")

        list_res = self.client.get("/api/{entity}")
        {entity} = json.loads(list_res.data)
        ids = [n["id"] for n in {entity}]
        self.assertNotIn({singular}_id, ids, msg="Deleted {singular} still present in list")

    # ------------------------------------------------------------------
    # Test 5: deploy.sh has correct FLASK_APP value
    # ------------------------------------------------------------------
    def test_deploy_script_env(self):
        """deploy.sh must export FLASK_APP=app.py (not {wrong_app})."""
        deploy_path = os.path.join(os.path.dirname(__file__), "deploy.sh")
        self.assertTrue(os.path.exists(deploy_path), msg="deploy.sh not found")
        with open(deploy_path) as f:
            content = f.read()
        self.assertIn(
            "FLASK_APP=app.py",
            content,
            msg="deploy.sh does not contain FLASK_APP=app.py",
        )
        self.assertNotIn(
            "FLASK_APP={wrong_app}",
            content,
            msg="deploy.sh still contains the buggy FLASK_APP={wrong_app}",
        )

    # ------------------------------------------------------------------
    # Test 6: static/app.js uses application/json Content-Type
    # ------------------------------------------------------------------
    def test_frontend_content_type(self):
        """static/app.js fetch POST must use Content-Type: application/json."""
        js_path = os.path.join(os.path.dirname(__file__), "static", "app.js")
        self.assertTrue(os.path.exists(js_path), msg="static/app.js not found")
        with open(js_path) as f:
            content = f.read()
        self.assertIn(
            "application/json",
            content,
            msg="static/app.js does not contain \'application/json\' in Content-Type",
        )
        self.assertNotIn(
            "{wrong_ct}",
            content,
            msg="static/app.js still contains the buggy \'{wrong_ct}\' Content-Type",
        )


if __name__ == "__main__":
    unittest.main()
'''

    def _gen_index_html(self, entity: str, singular: str, f1: str, f2: str) -> str:
        entity_cap = entity.capitalize()
        singular_cap = singular.capitalize()
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{entity_cap} App</title>
  <style>
    body {{ font-family: sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }}
    h1 {{ font-size: 1.5rem; }}
    form {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; }}
    input, textarea {{ padding: 8px; font-size: 1rem; border: 1px solid #ccc; border-radius: 4px; }}
    button {{ padding: 8px 16px; font-size: 1rem; cursor: pointer; }}
    #{entity}-list .{singular} {{ border: 1px solid #ddd; border-radius: 4px; padding: 12px; margin-bottom: 12px; }}
    #{entity}-list .{singular} h3 {{ margin: 0 0 4px; }}
    #{entity}-list .{singular} p  {{ margin: 0 0 8px; color: #555; }}
    #{entity}-list .{singular} small {{ color: #999; }}
    .delete-btn {{ background: #e55; color: #fff; border: none; border-radius: 4px; padding: 4px 10px; cursor: pointer; float: right; }}
  </style>
</head>
<body>
  <h1>{entity_cap}</h1>

  <form id="{singular}-form">
    <input  id="{singular}-{f1}"   type="text"     placeholder="{f1.capitalize()}"   required />
    <textarea id="{singular}-{f2}" rows="3"         placeholder="{f2.capitalize()}"></textarea>
    <button type="submit">Add {singular_cap}</button>
  </form>

  <div id="{entity}-list"></div>

  <script src="app.js"></script>
</body>
</html>
'''

    def _gen_spec(self, entity: str, singular: str, f1: str, f2: str, port: int) -> str:
        entity_cap = entity.capitalize()
        singular_cap = singular.capitalize()
        return f"""# MULTI1: Fullstack Bug Fix — Full Specification (Planner Only)

## Overview

A simple {singular}-taking web application built with Flask (Python backend), vanilla JS/HTML (frontend), and a bash deploy script. The app has **6 bugs** spread across all 3 layers. All bugs must be fixed so that `python3 test_app.py` passes all 6 tests.

---

## Application Architecture

```
workspace/
  app.py               # Flask backend
  static/
    index.html         # Frontend HTML
    app.js             # Frontend JavaScript
  deploy.sh            # Bash deploy script
  test_app.py          # Test suite (do not modify)
```

The backend uses an in-memory SQLite database (created fresh on app startup). The frontend communicates with the backend via a JSON REST API under `/api/{entity}`.

---

## Bug Inventory

### Backend Bugs — `app.py`

**Bug 1: {singular_cap} creation endpoint does not read the request body**
- **Symptom**: Every {singular} is created with null {f1} and {f2}, regardless of what the client sends
- **Expected behavior**: The POST endpoint must parse the JSON request body and use the `{f1}` and `{f2}` values from it
- **Constraint**: Flask provides `request.get_json()` to access the parsed JSON body; the endpoint currently uses `request.args` (URL query parameters)

**Bug 2: {entity_cap} are returned in the wrong order**
- **Symptom**: The GET /api/{entity} endpoint returns {entity} oldest-first
- **Expected behavior**: {entity_cap} must be returned newest-first so that the most recently created {singular} appears at the top

**Bug 3: Delete endpoint fails at runtime**
- **Symptom**: Any attempt to delete a {singular} causes a server-side error; the delete operation never succeeds
- **Expected behavior**: The DELETE endpoint must correctly identify the {singular} to delete using the ID from the route parameter and remove it from the database

---

### Frontend Bugs — `static/app.js`

**Bug 4: {singular_cap} creation requests are rejected by the backend**
- **Symptom**: Note creation fails because Flask does not parse the request body
- **Expected behavior**: The fetch request must declare `application/json` as its Content-Type so that Flask recognizes and parses the JSON body

**Bug 5: Delete requests are sent to the wrong URL**
- **Symptom**: Clicking delete sends a request to `/api/{entity}/undefined` instead of the correct URL
- **Expected behavior**: The delete fetch request URL must include the actual numeric ID of the {singular} being deleted

---

### Deploy Script Bug — `deploy.sh`

**Bug 6: Deploy script references the wrong application file**
- **Symptom**: Running the deploy script causes Flask to fail on startup because it cannot find the application module
- **Expected behavior**: The `FLASK_APP` environment variable in `deploy.sh` must point to `app.py`

---

## Expected Outcome

After all 6 fixes are applied:

```
python3 test_app.py
```

Should produce:
```
......
----------------------------------------------------------------------
Ran 6 tests in 0.XXXs

OK
```

All 6 tests pass:
1. `test_create_{singular}` — POST creates a {singular} (201 response)
2. `test_get_{entity}` — GET returns a JSON list
3. `test_{entity}_sorted` — newest {singular} appears first
4. `test_delete_{singular}` — DELETE removes a {singular} (200 response)
5. `test_deploy_script_env` — deploy.sh contains correct `FLASK_APP` value
6. `test_frontend_content_type` — app.js declares `application/json`

---

## Constraints

- Do not modify `test_app.py`
- Only `flask` is available as an external dependency (plus Python stdlib: `sqlite3`, `json`, `unittest`)
- The SQLite database is in-memory (`:memory:`) — no persistent storage needed
"""

    def _gen_brief(self, entity: str, singular: str, f1: str, f2: str) -> str:
        return f"""# MULTI1: Fullstack Bug Fix (Brief)

Fix 6 bugs spread across 3 files in a {singular}-management web app.
The app uses Flask (Python), vanilla JS, and a bash deploy script.
Run `python3 test_app.py` — all 6 tests must pass.

Files to fix:
- `app.py` — Flask backend (3 bugs)
- `static/app.js` — frontend JavaScript (2 bugs)
- `deploy.sh` — bash deploy script (1 bug)

Do NOT modify `test_app.py`.
"""
