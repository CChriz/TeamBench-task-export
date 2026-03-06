"""
Parameterized generator for LH7: Zero-Downtime Database Migration.

Each seed produces:
- A Python app with SQLAlchemy models
- 4 migration scripts in migrations/ that must be reordered for zero-downtime
- The migrations are provided in WRONG ORDER (2,4,1,3)
- Migration 4 is missing a backfill completeness check
- A RUNBOOK.md describing the zero-downtime pattern
- A deploy_config.yaml with blue-green deployment settings

Seed variation:
  - Different table names, column names, model types
  - Different migration content (but same structural pattern)
  - Different old/new column names

TNI driver (Pattern F + A):
  - Brief: "Apply the database migrations for zero-downtime deployment"
  - Spec: Full migration ordering rules + backfill requirements
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized pools ───────────────────────────────────────────────

TABLE_CONFIGS = [
    {
        "table": "users",
        "model": "User",
        "old_col": "full_name",
        "new_col_first": "first_name",
        "new_col_last": "last_name",
        "split_logic": "full_name.split(' ', 1)",
        "col_type": "String(128)",
        "py_type": "str",
    },
    {
        "table": "products",
        "model": "Product",
        "old_col": "price_cents",
        "new_col_first": "price_dollars",
        "new_col_last": "price_currency",
        "split_logic": "(price_cents / 100, 'USD')",
        "col_type": "Numeric(10, 2)",
        "py_type": "float",
    },
    {
        "table": "employees",
        "model": "Employee",
        "old_col": "address",
        "new_col_first": "street",
        "new_col_last": "city",
        "split_logic": "address.rsplit(',', 1)",
        "col_type": "String(256)",
        "py_type": "str",
    },
    {
        "table": "orders",
        "model": "Order",
        "old_col": "shipping_info",
        "new_col_first": "shipping_address",
        "new_col_last": "shipping_method",
        "split_logic": "shipping_info.split('|', 1)",
        "col_type": "String(256)",
        "py_type": "str",
    },
    {
        "table": "articles",
        "model": "Article",
        "old_col": "metadata_blob",
        "new_col_first": "author_name",
        "new_col_last": "category",
        "split_logic": "json.loads(metadata_blob)",
        "col_type": "String(128)",
        "py_type": "str",
    },
]


class Generator(TaskGenerator):
    task_id = "LH7_zero_downtime"
    domain = "long_horizon"
    difficulty = "hard"
    languages = ["python", "sql"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        cfg = TABLE_CONFIGS[seed % len(TABLE_CONFIGS)]

        workspace_files = self._make_workspace(cfg, rng, seed)

        expected = {
            "seed": seed,
            "table": cfg["table"],
            "model": cfg["model"],
            "old_col": cfg["old_col"],
            "new_col_first": cfg["new_col_first"],
            "new_col_last": cfg["new_col_last"],
            "correct_order": [1, 2, 3, 4],
            "provided_order": [2, 4, 1, 3],
            "backfill_check_required": True,
        }

        spec_md = self._generate_spec(cfg)
        brief_md = self._generate_brief(cfg)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_workspace(self, cfg: dict, rng: SeededRandom, seed: int) -> dict:
        files = {}

        table = cfg["table"]
        model = cfg["model"]
        old_col = cfg["old_col"]
        new_first = cfg["new_col_first"]
        new_last = cfg["new_col_last"]
        col_type = cfg["col_type"]
        split_logic = cfg["split_logic"]

        # App with SQLAlchemy models (both old and new columns for transition)
        files["app.py"] = f'''"""Application with {model} model — currently reads from {old_col}."""
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class {model}(Base):
    __tablename__ = "{table}"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {old_col} = Column({col_type}, nullable=False)
    status = Column(String(32), default="active")

    def __repr__(self):
        return f"<{model}(id={{self.id}}, {old_col}={{self.{old_col}}})>"


def get_engine(db_url="sqlite:///app.db"):
    return create_engine(db_url)


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def seed_data(session):
    """Insert sample data for testing."""
    samples = [
        {model}({old_col}="Alice Johnson", status="active"),
        {model}({old_col}="Bob Smith", status="active"),
        {model}({old_col}="Charlie Brown", status="inactive"),
        {model}({old_col}="Diana Prince", status="active"),
        {model}({old_col}="Eve Davis", status="active"),
    ]
    session.add_all(samples)
    session.commit()
    return len(samples)


def read_{table}(session):
    """Current read path — reads from {old_col}."""
    return session.query({model}).all()


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session(engine)
    count = seed_data(session)
    print(f"Seeded {{count}} {table}")
    for record in read_{table}(session):
        print(record)
'''

        # Migration 1 (CORRECT: Step 1 — add new nullable columns)
        mig1 = f'''"""Migration 001: Add new nullable columns {new_first} and {new_last}.

