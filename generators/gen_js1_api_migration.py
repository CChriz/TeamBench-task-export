"""
Parameterized generator for JS1: Express v4 -> v5 API Migration.

Each seed produces:
  - Different API resource name (tasks/users/products/orders/messages)
  - Different field names in the resource (title/description vary per seed)
  - Different port number
  - Different regex route parameter name for /user/:id route
  - Same 5 breaking-change TYPES but specific route/field/variable names change

The 5 breaking changes are always:
  1. req.param() removed — must use req.params.X / req.query.X / req.body.X
  2. res.json(data, status) signature removed — must use res.status(N).json(data)
  3. app.del() alias removed — must use app.delete()
  4. Inline regex constraint in route path removed — must use plain :param
  5. Error handler must explicitly set status code
  6. package.json must target express ^5
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Resource configurations: (resource, singular, field1, field2)
RESOURCE_CONFIGS = [
    ("tasks",    "task",    "title",       "description"),
    ("users",    "user",    "username",    "email"),
    ("products", "product", "name",        "price"),
    ("orders",   "order",   "item",        "quantity"),
    ("messages", "message", "subject",     "body"),
    ("events",   "event",   "title",       "date"),
    ("items",    "item",    "label",       "value"),
]

# Port options
PORTS = [3000, 3001, 4000, 8000, 8080, 9000]

# Regex parameter names for the /user/:id(\\d+) route variant
USER_PARAM_NAMES = ["userId", "uid", "accountId", "memberId", "profileId"]


class Generator(TaskGenerator):
    task_id = "JS1_api_migration"
    domain = "javascript"
    difficulty = "medium"
    languages = ["javascript"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        res_cfg = rng.choice(RESOURCE_CONFIGS)
        resource, singular, field1, field2 = res_cfg

        port = rng.choice(PORTS)
        param_name = rng.choice(USER_PARAM_NAMES)

        server_js = self._gen_server_js(resource, singular, field1, field2, port, param_name)
        test_js = self._gen_test_js(resource, singular, field1, field2, port)
        package_json = self._gen_package_json(resource)

        workspace_files = {
            "server.js": server_js,
            "test/api.test.js": test_js,
            "package.json": package_json,
        }

        expected = {
            "resource": resource,
            "singular": singular,
            "field1": field1,
            "field2": field2,
            "port": port,
            "param_name": param_name,
            "express_version": "^5",
            "breaking_changes": [
                "req.param() removed — replaced with req.params.id / req.query.X",
                "res.json(data, status) removed — replaced with res.status(N).json(data)",
                "app.del() removed — replaced with app.delete()",
                f"inline regex route /:id(\\\\d+) removed — replaced with /:id plain param",
                "error handler must explicitly call res.status(500)",
            ],
            "checks": [
                "express_not_v5",
                "req_param_not_removed",
                "app_del_not_renamed",
                "res_json_old_signature",
                "server_start_failed",
                "tests_failed",
                "bad_attestation",
            ],
        }

        spec_md = self._gen_spec(resource, singular, field1, field2, port)
        brief_md = self._gen_brief(resource, singular, field1, field2)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── File generators ────────────────────────────────────────────────────

    def _gen_server_js(self, resource: str, singular: str, f1: str, f2: str,
                       port: int, param_name: str) -> str:
        resource_upper = resource.upper()
        return f"""'use strict';

const express = require('express');
const app = express();

app.use(express.json());

// In-memory store
const {resource} = new Map();
let nextId = 1;

// ── GET /{resource} ─────────────────────────────────────────────────────────────────
app.get('/{resource}', (req, res) => {{
  const list = Array.from({resource}.values());
  // v4 pattern: second argument to res.json() sets status code
  res.json(list, 200);
}});

// ── POST /{resource} ────────────────────────────────────────────────────────────────
app.post('/{resource}', (req, res) => {{
  const {{ {f1}, {f2} }} = req.body;
  if (!{f1}) {{
    return res.json({{ error: '{f1} is required' }}, 400);
  }}
  const {singular} = {{ id: nextId++, {f1}, {f2}: {f2} || null }};
  {resource}.set({singular}.id, {singular});
  res.json({singular}, 201);
}});

