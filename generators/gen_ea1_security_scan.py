"""
Parameterized generator for EA1: Security Scan.

Each seed produces different variable/function names but the same
structural vulnerabilities. The Planner's bandit analysis will find
the same 8 vulnerability categories regardless of naming variations.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# App name variants per seed
APP_NAMES = ["inventory_app", "billing_app", "analytics_app"]
DB_TABLES = ["products", "invoices", "events"]
SECRET_NAMES = ["APP_SECRET", "SECRET_KEY", "API_SECRET"]
HARDCODED_SECRETS = ["hardcoded_prod_secret_xyz", "super_secret_key_456", "my_secret_key_789"]


class Generator(TaskGenerator):
    task_id = "EA1_security_scan"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(APP_NAMES)

        app_name = APP_NAMES[idx]
        table = DB_TABLES[idx]
        secret_name = SECRET_NAMES[idx]
        secret_val = HARDCODED_SECRETS[idx]

        workspace_files = self._make_workspace(table, secret_name, secret_val)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "EA1_security_scan")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="EA1_security_scan",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "fixed_vulns": ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"],
                "preserved_fps": ["FP1", "FP2", "FP3"],
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(self, table: str, secret_name: str, secret_val: str) -> dict:
        files = {}

        files["app/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        files["app/config.py"] = f'''import os

{secret_name} = "{secret_val}"
DEBUG = False
DATABASE = "app.db"
'''

        files["app/routes.py"] = f'''import sqlite3
import ast
from flask import request, jsonify

def search():
    """Search for items by name."""
    name = request.args.get("name", "")
    conn = sqlite3.connect("app.db")
    query = "SELECT * FROM {table} WHERE name = \'" + name + "\'"
    results = conn.execute(query).fetchall()
    return jsonify(results)

def calculate():
    """Evaluate a mathematical expression."""
    expr = request.args.get("expr", "0")
    result = eval(expr)
    return jsonify({{"result": result}})
'''

        files["app/utils.py"] = '''import subprocess

def run_report(report_name: str) -> str:
    """Generate a report for the given report name."""
    cmd = f"generate_report {report_name}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout
'''

        files["app/auth.py"] = '''import hashlib

def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash
'''

        files["app/parser.py"] = '''import xml.etree.ElementTree as ET

def parse_config(xml_data: str) -> dict:
    """Parse XML configuration data and return as dict."""
    root = ET.fromstring(xml_data)
    return {child.tag: child.text for child in root}
'''

        files["app/cache.py"] = '''import pickle

def load_cache(cache_bytes: bytes) -> dict:
    """Load cached data from bytes."""
    return pickle.loads(cache_bytes)

def save_cache(data: dict) -> bytes:
    return pickle.dumps(data)
'''

        files["app/tokens.py"] = '''import random

def generate_token() -> str:
    """Generate a session token."""
    return str(random.randint(100000, 999999))
'''

        # Tests with intentional false positives
        files["tests/test_auth.py"] = '''"""Auth tests — contains intentional bandit false positives."""
import hashlib

TEST_PASSWORD = "test_password_123"

def test_verify_password():
    """Test password verification."""
    from app.auth import hash_password, verify_password
    h = hash_password(TEST_PASSWORD)
    assert verify_password(TEST_PASSWORD, h)

def test_legacy_hash_compatibility():
    """Test backward compatibility with legacy password hashes from the old system."""
    legacy_hash = hashlib.md5("legacy_password".encode()).hexdigest()
    # Verify the migration check function can detect legacy format
    assert len(legacy_hash) == 32  # MD5 produces 32-char hex
'''

        files["tests/test_integration.py"] = '''"""Integration tests — contains intentional bandit false positives."""
import subprocess

def test_report_generation():
    """Test that report generation completes successfully."""
    result = subprocess.run(
        ["echo", "test_report_output"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
'''

        files["requirements.txt"] = "flask\ndefusedxml\n"

        return files
