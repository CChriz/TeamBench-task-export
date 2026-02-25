# JS1 — API Migration (Planner Specification)

## Overview

The workspace contains an Express v4 application that must be migrated to Express v5. Express v5 introduced several breaking changes that make the current code incompatible. The planner must identify all affected patterns and communicate the necessary changes to the executor.

---

## Breaking Changes That Must Be Fixed

### 1. Removed convenience method for accessing request parameters

Express v4 provided a single method that searched `params`, `body`, and `query` in order. This method was removed in Express v5. Code that relies on it must be rewritten to access the appropriate specific source directly, based on where the value actually comes from in each route.

### 2. Changed signature for JSON responses with status codes

Express v4 accepted a status code as a second argument to the JSON response method. Express v5 removed this overload. Status codes must now be set through the chained status method before the JSON method is called.

### 3. Removed legacy alias for the DELETE route registration method

Express v4 provided a compatibility alias for registering DELETE routes because `delete` was a reserved word in older JavaScript environments. Express v5 removed this alias. Only the standard method name is valid.

### 4. Removed inline regex constraint syntax in route paths

Express v4 allowed inline regular expression constraints to be appended to route parameter names within the path string. Express v5 no longer supports this syntax. Route paths must use plain parameter names; any type or format validation must be performed inside the handler.

### 5. Error handler must explicitly set HTTP status

Express v5 requires error-handling middleware to explicitly set the response status code. Handlers that rely on an implicit default status must be updated to call the status method before sending a response.

### 6. Package version must target Express v5

The `package.json` dependency pin must be updated to install Express v5 rather than v4.

---

## File Map

| File | What needs to change |
|---|---|
| `package.json` | Express version pin must target v5 |
| `server.js` | All five code patterns above must be fixed |
| `test/api.test.js` | **Do not modify** — tests are written against observable HTTP behaviour and pass once the server behaves correctly |

---

## Test Suite Reference

`test/api.test.js` runs five tests via the built-in `http` module:

| # | Test | Expected |
|---|---|---|
| 1 | `GET /tasks` | 200, JSON array |
| 2 | `POST /tasks` | 201, JSON task object |
| 3 | `GET /tasks/:id` | 200, same task |
| 4 | `PUT /tasks/:id` | 200, updated task |
| 5 | `DELETE /tasks/:id` | 204, empty body |

All five tests must exit the suite with code `0`.

---

## Deliverables

- `package.json` updated with Express v5 version pin
- `server.js` with all breaking-change patterns corrected
- All 5 tests pass with exit code `0`
- `attestation.json` created with `{"verdict": "pass"}` once all tests pass
