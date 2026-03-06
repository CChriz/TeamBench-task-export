# MULTI7: Polyglot Test — Full Specification (Planner Only)

## Overview

A Python application with a bash deployment script and SQL migration files. The system has **3 bugs** across the three languages. All bugs must be fixed so that `python3 test_app.py` passes all tests.

---

## Application Architecture

```
workspace/
  app.py               # Python application with config loader
  deploy.sh            # Bash deployment script
  migrations/
    001_create.sql      # Initial schema migration
    002_add_fk.sql      # Foreign key migration (buggy)
  config.env            # Environment configuration
  test_app.py           # Test suite (do not modify)
```

The Python app loads configuration from environment variables, the bash script sets up the environment and runs migrations, and the SQL migrations create the database schema.

---

## Bug Inventory

### Bug 1: Bash script uses wrong environment variable names — `deploy.sh`
- **Symptom**: The deployment script exports `DB_HOST` and `DB_PORT`, but the Python config loader reads `DATABASE_HOST` and `DATABASE_PORT`
- **Expected behavior**: The deployment script must export variable names that match what the Python application expects
- **Constraint**: Fix the deploy script, not the Python config loader — the Python naming convention is the standard

### Bug 2: SQL migration has wrong foreign key reference — `migrations/002_add_fk.sql`
- **Symptom**: The foreign key in the orders table references `users(user_id)` but the users table primary key column is named `id`
- **Expected behavior**: The foreign key must reference the correct column name in the users table
- **Constraint**: Do not rename the users table primary key — fix the FK reference

### Bug 3: Python config loader has wrong default path — `app.py`
- **Symptom**: The config loader tries to read from `/etc/app/config.env` by default, but the config file is at `./config.env` (relative to workspace)
- **Expected behavior**: The config loader must default to `./config.env` when no path override is provided

---

## Expected Outcome

After all 3 fixes:
```
python3 test_app.py
```
All tests pass.

---

## Constraints

- Do not modify `test_app.py`
- The Python config loader naming convention (`DATABASE_HOST`, `DATABASE_PORT`) is the standard — do not change it
- The users table primary key column is `id` — do not rename it