This is the FIRST step in a zero-downtime migration.
New columns MUST be nullable so existing rows are valid.
"""
from sqlalchemy import text


def upgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE {table}
            ADD COLUMN {new_first} VARCHAR(128) NULL
        """))
        conn.execute(text("""
            ALTER TABLE {table}
            ADD COLUMN {new_last} VARCHAR(128) NULL
        """))
        conn.commit()
    print("Migration 001: Added nullable columns {new_first}, {new_last}")


def downgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE {table}
            DROP COLUMN {new_first}
        """))
        conn.execute(text("""
            ALTER TABLE {table}
            DROP COLUMN {new_last}
        """))
        conn.commit()
'''

        # Migration 2 (CORRECT: Step 2 — backfill + dual-write)
        mig2 = f'''"""Migration 002: Backfill new columns from {old_col} and enable dual-write.

This is the SECOND step. Must run AFTER new columns exist.
Backfills existing data and sets up dual-write trigger.
"""
from sqlalchemy import text


def upgrade(engine):
    with engine.connect() as conn:
        # Backfill existing rows
        rows = conn.execute(text("SELECT id, {old_col} FROM {table}")).fetchall()
        for row in rows:
            parts = str(row[1]).split(" ", 1)
            first_val = parts[0] if parts else ""
            last_val = parts[1] if len(parts) > 1 else ""
            conn.execute(text("""
                UPDATE {table}
                SET {new_first} = :first_val, {new_last} = :last_val
                WHERE id = :id
            """), {{"first_val": first_val, "last_val": last_val, "id": row[0]}})
        conn.commit()
    print(f"Migration 002: Backfilled {{len(rows)}} rows")


def downgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE {table} SET {new_first} = NULL, {new_last} = NULL
        """))
        conn.commit()
'''

        # Migration 3 (CORRECT: Step 3 — switch reads to new columns)
        mig3 = f'''"""Migration 003: Switch reads to new columns.

This is the THIRD step. All data MUST be backfilled before this runs.
Application code switches from reading {old_col} to reading {new_first} + {new_last}.
"""
import os
import json


SWITCH_FLAG_FILE = "migration_flags.json"


def upgrade(engine):
    # Set a feature flag to switch read path
    flags = {{}}
    if os.path.exists(SWITCH_FLAG_FILE):
        with open(SWITCH_FLAG_FILE) as f:
            flags = json.load(f)
    flags["read_from_new_columns"] = True
    flags["dual_write_enabled"] = True
    with open(SWITCH_FLAG_FILE, "w") as f:
        json.dump(flags, f, indent=2)
    print("Migration 003: Read path switched to {new_first} + {new_last}")


def downgrade(engine):
    flags = {{}}
    if os.path.exists(SWITCH_FLAG_FILE):
        with open(SWITCH_FLAG_FILE) as f:
            flags = json.load(f)
    flags["read_from_new_columns"] = False
    with open(SWITCH_FLAG_FILE, "w") as f:
        json.dump(flags, f, indent=2)
