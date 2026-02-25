# MULTI1: Fullstack Bug Fix — Full Specification (Planner Only)

## Overview

A simple note-taking web application built with Flask (Python backend), vanilla JS/HTML (frontend), and a bash deploy script. The app has **6 bugs** spread across all 3 layers. All bugs must be fixed so that `python3 test_app.py` passes all 6 tests.

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

The backend uses an in-memory SQLite database (created fresh on app startup). The frontend communicates with the backend via a JSON REST API.

---

## Bug Inventory

### Backend Bugs — `app.py`

**Bug 1: Note creation endpoint does not read the request body**
- **Symptom**: Every note is created with null title and content, regardless of what the client sends
- **Expected behavior**: The POST endpoint must parse the JSON request body and use the `title` and `content` values from it
- **Constraint**: Flask provides two separate ways to access request data — URL query parameters and the parsed JSON body. The endpoint is currently using the wrong one.

**Bug 2: Notes are returned in the wrong order**
- **Symptom**: The GET /api/notes endpoint returns notes oldest-first
- **Expected behavior**: Notes must be returned newest-first so that the most recently created note appears at the top of the list

**Bug 3: Delete endpoint fails at runtime**
- **Symptom**: Any attempt to delete a note causes a server-side error; the delete operation never succeeds
- **Expected behavior**: The DELETE endpoint must correctly identify the note to delete using the ID from the route and remove it from the database

---

### Frontend Bugs — `static/app.js`

**Bug 4: Note creation requests are rejected by the backend**
- **Symptom**: Even after the backend bug is fixed, note creation still fails because Flask does not parse the request body
- **Expected behavior**: The fetch request that creates a note must declare the correct MIME type so that Flask recognizes and parses the JSON body
- **Constraint**: Flask's JSON body parsing is only activated when the request declares `application/json` as its Content-Type

**Bug 5: Delete requests are sent to the wrong URL**
- **Symptom**: Clicking delete sends a request to `/api/notes/undefined` instead of the correct note URL
- **Expected behavior**: The delete fetch request URL must include the actual numeric ID of the note being deleted

---

### Deploy Script Bug — `deploy.sh`

**Bug 6: Deploy script references the wrong application file**
- **Symptom**: Running the deploy script causes Flask to fail on startup because it cannot find the application module
- **Expected behavior**: The `FLASK_APP` environment variable in `deploy.sh` must point to the actual application file

---

## Expected Outcome

After all 6 fixes are applied:

```
python3 test_app.py
```

Should produce output like:
```
......
----------------------------------------------------------------------
Ran 6 tests in 0.XXXs

OK
```

All 6 tests pass:
1. `test_create_note` — POST creates a note (201 response)
2. `test_get_notes` — GET returns a JSON list
3. `test_notes_sorted` — newest note appears first
4. `test_delete_note` — DELETE removes a note (200 response)
5. `test_deploy_script_env` — deploy.sh contains correct `FLASK_APP` value
6. `test_frontend_content_type` — app.js declares `application/json`

---

## Constraints

- Do not modify `test_app.py`
- Only `flask` is available as an external dependency (plus Python stdlib: `sqlite3`, `json`, `unittest`)
- The SQLite database is in-memory (`:memory:`) — no persistent storage needed
