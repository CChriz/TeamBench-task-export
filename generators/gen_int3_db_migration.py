"""
Parameterized generator for INT3: Database Schema Migration Fix.

Each seed produces a different schema domain with 4 migration bugs:
  1. FK constraint created before referenced table exists (wrong order)
  2. NOT NULL column added without DEFAULT (breaks existing rows)
  3. Index name collides with existing index in prior migration
  4. Rollback drops the wrong column
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

SCHEMAS = [
    {
        "domain": "ecommerce",
        "base_table": "customers",
        "base_cols": "id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE",
        "ref_table": "orders",
        "ref_cols_pre": "id INTEGER PRIMARY KEY, total REAL NOT NULL, status TEXT DEFAULT 'pending'",
        "new_table": "order_items",
        "new_cols": "id INTEGER PRIMARY KEY, order_id INTEGER, product_name TEXT, quantity INTEGER",
        "fk_col": "order_id",
        "fk_ref": "orders(id)",
        "new_col_name": "loyalty_tier",
        "new_col_type": "TEXT",
        "new_col_default": "'bronze'",
        "wrong_drop_col": "email",
        "correct_drop_col": "loyalty_tier",
        "idx_name": "idx_customers_email",
        "idx_col": "email",
        "idx_table": "customers",
    },
    {
        "domain": "hr",
        "base_table": "departments",
        "base_cols": "id INTEGER PRIMARY KEY, name TEXT NOT NULL, budget REAL",
        "ref_table": "employees",
        "ref_cols_pre": "id INTEGER PRIMARY KEY, name TEXT NOT NULL, salary REAL DEFAULT 0",
        "new_table": "projects",
        "new_cols": "id INTEGER PRIMARY KEY, employee_id INTEGER, title TEXT, deadline TEXT",
        "fk_col": "employee_id",
        "fk_ref": "employees(id)",
        "new_col_name": "department_head",
        "new_col_type": "INTEGER",
        "new_col_default": "0",
        "wrong_drop_col": "budget",
        "correct_drop_col": "department_head",
        "idx_name": "idx_departments_name",
        "idx_col": "name",
        "idx_table": "departments",
    },
    {
        "domain": "inventory",
        "base_table": "warehouses",
        "base_cols": "id INTEGER PRIMARY KEY, location TEXT NOT NULL, capacity INTEGER",
        "ref_table": "products",
        "ref_cols_pre": "id INTEGER PRIMARY KEY, sku TEXT UNIQUE, price REAL DEFAULT 0.0",
        "new_table": "shipments",
        "new_cols": "id INTEGER PRIMARY KEY, product_id INTEGER, warehouse_id INTEGER, quantity INTEGER",
        "fk_col": "product_id",
        "fk_ref": "products(id)",
        "new_col_name": "zone_code",
        "new_col_type": "TEXT",
        "new_col_default": "'A1'",
        "wrong_drop_col": "capacity",
        "correct_drop_col": "zone_code",
        "idx_name": "idx_warehouses_location",
        "idx_col": "location",
        "idx_table": "warehouses",
    },
]


class Generator(TaskGenerator):
    task_id = "INT3_db_migration"
    domain = "integration"
    difficulty = "hard"
    languages = ["python", "sql"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        s = SCHEMAS[seed % len(SCHEMAS)]

        workspace_files = self._make_workspace(s, rng)

        expected = {
            "domain": s["domain"],
            "bugs": [
                "fk_before_referenced_table",
                "not_null_without_default",
                "index_name_collision",
                "rollback_drops_wrong_column",
            ],
            "bug_count": 4,
            "fk_table": s["new_table"],
            "fk_ref": s["fk_ref"],
            "new_col_name": s["new_col_name"],
            "new_col_default": s["new_col_default"],
            "correct_drop_col": s["correct_drop_col"],
            "wrong_drop_col": s["wrong_drop_col"],
            "colliding_index": s["idx_name"],
            "base_table": s["base_table"],
            "ref_table": s["ref_table"],
            "new_table": s["new_table"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._spec(s),
            brief_md=self._brief(s),
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_workspace(self, s: dict, rng: SeededRandom) -> dict[str, str]:
        files: dict[str, str] = {}
        files["migrations/__init__.py"] = ""
        files["migrations/001_initial.py"] = self._migration_001(s)
        files["migrations/002_add_features.py"] = self._migration_002(s)
        files["migrations/003_indexes.py"] = self._migration_003(s)
        files["migrate.py"] = self._migrate_runner(s)
        files["schema_design.md"] = self._schema_design(s)
        files["tests/__init__.py"] = ""
        files["tests/test_migrations.py"] = self._test_migrations(s)
        return files

    def _migration_001(self, s: dict) -> str:
        return f'''\
"""Migration 001: Create initial tables for {s["domain"]} schema."""
import sqlite3


def up(db_path: str) -> None:
    """Apply migration: create base tables."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS {s["base_table"]} (
            {s["base_cols"]}
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS {s["ref_table"]} (
            {s["ref_cols_pre"]}
        )
    """)
    # Create initial index on base table
    conn.execute("""
        CREATE INDEX IF NOT EXISTS {s["idx_name"]}
        ON {s["idx_table"]}({s["idx_col"]})
    """)
    conn.commit()
    conn.close()


def down(db_path: str) -> None:
    """Rollback migration: drop base tables."""
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS {s["ref_table"]}")
    conn.execute("DROP TABLE IF EXISTS {s["base_table"]}")
    conn.commit()
    conn.close()
'''

    def _migration_002(self, s: dict) -> str:
        # BUG1: FK to ref_table but also a spurious FK to base_table(id) — wrong
        # BUG2: NOT NULL column added without DEFAULT
        # BUG4: down() drops wrong column
        return f'''\
"""Migration 002: Add features to {s["domain"]} schema.

