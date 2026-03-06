"""
Parameterized generator for MULTI6: Fullstack Bug Fix.

Each seed produces:
  - Different item entity name and field names
  - Different stale field name in types.json
  - Same 3 bug types: envelope wrapping, wrong frontend field, stale type definition

The 3 bugs are always:
  1. Backend GET wraps items in {"data": [...]} instead of returning plain array
  2. Frontend reads item.description instead of the correct detail field
  3. types.json lists "timestamp" instead of "created_at"
"""
from __future__ import annotations

import json
import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

ENTITY_CONFIGS = [
    {"entity": "items",    "singular": "item",    "title": "title",   "detail": "body"},
    {"entity": "posts",    "singular": "post",    "title": "title",   "detail": "content"},
    {"entity": "entries",  "singular": "entry",   "title": "heading", "detail": "text"},
    {"entity": "records",  "singular": "record",  "title": "name",    "detail": "summary"},
    {"entity": "articles", "singular": "article", "title": "title",   "detail": "paragraph"},
]

PORTS = [5000, 5001, 8000, 8080, 4000]


class Generator(TaskGenerator):
    task_id = "MULTI6_fullstack_bug"
    domain = "fullstack"
    difficulty = "hard"
    languages = ["python", "javascript"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = ENTITY_CONFIGS[seed % len(ENTITY_CONFIGS)]
        port = PORTS[seed % len(PORTS)]

        entity = cfg["entity"]
        singular = cfg["singular"]
        title_f = cfg["title"]
        detail_f = cfg["detail"]

        workspace_files = {
            "app.py": self._gen_app(entity, singular, title_f, detail_f, port),
            "static/app.js": self._gen_js(entity, singular, title_f, detail_f),
            "static/index.html": self._gen_html(entity, singular, title_f, detail_f),
            "types.json": self._gen_types_buggy(entity, title_f, detail_f),
            "test_app.py": self._gen_tests(entity, singular, title_f, detail_f),
        }

        expected = {
            "seed": seed,
            "entity": entity,
            "singular": singular,
            "title_field": title_f,
            "detail_field": detail_f,
            "time_field": "created_at",
            "port": port,
            "bugs": [
                f"GET /api/{entity} wraps result in {{\"data\": [...]}} instead of plain array",
                f"static/app.js reads item.description instead of item.{detail_f}",
                "types.json lists 'timestamp' instead of 'created_at'",
            ],
        }

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
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
            metadata={"difficulty": "hard", "category": "Multi-language"},
        )

    def _gen_app(self, entity, singular, title_f, detail_f, port):
        return f'''"""
{entity.capitalize()} web application — Flask backend.
"""
import sqlite3
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")


def get_db():
    if not hasattr(app, "_db"):
        app._db = sqlite3.connect(":memory:", check_same_thread=False)
        app._db.row_factory = sqlite3.Row
        app._db.execute("""
            CREATE TABLE IF NOT EXISTS {entity} (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                {title_f}  TEXT NOT NULL,
                {detail_f} TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        app._db.commit()
    return app._db


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/{entity}", methods=["GET"])
def get_{entity}():
    db = get_db()
    rows = db.execute(
        "SELECT id, {title_f}, {detail_f}, created_at FROM {entity} ORDER BY id DESC"
    ).fetchall()
    {entity}_list = [dict(row) for row in rows]
    return jsonify({{"data": {entity}_list}}), 200


@app.route("/api/{entity}", methods=["POST"])
def create_{singular}():
    data = request.get_json()
    {title_f} = data.get("{title_f}", "")
    {detail_f} = data.get("{detail_f}", "")
    if not {title_f}:
        return jsonify({{"error": "{title_f} is required"}}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO {entity} ({title_f}, {detail_f}) VALUES (?, ?)",
        ({title_f}, {detail_f}),
    )
    db.commit()
    row = db.execute(
        "SELECT id, {title_f}, {detail_f}, created_at FROM {entity} WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/{entity}/<int:id>", methods=["DELETE"])
def delete_{singular}(id):
    db = get_db()
    db.execute("DELETE FROM {entity} WHERE id = ?", (id,))
    db.commit()
    return jsonify({{"deleted": id}}), 200


if __name__ == "__main__":
    app.run(debug=False, port={port})
'''

    def _gen_js(self, entity, singular, title_f, detail_f):
        return f'''/**
 * {entity.capitalize()} app — frontend JavaScript.
 */

async function load{entity.capitalize()}() {{
  const res = await fetch("/api/{entity}");
  const {entity} = await res.json();
  render{entity.capitalize()}({entity});
}}

async function add{singular.capitalize()}({title_f}, {detail_f}) {{
  await fetch("/api/{entity}", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ {title_f}, {detail_f} }}),
  }});
  await load{entity.capitalize()}();
}}

function render{entity.capitalize()}({entity}) {{
  const container = document.getElementById("{entity}-list");
  if (!{entity} || {entity}.length === 0) {{
    container.innerHTML = "<p>No {entity} yet.</p>";
    return;
  }}
  container.innerHTML = {entity}
    .map(
      ({singular}) => `
      <div class="{singular}">
        <h3>${{{singular}.{title_f}}}</h3>
        <p>${{{singular}.description}}</p>
        <small>${{{singular}.created_at}}</small>
      </div>`
    )
    .join("");
}}

document.addEventListener("DOMContentLoaded", () => {{
  load{entity.capitalize()}();
  const form = document.getElementById("{singular}-form");
  form.addEventListener("submit", async (e) => {{
    e.preventDefault();
    const {title_f} = document.getElementById("{singular}-{title_f}").value.trim();
    const {detail_f} = document.getElementById("{singular}-{detail_f}").value.trim();
    if (!{title_f}) return;
    await add{singular.capitalize()}({title_f}, {detail_f});
    form.reset();
  }});
}});
'''

    def _gen_html(self, entity, singular, title_f, detail_f):
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{entity.capitalize()} App</title>
</head>
<body>
  <h1>{entity.capitalize()}</h1>
  <form id="{singular}-form">
    <input id="{singular}-{title_f}" type="text" placeholder="{title_f.capitalize()}" required />
    <textarea id="{singular}-{detail_f}" placeholder="{detail_f.capitalize()}"></textarea>
    <button type="submit">Add {singular.capitalize()}</button>
  </form>
  <div id="{entity}-list"></div>
  <script src="app.js"></script>