// ── GET /{resource}/:id ─────────────────────────────────────────────────────────────
app.get('/{resource}/:id', (req, res) => {{
  // v4 pattern: req.param() searches params, query, and body
  const id = parseInt(req.param('id'), 10);
  const {singular} = {resource}.get(id);
  if (!{singular}) {{
    return res.json({{ error: 'not found' }}, 404);
  }}
  res.json({singular}, 200);
}});

// ── PUT /{resource}/:id ─────────────────────────────────────────────────────────────
app.put('/{resource}/:id', (req, res) => {{
  const id = parseInt(req.param('id'), 10);
  const {singular} = {resource}.get(id);
  if (!{singular}) {{
    return res.json({{ error: 'not found' }}, 404);
  }}
  const {{ {f1}, {f2} }} = req.body;
  if ({f1} !== undefined) {singular}.{f1} = {f1};
  if ({f2} !== undefined) {singular}.{f2} = {f2};
  {resource}.set(id, {singular});
  res.json({singular}, 200);
}});

// ── DELETE /{resource}/:id ──────────────────────────────────────────────────────────
// v4 pattern: app.del() was an alias for app.delete()
app.del('/{resource}/:id', (req, res) => {{
  const id = parseInt(req.param('id'), 10);
  if (!{resource}.has(id)) {{
    return res.json({{ error: 'not found' }}, 404);
  }}
  {resource}.delete(id);
  res.status(204).send();
}});

// ── GET /profile/:{param_name} ──────────────────────────────────────────────────────
// v4 pattern: inline regex constraint on route parameter
app.get('/profile/:{param_name}(\\\\d+)', (req, res) => {{
  const id = req.param('{param_name}');
  res.json({{ {param_name}: id, display: 'Profile ' + id }}, 200);
}});

// ── Centralised error handler ──────────────────────────────────────────────────
// v4 pattern: error handler without explicit res.status() call
// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {{
  console.error(err.stack);
  res.json({{ error: err.message || 'Internal Server Error' }});
}});

// ── Start ──────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || {port};
app.listen(PORT, () => {{
  console.log('{resource_upper} API listening on port ' + PORT);
}});

module.exports = app;
"""

    def _gen_test_js(self, resource: str, singular: str, f1: str, f2: str, port: int) -> str:
        resource_upper = resource.upper()
        # Sample values for test assertions
        f1_val = "Test item"
        f2_val = "sample"
        f1_updated = "Updated item"
        f2_updated = "updated"
        return f"""'use strict';

/**
 * api.test.js — Integration tests for the {resource_upper} API.
 *
 * Tests are written against observable HTTP behaviour only (status codes +
 * JSON body shape), so they pass with a correctly-migrated Express v5 server
 * and would also pass with a correctly-written Express v4 server.
 *
 * Run: node test/api.test.js
 * Exit 0 on all pass, exit 1 on any failure.
 */

const http = require('http');
const {{ spawn }} = require('child_process');
const path = require('path');
const assert = require('assert');

const PORT = {port};
const BASE = `http://localhost:${{PORT}}`;

// ── Helpers ────────────────────────────────────────────────────────────────────

function request(method, urlPath, body) {{
  return new Promise((resolve, reject) => {{
    const payload = body ? JSON.stringify(body) : null;
    const options = {{
      hostname: 'localhost',
      port: PORT,
      path: urlPath,
      method,
      headers: {{
        'Content-Type': 'application/json',
        ...(payload ? {{ 'Content-Length': Buffer.byteLength(payload) }} : {{}}),
      }},
    }};
    const req = http.request(options, (res) => {{
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {{
        let parsed = null;
        try {{ parsed = data.length ? JSON.parse(data) : null; }} catch (_) {{}}
        resolve({{ status: res.statusCode, body: parsed, raw: data }});
      }});
    }});
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  }});
}}