Bugs in this file:
  BUG1: {s["new_table"]} has a spurious FK referencing {s["base_table"]}(id) which
        does not make sense and will fail if FK enforcement is strict.
  BUG2: ALTER TABLE adds {s["new_col_name"]} as NOT NULL without DEFAULT,
        which breaks any existing rows in {s["base_table"]}.
  BUG4: The down() rollback drops {s["wrong_drop_col"]} instead of {s["correct_drop_col"]}.
"""
import sqlite3


def up(db_path: str) -> None:
    """Apply migration: add new table and alter base table."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # BUG1: Creates {s["new_table"]} with a FK to {s["base_table"]}(id) which is wrong.
    # Only the FK to {s["ref_table"]} is correct.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS {s["new_table"]} (
            {s["new_cols"]},
            FOREIGN KEY ({s["fk_col"]}) REFERENCES {s["fk_ref"]},
            FOREIGN KEY (id) REFERENCES {s["base_table"]}(id)
        )
    """)

    # BUG2: NOT NULL without DEFAULT — breaks existing rows in {s["base_table"]}
    conn.execute("""
        ALTER TABLE {s["base_table"]}
        ADD COLUMN {s["new_col_name"]} {s["new_col_type"]} NOT NULL
    """)

    conn.commit()
    conn.close()


def down(db_path: str) -> None:
    """Rollback migration: undo feature additions."""
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS {s["new_table"]}")

    # BUG4: This drops {s["wrong_drop_col"]} — should drop {s["correct_drop_col"]}
    # Reconstruct {s["base_table"]} without the wrong column
    conn.execute("""
        CREATE TABLE {s["base_table"]}_bak AS
        SELECT * FROM {s["base_table"]}
    """)
    conn.execute("DROP TABLE {s["base_table"]}")
    # Recreate from backup missing the correct column that was ADDED (loyalty_tier etc.)
    # but this code omits {s["wrong_drop_col"]} instead — data corruption
    conn.execute("""
        CREATE TABLE {s["base_table"]} AS
        SELECT * FROM {s["base_table"]}_bak
    """)
    conn.execute("DROP TABLE {s["base_table"]}_bak")

    conn.commit()
    conn.close()
'''

    def _migration_003(self, s: dict) -> str:
        # BUG3: idx_name collides with one created in 001
        return f'''\
"""Migration 003: Add performance indexes for {s["domain"]} schema.

Bug in this file:
  BUG3: {s["idx_name"]} was already created in migration 001.
        This CREATE INDEX (without IF NOT EXISTS) will raise an error.
