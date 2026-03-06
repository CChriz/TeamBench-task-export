"""
Parameterized generator for MULTI7: Polyglot Test.

Each seed produces:
  - Different table/entity names
  - Different env var naming conventions (wrong vs correct)
  - Different FK column name errors
  - Same 3 bug types: wrong env vars in bash, wrong FK reference in SQL,
    wrong default config path in Python

The 3 bugs are always:
  1. deploy.sh exports DB_HOST/DB_PORT instead of DATABASE_HOST/DATABASE_PORT
  2. migrations/002_add_fk.sql references users(user_id) instead of users(id)
  3. app.py defaults to /etc/app/config.env instead of ./config.env
"""
from __future__ import annotations

import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

ENTITY_CONFIGS = [
    {"table": "orders",   "fk_table": "users",      "pk_col": "id",
     "host_var": "DATABASE_HOST", "port_var": "DATABASE_PORT",
     "wrong_host": "DB_HOST", "wrong_port": "DB_PORT",
     "wrong_fk": "user_id", "db_name": "appdb"},
    {"table": "invoices", "fk_table": "customers",   "pk_col": "id",
     "host_var": "DATABASE_HOST", "port_var": "DATABASE_PORT",
     "wrong_host": "DB_HOST", "wrong_port": "DB_PORT",
     "wrong_fk": "customer_id", "db_name": "billing"},
    {"table": "tickets",  "fk_table": "agents",      "pk_col": "id",
     "host_var": "DATABASE_HOST", "port_var": "DATABASE_PORT",
     "wrong_host": "DB_HOST", "wrong_port": "DB_PORT",
     "wrong_fk": "agent_id", "db_name": "support"},
    {"table": "shipments","fk_table": "warehouses",   "pk_col": "id",
     "host_var": "DATABASE_HOST", "port_var": "DATABASE_PORT",
     "wrong_host": "DB_HOST", "wrong_port": "DB_PORT",
     "wrong_fk": "warehouse_id", "db_name": "logistics"},
    {"table": "reviews",  "fk_table": "products",     "pk_col": "id",
     "host_var": "DATABASE_HOST", "port_var": "DATABASE_PORT",
     "wrong_host": "DB_HOST", "wrong_port": "DB_PORT",
     "wrong_fk": "product_id", "db_name": "catalog"},
]

WRONG_PATHS = [
    "/etc/app/config.env",
    "/opt/config/app.env",
    "/var/lib/app/config.env",
    "/usr/local/etc/config.env",
    "/home/deploy/config.env",
]

PORTS = [5432, 3306, 5433, 3307, 5434]


