"""
Parameterized generator for MULTI5: CI/CD Pipeline Repair.

Each seed produces a different project with 3 broken pipeline stages:
  1. Lint: pylint config has wrong max-line-length causing false failures
  2. Test: conftest.py has wrong fixture scope (function instead of session)
  3. Deploy: Dockerfile has wrong COPY path and missing build arg
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

PROJECTS = [
    {
        "name": "webapp",
        "module": "app_web",
        "port": "8080",
        "bad_max_line": 40,
        "good_max_line": 120,
        "db_type": "postgresql",
        "db_port": "5432",
    },
    {
        "name": "api_service",
        "module": "app_api",
        "port": "9090",
        "bad_max_line": 50,
        "good_max_line": 100,
        "db_type": "mysql",
        "db_port": "3306",
    },
    {
        "name": "data_worker",
        "module": "app_worker",
        "port": "7070",
        "bad_max_line": 35,
        "good_max_line": 110,
        "db_type": "sqlite",
        "db_port": "",
    },
]


class Generator(TaskGenerator):
    task_id = "MULTI5_deploy_pipeline"
    domain = "Operations"
    difficulty = "hard"
    languages = ["python", "bash"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        p = PROJECTS[seed % len(PROJECTS)]

        workspace_files = self._make_workspace(p, rng)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "MULTI5_deploy_pipeline")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="MULTI5_deploy_pipeline",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "project": p["name"],
                "bugs_fixed": 3,
                "good_max_line": p["good_max_line"],
                "fixture_scope": "session",
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Operations"},
        )

    def _make_workspace(self, p: dict, rng: SeededRandom) -> dict:
        files = {}

        # --- Application source (DO NOT MODIFY) ---
        files["app/__init__.py"] = ""
        files["app/main.py"] = self._app_main(p)
        files["app/models.py"] = self._app_models(p)
        files["app/utils.py"] = self._app_utils(p)

        # --- Pipeline config ---
        files["pipeline.yaml"] = self._pipeline_yaml(p)

        # --- Lint config (BUGGY: max-line-length too low) ---
        files[".pylintrc"] = self._pylintrc(p)

        # --- Scripts ---
        files["scripts/lint.sh"] = self._lint_script(p)
        files["scripts/test.sh"] = self._test_script(p)
        files["scripts/deploy.sh"] = self._deploy_script(p)

        # --- Test files ---
        files["tests/__init__.py"] = ""
        files["tests/conftest.py"] = self._conftest(p)
        files["tests/test_models.py"] = self._test_models(p)
        files["tests/test_utils.py"] = self._test_utils(p)

        # --- Dockerfile (BUGGY: wrong COPY path, missing ARG) ---
        files["Dockerfile"] = self._dockerfile(p)

        # --- Docs ---
        files["PIPELINE_DOCS.md"] = self._pipeline_docs(p)

        return files

    def _app_main(self, p: dict) -> str:
        return f'''"""Main application entry point for {p["name"]}."""
import os
from app.models import DatabaseConnection
from app.utils import format_response, validate_input


def create_app(config=None):
    """Create and configure the application instance with default settings for {p["name"]}."""
    db = DatabaseConnection(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "{p["port"]}")))
    return {{"db": db, "config": config or {{}}}}


def handle_request(app, request_data):
    """Handle an incoming request, validate it, process through the database, and return a formatted response."""
    if not validate_input(request_data):
        return format_response(error="Invalid input data provided to the {p["name"]} service endpoint")
    result = app["db"].query(request_data.get("query", "SELECT 1"))
    return format_response(data=result, status="success")
'''

    def _app_models(self, p: dict) -> str:
        return f'''"""Database models for {p["name"]}."""


class DatabaseConnection:
    """Manages database connections for the {p["name"]} service with connection pooling and retry logic."""

    def __init__(self, host="localhost", port={p["port"]}):
        self.host = host
        self.port = port
        self._connection = None

    def connect(self):
        """Establish a database connection to {p["db_type"]} with automatic retry on transient connection failures."""
        self._connection = {{"host": self.host, "port": self.port, "type": "{p["db_type"]}", "connected": True}}
        return self._connection

    def query(self, sql):
        """Execute a SQL query against the {p["db_type"]} database and return results as a list of row dictionaries."""
        if not self._connection:
            self.connect()
        return [{{"result": "ok", "sql": sql}}]

    def close(self):
        """Close the database connection and release any held resources back to the connection pool."""
        self._connection = None
'''

    def _app_utils(self, p: dict) -> str:
        return f'''"""Utility functions for {p["name"]}."""


def format_response(data=None, error=None, status="ok"):
    """Format a standardized API response dictionary with optional data payload, error message, and status indicator."""
    response = {{"status": status}}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
        response["status"] = "error"
    return response


def validate_input(data):
    """Validate incoming request data ensuring it is a non-empty dictionary with only allowed string or numeric values."""
    if not isinstance(data, dict):
        return False
    if not data:
        return False
    return True


def sanitize_string(value):
    """Sanitize a string value by stripping whitespace, removing null bytes, and truncating to a maximum safe length."""
    if not isinstance(value, str):
        return str(value)
    return value.strip().replace("\\x00", "")[:1000]
'''

    def _pipeline_yaml(self, p: dict) -> str:
        return f'''# CI/CD Pipeline for {p["name"]}
name: {p["name"]}-pipeline
trigger:
  branches: [main, develop]

stages:
  - name: lint
    script: scripts/lint.sh
    timeout: 300

  - name: test
    script: scripts/test.sh
    timeout: 600
    depends_on: [lint]

  - name: deploy
    script: scripts/deploy.sh
    timeout: 900
    depends_on: [test]
    environment:
      APP_VERSION: "1.0.0"
      REGISTRY: "registry.example.com"
'''

    def _pylintrc(self, p: dict) -> str:
        return f'''[MASTER]
jobs=1
load-plugins=

[FORMAT]
max-line-length={p["bad_max_line"]}
indent-string='    '
indent-after-paren=4

[MESSAGES CONTROL]
disable=C0114,C0115,C0116

[BASIC]
good-names=i,j,k,v,e,f,db,p

[DESIGN]
max-args=8
max-locals=20
'''

    def _lint_script(self, p: dict) -> str:
        return f'''#!/usr/bin/env bash
set -euo pipefail
echo "Running pylint for {p["name"]}..."
python3 -m pylint --rcfile=.pylintrc app/
echo "Lint passed."
'''

    def _test_script(self, p: dict) -> str:
        return f'''#!/usr/bin/env bash
set -euo pipefail
echo "Running pytest for {p["name"]}..."
python3 -m pytest tests/ -v
echo "Tests passed."
'''

    def _deploy_script(self, p: dict) -> str:
        return f'''#!/usr/bin/env bash
set -euo pipefail
echo "Building Docker image for {p["name"]}..."
docker build \\
    --build-arg APP_VERSION="${{APP_VERSION:-1.0.0}}" \\
    -t "${{REGISTRY:-registry.example.com}}/{p["name"]}:${{APP_VERSION:-1.0.0}}" \\
    .
echo "Deploy image built successfully."
'''

    def _conftest(self, p: dict) -> str:
        return f'''"""Pytest fixtures for {p["name"]} tests."""
import pytest
from app.models import DatabaseConnection


@pytest.fixture(scope="function")  # BUG: should be scope="session" to avoid connection exhaustion
def db():
    """Create a database connection for testing.

    NOTE: This fixture creates a new connection for every test function.
    With many tests, this exhausts the connection pool on {p["db_type"]}.
    """
    conn = DatabaseConnection(host="localhost", port={p["port"]})
    conn.connect()
    yield conn
    conn.close()


@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {{"query": "SELECT * FROM test_table", "expected_rows": 5}}
'''

    def _test_models(self, p: dict) -> str:
        return f'''"""Tests for {p["name"]} models."""


def test_connection_creates(db):
    """Test that database connection is established."""
    assert db._connection is not None
    assert db._connection["connected"] is True


def test_connection_type(db):
    """Test database type is correct."""
    assert db._connection["type"] == "{p["db_type"]}"


def test_query_returns_results(db):
    """Test that query returns results."""
    results = db.query("SELECT 1")
    assert len(results) > 0
    assert results[0]["result"] == "ok"


def test_close_clears_connection(db):
    """Test that closing clears the connection."""
    db.close()
    assert db._connection is None
'''

    def _test_utils(self, p: dict) -> str:
        return '''"""Tests for utility functions."""
from app.utils import format_response, validate_input, sanitize_string


def test_format_response_success():
    resp = format_response(data={"key": "value"})
    assert resp["status"] == "ok"
    assert resp["data"] == {"key": "value"}


def test_format_response_error():
    resp = format_response(error="Something went wrong")
    assert resp["status"] == "error"
    assert resp["error"] == "Something went wrong"


def test_validate_input_valid():
    assert validate_input({"key": "value"}) is True


def test_validate_input_empty():
    assert validate_input({}) is False


def test_validate_input_none():
    assert validate_input(None) is False


def test_sanitize_string():
    assert sanitize_string("  hello  ") == "hello"
    assert sanitize_string(42) == "42"
'''

    def _dockerfile(self, p: dict) -> str:
        # BUG 1: COPY from wrong path (src/ instead of app/)
        # BUG 2: Missing ARG APP_VERSION
        return f'''FROM python:3.11-slim

WORKDIR /opt/{p["name"]}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# BUG: copies from src/ but the actual code is in app/
COPY src/ ./app/

EXPOSE {p["port"]}

ENV DB_HOST=localhost
ENV DB_PORT={p["port"]}

# BUG: references APP_VERSION but no ARG defined
LABEL version="${{APP_VERSION}}"

CMD ["python", "-m", "app.main"]
'''

    def _pipeline_docs(self, p: dict) -> str:
        return f'''# Pipeline Documentation for {p["name"]}

## Overview
The CI/CD pipeline has 3 stages that run in sequence: lint, test, deploy.

## Stage 1: Lint
- Runs pylint on all Python files under `app/`
- Uses `.pylintrc` for configuration
- **Expected**: max-line-length should be {p["good_max_line"]} (standard for this project)
- Lines up to {p["good_max_line"]} characters are acceptable

## Stage 2: Test
- Runs pytest on all tests under `tests/`
- The database fixture in `conftest.py` must use `scope="session"` to prevent
  connection exhaustion — the {p["db_type"]} test instance has a connection limit
- All tests should pass with a single database connection shared across the session

## Stage 3: Deploy
- Builds a Docker image using the `Dockerfile`
- Requires `APP_VERSION` build argument (declared as `ARG` in Dockerfile)
- The application code lives in `app/` directory (must be copied correctly)
- Image is tagged with the version and pushed to the registry

## Troubleshooting
- If lint fails with line-length errors, check `.pylintrc` max-line-length
- If tests fail with connection errors, check conftest.py fixture scope
- If docker build fails, check COPY paths and ARG declarations
'''