'''

        # Migration 4 (BUGGY: Step 4 — drops old column WITHOUT checking backfill)
        mig4_buggy = f'''"""Migration 004: Drop old column and add NOT NULL constraints.

This is the FOURTH and final step.
Drops {old_col} and makes new columns NOT NULL.
"""
from sqlalchemy import text


def upgrade(engine):
    with engine.connect() as conn:
        # BUG: Missing backfill completeness check!
        # Should verify no NULL values exist in {new_first}/{new_last}
        # before dropping the old column. Without this check, data loss
        # can occur if migration 002 failed partially.

        # Drop old column
        conn.execute(text("""
            CREATE TABLE {table}_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {new_first} VARCHAR(128) NOT NULL,
                {new_last} VARCHAR(128) NOT NULL,
                status VARCHAR(32) DEFAULT 'active'
            )
        """))
        conn.execute(text("""
            INSERT INTO {table}_new (id, {new_first}, {new_last}, status)
            SELECT id, {new_first}, {new_last}, status
            FROM {table}
        """))
        conn.execute(text("DROP TABLE {table}"))
        conn.execute(text("ALTER TABLE {table}_new RENAME TO {table}"))
        conn.commit()
    print("Migration 004: Dropped {old_col}, added NOT NULL constraints")


def downgrade(engine):
    raise RuntimeError("Migration 004 is irreversible — cannot restore {old_col}")
'''

        # Place migrations in WRONG ORDER: 2, 4, 1, 3
        # The filenames suggest an ordering but the actual content is scrambled
        files["migrations/__init__.py"] = ""
        files["migrations/001_backfill_dual_write.py"] = mig2      # Actually step 2
        files["migrations/002_drop_old_column.py"] = mig4_buggy     # Actually step 4
        files["migrations/003_add_new_columns.py"] = mig1           # Actually step 1
        files["migrations/004_switch_reads.py"] = mig3              # Actually step 3

        # run_migrations.py that executes in filename order (wrong!)
        files["run_migrations.py"] = f'''"""Run all migrations in order.

Executes migration files from migrations/ in filename sort order.
"""
import importlib
import os
import sys

from app import get_engine, Base


def run_all():
    engine = get_engine()
    Base.metadata.create_all(engine)

    mig_dir = "migrations"
    scripts = sorted(
        f for f in os.listdir(mig_dir)
        if f.endswith(".py") and f != "__init__.py"
    )

    print(f"Running {{len(scripts)}} migrations...")
    for script in scripts:
        mod_name = f"migrations.{{script[:-3]}}"
        print(f"  Running {{script}}...")
        mod = importlib.import_module(mod_name)
        mod.upgrade(engine)
        print(f"  Done: {{script}}")

    print("All migrations complete.")


if __name__ == "__main__":
    run_all()