function sleep(ms) {{
  return new Promise((r) => setTimeout(r, ms));
}}

// ── Test runner ────────────────────────────────────────────────────────────────

const results = [];

async function test(name, fn) {{
  try {{
    await fn();
    results.push({{ name, pass: true }});
    console.log(`  PASS  ${{name}}`);
  }} catch (err) {{
    results.push({{ name, pass: false, error: err.message }});
    console.log(`  FAIL  ${{name}}`);
    console.log(`        ${{err.message}}`);
  }}
}}

// ── Tests ──────────────────────────────────────────────────────────────────────

async function runTests() {{
  let createdId;

  // 1. GET /{resource} returns 200 and a JSON array (possibly empty)
  await test('GET /{resource} returns 200 with array', async () => {{
    const res = await request('GET', '/{resource}');
    assert.strictEqual(res.status, 200, `expected 200, got ${{res.status}}`);
    assert.ok(Array.isArray(res.body), `expected array, got ${{JSON.stringify(res.body)}}`);
  }});

  // 2. POST /{resource} creates a {singular} and returns 201
  await test('POST /{resource} creates a {singular} (201)', async () => {{
    const res = await request('POST', '/{resource}', {{ {f1}: '{f1_val}', {f2}: '{f2_val}' }});
    assert.strictEqual(res.status, 201, `expected 201, got ${{res.status}}`);
    assert.ok(res.body && typeof res.body.id === 'number', 'expected body.id to be a number');
    assert.strictEqual(res.body.{f1}, '{f1_val}', '{f1} mismatch');
    createdId = res.body.id;
  }});

  // 3. GET /{resource}/:id returns the created {singular}
  await test('GET /{resource}/:id returns the created {singular} (200)', async () => {{
    assert.ok(createdId !== undefined, 'createdId must be set by previous test');
    const res = await request('GET', `/{resource}/${{createdId}}`);
    assert.strictEqual(res.status, 200, `expected 200, got ${{res.status}}`);
    assert.strictEqual(res.body.id, createdId, 'id mismatch');
    assert.strictEqual(res.body.{f1}, '{f1_val}', '{f1} mismatch');
  }});

  // 4. PUT /{resource}/:id updates the {singular} and returns 200
  await test('PUT /{resource}/:id updates the {singular} (200)', async () => {{
    assert.ok(createdId !== undefined, 'createdId must be set by previous test');
    const res = await request('PUT', `/{resource}/${{createdId}}`, {{ {f1}: '{f1_updated}', {f2}: '{f2_updated}' }});
    assert.strictEqual(res.status, 200, `expected 200, got ${{res.status}}`);
    assert.strictEqual(res.body.{f1}, '{f1_updated}', '{f1} should be updated');
    assert.strictEqual(res.body.id, createdId, 'id mismatch');
  }});

  // 5. DELETE /{resource}/:id removes the {singular} and returns 204
  await test('DELETE /{resource}/:id removes the {singular} (204)', async () => {{
    assert.ok(createdId !== undefined, 'createdId must be set by previous test');
    const res = await request('DELETE', `/{resource}/${{createdId}}`);
    assert.strictEqual(res.status, 204, `expected 204, got ${{res.status}}`);
  }});
}}

// ── Main ───────────────────────────────────────────────────────────────────────

