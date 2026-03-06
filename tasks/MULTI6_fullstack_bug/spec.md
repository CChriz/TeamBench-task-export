# MULTI6: Fullstack Bug Fix — Full Specification (Planner Only)

## Overview

A web application with a Python Flask backend and a JavaScript frontend that communicate via a JSON REST API. The application manages a collection of items. There are **3 bugs** spread across the backend, frontend, and a shared type definition file. All bugs must be fixed so that `python3 test_app.py` passes all tests.

---

## Application Architecture

```
workspace/
  app.py               # Flask backend API
  static/
    app.js             # Frontend JavaScript
    index.html         # Frontend HTML
  types.json           # Shared API type contract
  test_app.py          # Test suite (do not modify)
```

The backend uses an in-memory SQLite database. The frontend communicates with the backend via fetch calls. The `types.json` file documents the expected API response shapes.

---

## Bug Inventory

### Bug 1: Backend returns wrong JSON shape — `app.py`
- **Symptom**: The GET endpoint wraps the list of items inside a `{"data": [...]}` envelope, but the frontend and tests expect a plain JSON array `[...]`
- **Expected behavior**: The GET endpoint must return a plain JSON array of items, not wrapped in an envelope object
- **Constraint**: The POST endpoint correctly returns a single item object (not an array) — do not change the POST response format

### Bug 2: Frontend parses wrong field — `static/app.js`
- **Symptom**: The frontend tries to read `item.description` from each API response object, but the backend uses the field name specified in `types.json`
- **Expected behavior**: The frontend must read the correct field name that the backend actually returns
- **Constraint**: Check `types.json` for the canonical field name — the frontend must match it

### Bug 3: Shared type definition is stale — `types.json`
- **Symptom**: The `types.json` file lists a `timestamp` field in the item schema, but the backend actually returns a field called `created_at`
- **Expected behavior**: Update `types.json` so the schema matches what the backend actually returns (`created_at` not `timestamp`)

---

## Expected Outcome

After all 3 fixes are applied:

```
python3 test_app.py
```

All tests pass:
1. `test_create_item` — POST returns 201 with correct fields
2. `test_list_items` — GET returns a plain JSON array
3. `test_item_fields` — each item has the correct field names
4. `test_types_json` — types.json matches actual API response shape
5. `test_frontend_field` — app.js references the correct field name

---

## Constraints

- Do not modify `test_app.py`
- Only `flask` is available as an external dependency (plus Python stdlib)
- The SQLite database is in-memory — no persistent storage needed