</body>
</html>
'''

    def _gen_types_buggy(self, entity, title_f, detail_f):
        schema = {
            "item": {
                "fields": [
                    {"name": "id", "type": "integer"},
                    {"name": title_f, "type": "string"},
                    {"name": detail_f, "type": "string"},
                    {"name": "timestamp", "type": "string"},
                ]
            },
            "list_endpoint": {
                "path": f"/api/{entity}",
                "method": "GET",
                "response": "array of item",
            },
        }
        return json.dumps(schema, indent=2) + "\n"

    def _gen_tests(self, entity, singular, title_f, detail_f):
        return f'''"""
Test suite for MULTI6_fullstack_bug. Do NOT modify.
"""
import json
import os
import unittest


class {entity.capitalize()}AppTestCase(unittest.TestCase):

    def setUp(self):
        import importlib
        import app as app_module
        importlib.reload(app_module)
        self.client = app_module.app.test_client()
        app_module.app.testing = True

    def test_create_{singular}(self):
        res = self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{title_f}": "Hello", "{detail_f}": "World"}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data["{title_f}"], "Hello")
        self.assertEqual(data["{detail_f}"], "World")

    def test_list_{entity}(self):
        self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{title_f}": "A", "{detail_f}": "B"}}),
            content_type="application/json",
        )
        res = self.client.get("/api/{entity}")
        data = json.loads(res.data)
        self.assertIsInstance(data, list, msg="GET must return a plain JSON array")
        self.assertGreater(len(data), 0)

    def test_{singular}_fields(self):
        self.client.post(
            "/api/{entity}",
            data=json.dumps({{"{title_f}": "X", "{detail_f}": "Y"}}),
            content_type="application/json",
        )
        res = self.client.get("/api/{entity}")
        items = json.loads(res.data)
        self.assertIn("{detail_f}", items[0], msg="Item missing {detail_f} field")
        self.assertIn("created_at", items[0], msg="Item missing created_at field")

    def test_types_json(self):
        with open(os.path.join(os.path.dirname(__file__), "types.json")) as f:
            t = json.load(f)
        text = json.dumps(t)
        self.assertIn("created_at", text, msg="types.json must reference created_at")
        self.assertNotIn("timestamp", text, msg="types.json still has stale timestamp")

    def test_frontend_field(self):
        js_path = os.path.join(os.path.dirname(__file__), "static", "app.js")
        with open(js_path) as f:
            content = f.read()
        self.assertIn("{detail_f}", content, msg="app.js must reference {detail_f}")
        self.assertNotIn(".description", content, msg="app.js still references .description")


if __name__ == "__main__":
    unittest.main()
'''