"""
import sqlite3


def up(db_path: str) -> None:
    """Apply migration: add indexes."""
    conn = sqlite3.connect(db_path)

    # BUG3: {s["idx_name"]} already exists from 001_initial.py — name collision
    conn.execute("""
        CREATE INDEX {s["idx_name"]}
        ON {s["idx_table"]}({s["idx_col"]})
    """)

    # This secondary index is fine
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_{s["new_table"]}_{s["fk_col"]}
        ON {s["new_table"]}({s["fk_col"]})
    """)

    conn.commit()
    conn.close()


def down(db_path: str) -> None:
    """Rollback migration: drop indexes added here."""
    conn = sqlite3.connect(db_path)
    # Only drop the index added by THIS migration (the secondary one)
    conn.execute("DROP INDEX IF EXISTS idx_{s["new_table"]}_{s["fk_col"]}")
    conn.commit()
    conn.close()
'''

    def _migrate_runner(self, s: dict) -> str:
        return f'''\
"""Migration runner for {s["domain"]} schema. DO NOT MODIFY."""
import importlib
import os
import sys

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
DB_PATH = os.environ.get("MIGRATION_DB", "{s["domain"]}.db")


def get_migrations():
    """Discover and sort migration modules."""
    migrations = []
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if fname.endswith(".py") and not fname.startswith("__"):
            mod_name = f"migrations.{{fname[:-3]}}"
            mod = importlib.import_module(mod_name)
            migrations.append((fname, mod))
    return migrations


def run_up(db_path: str = None) -> None:
    """Run all migrations up."""
    path = db_path or DB_PATH
    for fname, mod in get_migrations():
        print(f"Applying {{fname}}...")
        mod.up(path)
    print("All migrations applied.")