'''

        # RUNBOOK
        files["RUNBOOK.md"] = f"""# Zero-Downtime Migration Runbook

## Overview
Migrating `{table}.{old_col}` -> `{table}.{new_first}` + `{table}.{new_last}`

## Correct Migration Order for Zero Downtime

The four steps MUST be executed in this exact sequence:

### Step 1: Add New Nullable Columns
- Add `{new_first}` and `{new_last}` as nullable columns
- This is backwards-compatible: old code ignores new columns
- **No downtime**: existing reads/writes unaffected

### Step 2: Backfill + Enable Dual-Write
- Backfill all existing rows: split `{old_col}` into `{new_first}` and `{new_last}`
- Enable dual-write: new writes go to both old and new columns
- **No downtime**: old code still reads `{old_col}`
- **CRITICAL**: Verify 100% backfill completeness before proceeding

### Step 3: Switch Reads to New Columns
- Application code switches from `{old_col}` to `{new_first}` + `{new_last}`
- Dual-write continues to maintain `{old_col}` as fallback
- **No downtime**: if rollback needed, switch reads back

### Step 4: Drop Old Column + NOT NULL
- After confirming reads work correctly, drop `{old_col}`
- Add NOT NULL constraint to new columns
- **CRITICAL**: Must verify backfill is 100% complete before dropping
- If any row has NULL in new columns, this will fail

## Anti-Patterns (DO NOT DO)
- Do NOT drop old column before backfill is complete
- Do NOT add NOT NULL constraint before backfill
- Do NOT skip the dual-write phase
- Do NOT switch reads before backfill is verified
"""

        # deploy_config.yaml
        files["deploy_config.yaml"] = f"""# Blue-Green Deployment Configuration
deployment:
  strategy: blue-green
  table: {table}
  migration:
    old_column: {old_col}
    new_columns:
      - {new_first}
      - {new_last}
  rollback_window_minutes: 30
  health_check_interval_seconds: 10
  canary_percentage: 10
"""

        files["requirements.txt"] = "sqlalchemy>=2.0.0\n"

        return files

    def _generate_spec(self, cfg: dict) -> str:
        table = cfg["table"]
        model = cfg["model"]
        old_col = cfg["old_col"]
        new_first = cfg["new_col_first"]
        new_last = cfg["new_col_last"]

        return f"""# LH7: Zero-Downtime Database Migration

## Goal
Execute a database schema migration from `{table}.{old_col}` to two new columns
(`{new_first}`, `{new_last}`) with **zero downtime**. The application must remain
functional throughout the migration process.

## Current State
- `app.py` has a `{model}` SQLAlchemy model with column `{old_col}`
- 4 migration scripts in `migrations/` directory
- `run_migrations.py` executes migrations in filename sort order

## Problems to Fix

### 1. Migration Order is WRONG
The migration files are numbered incorrectly. The filename ordering is:
1. `001_backfill_dual_write.py` — actually performs backfill (Step 2)
2. `002_drop_old_column.py` — actually drops old column (Step 4)
3. `003_add_new_columns.py` — actually adds new columns (Step 1)
4. `004_switch_reads.py` — actually switches reads (Step 3)

**Correct order must be**: Add columns -> Backfill -> Switch reads -> Drop old column

Rename the files so they execute in the correct order:
- `001_add_new_columns.py` (currently 003)
- `002_backfill_dual_write.py` (currently 001)
- `003_switch_reads.py` (currently 004)
- `004_drop_old_column.py` (currently 002)

### 2. Missing Backfill Completeness Check
Migration 004 (drop old column) does NOT verify that all rows have been backfilled.
Before dropping `{old_col}`, it must:
- Query for rows where `{new_first} IS NULL OR {new_last} IS NULL`
- Raise an error if any are found
- Only proceed with the drop if 100% of rows are backfilled

### 3. Update app.py
After migrations complete, `app.py` should be updated to:
- Add `{new_first}` and `{new_last}` columns to the model
- Update `read_{table}()` to use new columns
- Keep `{old_col}` in model for backwards compatibility during transition

## RUNBOOK.md
Contains the correct migration sequence documentation. Follow it.

## Deliverables
1. Migration files renamed/reordered to execute in correct sequence
2. Backfill completeness check added to the drop-old-column migration
3. `app.py` updated with new columns in model
4. `run_migrations.py` must succeed end-to-end
5. Verifier writes `attestation.json`
"""

    def _generate_brief(self, cfg: dict) -> str:
        table = cfg["table"]
        old_col = cfg["old_col"]
        new_first = cfg["new_col_first"]
        new_last = cfg["new_col_last"]

        return f"""# LH7: Zero-Downtime Database Migration (Brief)

Migrate `{table}.{old_col}` to `{new_first}` + `{new_last}` with zero downtime.

The `migrations/` directory has 4 migration scripts that are in the WRONG ORDER.
Reorder them and fix any issues so `run_migrations.py` succeeds.

See `RUNBOOK.md` for the correct migration pattern.

Run: `python app.py` to seed data, then `python run_migrations.py` to apply migrations.
"""
