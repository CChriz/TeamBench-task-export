"""
Parameterized generator for S7: Environment Variable Configuration Fix.

Each seed produces:
  - Different variable names and default values
  - A buggy config.py with 3 env var bugs
  - An app.py that imports config
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DB_HOST_DEFAULTS = ["localhost", "127.0.0.1", "db.local"]
RETRIES_VARS = ["MAX_RETRIES", "RETRY_COUNT", "MAX_ATTEMPTS"]
RETRIES_ATTRS = ["max_retries", "retry_count", "max_attempts"]
API_KEY_VARS = ["API_KEY", "AUTH_TOKEN", "SERVICE_KEY"]
DB_HOST_VARS = ["DB_HOST", "DATABASE_HOST", "DB_SERVER"]
CACHE_TTL_VARS = ["CACHE_TTL", "TTL_SECONDS", "CACHE_TIMEOUT"]


class Generator(TaskGenerator):
    task_id = "S7_env_config"
    domain = "swe"
    difficulty = "easy"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 3

        db_host_var = DB_HOST_VARS[idx]
        db_host_default = DB_HOST_DEFAULTS[idx]
        retries_var = RETRIES_VARS[idx]
        retries_attr = RETRIES_ATTRS[idx]
        api_key_var = API_KEY_VARS[idx]
        api_key_wrong = api_key_var.lower()  # wrong case
        cache_ttl_var = CACHE_TTL_VARS[idx]

        workspace_files = {
            "config.py": self._make_buggy_config(
                db_host_var, retries_var, retries_attr, api_key_wrong, cache_ttl_var
            ),
            "app.py": self._make_app(retries_attr),
            ".env.example": self._make_env_example(
                db_host_var, db_host_default, retries_var, api_key_var, cache_ttl_var
            ),
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
            expected={
                "seed": seed,
                "db_host_var": db_host_var,
                "db_host_default": db_host_default,
                "retries_var": retries_var,
                "retries_attr": retries_attr,
                "api_key_var": api_key_var,
                "api_key_wrong": api_key_wrong,
                "cache_ttl_var": cache_ttl_var,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "SWE"},
        )

    def _make_buggy_config(self, db_host_var: str, retries_var: str,
                           retries_attr: str, api_key_wrong: str,
                           cache_ttl_var: str) -> str:
        return f'''"""Application configuration from environment variables."""
import os


# BUG 1: os.environ[] with no default — crashes if unset
db_host = os.environ["{db_host_var}"]

# OK: this one has a proper default
cache_ttl = int(os.environ.get("{cache_ttl_var}", "300"))

# BUG 2: read as string, compared with int later — TypeError
{retries_attr} = os.environ.get("{retries_var}", "3")

# BUG 3: wrong case — should be "{api_key_wrong.upper()}" not "{api_key_wrong}"
api_key = os.environ.get("{api_key_wrong}", "default-key")
'''

    def _make_app(self, retries_attr: str) -> str:
        return f'''"""Main application entry point."""
import config


def main():
    print(f"Connecting to {{config.db_host}}")
    print(f"Cache TTL: {{config.cache_ttl}}")
    print(f"API Key: {{config.api_key}}")

    # BUG 2 manifests here: comparing string with int
    if config.{retries_attr} > 5:
        print("High retry count")
    else:
        print(f"Retries: {{config.{retries_attr}}}")

    print("App started successfully")


if __name__ == "__main__":
    main()
'''

    def _make_env_example(self, db_host_var: str, db_host_default: str,
                          retries_var: str, api_key_var: str,
                          cache_ttl_var: str) -> str:
        return f"""# Environment variables for the application
# Copy this to .env and adjust values

{db_host_var}={db_host_default}
{cache_ttl_var}=300
{retries_var}=3
{api_key_var}=your-api-key-here
"""