def run_down(db_path: str = None) -> None:
    """Run all migrations down in reverse order."""
    path = db_path or DB_PATH
    for fname, mod in reversed(get_migrations()):
        print(f"Rolling back {{fname}}...")
        mod.down(path)
    print("All migrations rolled back.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [up|down]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "up":
        run_up()
    elif cmd == "down":
        run_down()
    else:
        print(f"Unknown command: {{cmd}}")
        sys.exit(1)
'''

    def _schema_design(self, s: dict) -> str:
        return f'''\
# Schema Design: {s["domain"]}

## Tables

### {s["base_table"]}
```sql
{s["base_cols"]},
{s["new_col_name"]} {s["new_col_type"]} NOT NULL DEFAULT {s["new_col_default"]}
```
Note: `{s["new_col_name"]}` must have DEFAULT {s["new_col_default"]} so existing rows are not broken.

### {s["ref_table"]}
```sql
{s["ref_cols_pre"]}
```

### {s["new_table"]}
```sql
{s["new_cols"]},
FOREIGN KEY ({s["fk_col"]}) REFERENCES {s["fk_ref"]}
```
Note: Only the FK to `{s["fk_ref"]}` is required. No FK to `{s["base_table"]}(id)`.

## Indexes
- `{s["idx_name"]}` on `{s["idx_table"]}({s["idx_col"]})` — created in migration 001
- `idx_{s["new_table"]}_{s["fk_col"]}` on `{s["new_table"]}({s["fk_col"]})` — created in migration 003

Each index must have a unique name. Migration 003 must NOT recreate `{s["idx_name"]}`.

## Rollback Notes
- `002_add_features.down()` must drop `{s["correct_drop_col"]}` (the column that was ADDED).
  It must NOT drop `{s["wrong_drop_col"]}`.
'''

    def _test_migrations(self, s: dict) -> str:
        return f'''\
"""Tests for {s["domain"]} schema migrations."""
import os
import sqlite3
import pytest

DB_PATH = "/tmp/test_int3_{s["domain"]}.db"


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def test_migrate_up():
    """All migrations apply without error."""
    from migrate import run_up
    run_up(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    tables = {{r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type=\'table\'"
    ).fetchall()}}
    conn.close()
    assert "{s["base_table"]}" in tables
    assert "{s["ref_table"]}" in tables
    assert "{s["new_table"]}" in tables


def test_migrate_up_then_down():
    """Migrations can be applied then rolled back without error."""
    from migrate import run_up, run_down
    run_up(DB_PATH)
    run_down(DB_PATH)


def test_new_column_has_default():
    """The new column must have a DEFAULT so pre-existing rows are not broken."""
    from migrate import run_up
    # Seed a row into base table before migration 002
    conn = sqlite3.connect(db_path := DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    # Run 001 only (create base tables)
    from migrations import _001_initial as m1
    m1.up(DB_PATH)
    conn2 = sqlite3.connect(DB_PATH)
    # Insert a row without the new column
    conn2.execute("INSERT INTO {s["base_table"]} VALUES (1, 'test', 'x@y.com')")
    conn2.commit()
    conn2.close()
    # Now run 002 — must not fail due to NOT NULL without DEFAULT
    from migrations import _002_add_features as m2
    m2.up(DB_PATH)


def test_index_names_unique():
    """No two indexes share a name."""
    from migrate import run_up
    run_up(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    indexes = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type=\'index\' AND name NOT LIKE \'sqlite_%\'"
    ).fetchall()]
    conn.close()
    assert len(indexes) == len(set(indexes)), f"Duplicate index names: {{indexes}}"


def test_rollback_drops_correct_column():
    """Rollback of 002 must drop {s["correct_drop_col"]}, not {s["wrong_drop_col"]}."""
    from migrate import run_up, run_down
    run_up(DB_PATH)
    run_down(DB_PATH)
    # After full rollback base table should not exist, but if partial rollback is tested:
    # Re-apply just migration 001 and 002, then roll back 002
    from migrations import _001_initial as m1
    from migrations import _002_add_features as m2
    m1.up(DB_PATH)
    m2.up(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cols_before = {{r[1] for r in conn.execute(
        f"PRAGMA table_info({s["base_table"]})"
    ).fetchall()}}
    conn.close()
    assert "{s["correct_drop_col"]}" in cols_before
    assert "{s["wrong_drop_col"]}" in cols_before
    m2.down(DB_PATH)
    conn2 = sqlite3.connect(DB_PATH)
    cols_after = {{r[1] for r in conn2.execute(
        f"PRAGMA table_info({s["base_table"]})"
    ).fetchall()}}
    conn2.close()
    assert "{s["correct_drop_col"]}" not in cols_after, "down() should have dropped {s["correct_drop_col"]}"
    assert "{s["wrong_drop_col"]}" in cols_after, "down() must NOT drop {s["wrong_drop_col"]}"
'''

    def _spec(self, s: dict) -> str:
        return f"""\
# INT3: Database Schema Migration Fix

## Goal
Fix a database migration system that has 4 bugs preventing successful up/down migration.

## Requirements
1. Fix FK constraint: `migrations/002_add_features.py` creates `{s["new_table"]}` with a spurious FK to `{s["base_table"]}(id)` that does not belong in the schema
2. Fix NOT NULL column: `{s["new_col_name"]}` is added as `NOT NULL` without a `DEFAULT` value — add `DEFAULT {s["new_col_default"]}`
3. Fix index naming: `migrations/003_indexes.py` re-creates `{s["idx_name"]}` which already exists from migration 001 — rename or add `IF NOT EXISTS`
4. Fix rollback: `002_add_features.down()` drops `{s["wrong_drop_col"]}` but must drop `{s["correct_drop_col"]}`
5. Running all migrations up then down must succeed without errors
6. The final schema after up must match `schema_design.md`

## Supporting Documents
- `migrations/001_initial.py` — First migration (creates base tables)
- `migrations/002_add_features.py` — Second migration (has bugs 1, 2, 4)
- `migrations/003_indexes.py` — Third migration (has bug 3)
- `schema_design.md` — Target schema specification
- `migrate.py` — Migration runner (do not modify)
- `tests/test_migrations.py` — Tests that run migrations up and down

## Important
Do NOT modify `migrate.py`. Only fix the migration files.
"""

    def _brief(self, s: dict) -> str:
        return f"""\
# INT3: Database Schema Migration Fix (Brief)

Fix 4 bugs in the {s["domain"]} schema migrations so that `python migrate.py up` and
`python migrate.py down` both succeed without errors.
Run tests: `pytest tests/test_migrations.py`
"""