(async () => {{
  const serverPath = path.resolve(__dirname, '..', 'server.js');

  // Start server subprocess
  const server = spawn(process.execPath, [serverPath], {{
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {{ ...process.env, PORT: String(PORT) }},
  }});

  let startupOutput = '';
  server.stdout.on('data', (d) => (startupOutput += d));
  server.stderr.on('data', (d) => (startupOutput += d));

  // Wait for server to be ready
  let ready = false;
  for (let i = 0; i < 20; i++) {{
    await sleep(300);
    try {{
      await request('GET', '/{resource}');
      ready = true;
      break;
    }} catch (_) {{}}
  }}

  if (!ready) {{
    console.error('Server did not start within 6 s.');
    console.error(startupOutput);
    server.kill();
    process.exit(1);
  }}

  try {{
    await runTests();
  }} finally {{
    server.kill();
  }}

  const passed = results.filter((r) => r.pass).length;
  const total = results.length;
  console.log(`\\n${{passed}}/${{total}} tests passed`);

  if (passed !== total) {{
    process.exit(1);
  }}
}})();
"""

    def _gen_package_json(self, resource: str) -> str:
        return f"""{{
  "name": "{resource}-api",
  "version": "1.0.0",
  "description": "{resource.capitalize()} management REST API",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "test": "node test/api.test.js"
  }},
  "dependencies": {{
    "express": "^4.18.2"
  }}
}}
"""

    def _gen_spec(self, resource: str, singular: str, f1: str, f2: str, port: int) -> str:
        resource_cap = resource.capitalize()
        return f"""# JS1 — API Migration (Planner Specification)

## Overview

The workspace contains an Express v4 application that manages `{resource}` and must be migrated to Express v5. Express v5 introduced several breaking changes that make the current code incompatible. The planner must identify all affected patterns and communicate the necessary changes to the executor.

---

## Breaking Changes That Must Be Fixed

### 1. Removed convenience method for accessing request parameters

Express v4 provided `req.param()` which searched `params`, `body`, and `query` in order. This method was removed in Express v5. Code that uses it must be rewritten to access the appropriate specific source directly (e.g. `req.params.id` for route parameters).

### 2. Changed signature for JSON responses with status codes

Express v4 accepted a status code as a second argument to `res.json()`. Express v5 removed this overload. Status codes must now be set through the chained `.status()` method before calling `.json()`.

### 3. Removed legacy alias for the DELETE route registration method

Express v4 provided `app.del()` as a compatibility alias for `app.delete()`. Express v5 removed this alias. Only `app.delete()` is valid.

### 4. Removed inline regex constraint syntax in route paths

Express v4 allowed inline regular expression constraints appended to route parameter names (e.g. `/:id(\\d+)`). Express v5 no longer supports this syntax. Route paths must use plain parameter names.

### 5. Error handler must explicitly set HTTP status

Express v5 requires error-handling middleware to explicitly set the response status code. Handlers that rely on an implicit default must call `.status()` before sending a response.

### 6. Package version must target Express v5

The `package.json` dependency pin must be updated to install Express v5 (e.g. `"express": "^5"`).

---

## File Map

| File | What needs to change |
|---|---|
| `package.json` | Express version pin must target v5 |
| `server.js` | All five code patterns above must be fixed |
| `test/api.test.js` | **Do not modify** — tests pass once the server behaves correctly |

---

## Test Suite Reference

`test/api.test.js` runs five tests:

| # | Test | Expected |
|---|---|---|
| 1 | `GET /{resource}` | 200, JSON array |
| 2 | `POST /{resource}` | 201, JSON {singular} object |
| 3 | `GET /{resource}/:id` | 200, same {singular} |
| 4 | `PUT /{resource}/:id` | 200, updated {singular} |
| 5 | `DELETE /{resource}/:id` | 204, empty body |

All five tests must exit with code `0`.

---

## Deliverables

- `package.json` updated with Express v5 version pin
- `server.js` with all breaking-change patterns corrected
- All 5 tests pass with exit code `0`
- `attestation.json` created with `{{"verdict": "pass"}}` once all tests pass
"""

    def _gen_brief(self, resource: str, singular: str, f1: str, f2: str) -> str:
        return f"""# JS1: API Migration (Brief)

Migrate an Express v4 `{resource}` API to Express v5.
Express v5 removed several methods and changed some signatures.
All 5 integration tests in `test/api.test.js` must pass.

Run: `node test/api.test.js`

Files to modify:
- `package.json` — update express version to v5
- `server.js` — fix all v4-to-v5 breaking changes

Do NOT modify `test/api.test.js`.
"""