class Generator(TaskGenerator):
    task_id = "MULTI7_polyglot_test"
    domain = "deployment"
    difficulty = "hard"
    languages = ["python", "bash", "sql"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = ENTITY_CONFIGS[seed % len(ENTITY_CONFIGS)]
        wrong_path = WRONG_PATHS[seed % len(WRONG_PATHS)]
        db_port = PORTS[seed % len(PORTS)]

        workspace_files = {
            "app.py": self._gen_app(cfg, wrong_path, db_port),
            "deploy.sh": self._gen_deploy(cfg, db_port),
            "migrations/001_create.sql": self._gen_migration_001(cfg),
            "migrations/002_add_fk.sql": self._gen_migration_002_buggy(cfg),
            "config.env": self._gen_config_env(cfg, db_port),
            "test_app.py": self._gen_tests(cfg, wrong_path),
        }

        expected = {
            "seed": seed,
            "table": cfg["table"],
            "fk_table": cfg["fk_table"],
            "pk_col": cfg["pk_col"],
            "host_var": cfg["host_var"],
            "port_var": cfg["port_var"],
            "wrong_host": cfg["wrong_host"],
            "wrong_port": cfg["wrong_port"],
            "wrong_fk": cfg["wrong_fk"],
            "wrong_path": wrong_path,
            "correct_path": "./config.env",
            "bugs": [
                f"deploy.sh exports {cfg['wrong_host']}/{cfg['wrong_port']} instead of {cfg['host_var']}/{cfg['port_var']}",
                f"002_add_fk.sql FK references {cfg['fk_table']}({cfg['wrong_fk']}) instead of {cfg['fk_table']}({cfg['pk_col']})",
                f"app.py defaults to {wrong_path} instead of ./config.env",
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

    def _gen_app(self, cfg, wrong_path, db_port):
        return f'''"""Application configuration loader."""
import os


def load_config(path=None):
    """Load configuration from env file.

    Reads DATABASE_HOST, DATABASE_PORT, DATABASE_NAME from the env file.
    """
    config_path = path or "{wrong_path}"
    config = {{}}
    if os.path.exists(config_path):
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    config[key.strip()] = value.strip()
    return config


def get_db_url(config=None):
    """Build database connection URL from config."""
    if config is None:
        config = load_config()
    host = config.get("{cfg['host_var']}", "localhost")
    port = config.get("{cfg['port_var']}", "{db_port}")
    name = config.get("DATABASE_NAME", "{cfg['db_name']}")
    return f"postgresql://{{host}}:{{port}}/{{name}}"


if __name__ == "__main__":
    cfg = load_config()
    print(f"DB URL: {{get_db_url(cfg)}}")
'''

    def _gen_deploy(self, cfg, db_port):
        return f'''#!/usr/bin/env bash
set -euo pipefail

# Environment setup
export {cfg["wrong_host"]}=db.example.com
export {cfg["wrong_port"]}={db_port}
export DATABASE_NAME={cfg["db_name"]}

echo "Running migrations..."
for f in migrations/*.sql; do
    echo "  Applying $f"
done

echo "Starting application..."
python3 app.py
'''

    def _gen_migration_001(self, cfg):
        return f'''-- Initial schema creation
CREATE TABLE IF NOT EXISTS {cfg["fk_table"]} (
    {cfg["pk_col"]}   INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS {cfg["table"]} (
    {cfg["pk_col"]}   INTEGER PRIMARY KEY AUTOINCREMENT,
    amount            REAL NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
'''

    def _gen_migration_002_buggy(self, cfg):
        return f'''-- Add foreign key relationship
-- Link {cfg["table"]} to {cfg["fk_table"]}

DROP TABLE IF EXISTS {cfg["table"]};

CREATE TABLE {cfg["table"]} (
    {cfg["pk_col"]}         INTEGER PRIMARY KEY AUTOINCREMENT,
    {cfg["fk_table"]}_ref   INTEGER NOT NULL,
    amount                  REAL NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'pending',
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY ({cfg["fk_table"]}_ref) REFERENCES {cfg["fk_table"]}({cfg["wrong_fk"]})
);
'''

    def _gen_config_env(self, cfg, db_port):
        return f'''{cfg["host_var"]}=db.example.com
{cfg["port_var"]}={db_port}
DATABASE_NAME={cfg["db_name"]}
'''

    def _gen_tests(self, cfg, wrong_path):
        return f'''"""
Test suite for MULTI7_polyglot_test. Do NOT modify.
"""
import os
import sqlite3
import unittest


class PolyglotTestCase(unittest.TestCase):

    def test_deploy_exports_correct_host_var(self):
        with open("deploy.sh") as f:
            content = f.read()
        self.assertIn("{cfg['host_var']}", content,
                      msg="deploy.sh must export {cfg['host_var']}")
        self.assertNotIn("{cfg['wrong_host']}=", content,
                         msg="deploy.sh still uses {cfg['wrong_host']}")

    def test_deploy_exports_correct_port_var(self):
        with open("deploy.sh") as f:
            content = f.read()
        self.assertIn("{cfg['port_var']}", content,
                      msg="deploy.sh must export {cfg['port_var']}")
        self.assertNotIn("{cfg['wrong_port']}=", content,
                         msg="deploy.sh still uses {cfg['wrong_port']}")

    def test_sql_fk_correct_column(self):
        with open("migrations/002_add_fk.sql") as f:
            content = f.read().lower()
        self.assertIn("({cfg['pk_col']})", content,
                      msg="FK must reference {cfg['fk_table']}({cfg['pk_col']})")

    def test_sql_fk_not_wrong_column(self):
        with open("migrations/002_add_fk.sql") as f:
            content = f.read().lower()
        self.assertNotIn("({cfg['wrong_fk']})", content,
                         msg="FK still references wrong column {cfg['wrong_fk']}")

    def test_sql_schema_valid(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        with open("migrations/001_create.sql") as f:
            conn.executescript(f.read())
        with open("migrations/002_add_fk.sql") as f:
            conn.executescript(f.read())
        conn.close()

    def test_config_loader_default_path(self):
        with open("app.py") as f:
            source = f.read()
        self.assertNotIn("{wrong_path}", source,
                         msg="app.py still defaults to {wrong_path}")
        self.assertIn("config.env", source,
                      msg="app.py must reference config.env")

    def test_config_loader_works(self):
        import importlib
        import app as app_module
        importlib.reload(app_module)
        cfg = app_module.load_config()
        self.assertIsNotNone(cfg)
        self.assertIn("{cfg['host_var']}", cfg,
                      msg="Config missing {cfg['host_var']}")

    def test_db_url_generation(self):
        import importlib
        import app as app_module
        importlib.reload(app_module)
        cfg = app_module.load_config()
        url = app_module.get_db_url(cfg)
        self.assertIn("db.example.com", url)


if __name__ == "__main__":
    unittest.main()
'''
