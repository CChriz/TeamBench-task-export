"""
Parameterized generator for O1: Service Health Recovery.

Each seed produces:
  - Different port number
  - Different health check endpoint path
  - Different config key/value structure
  - Different bug type in server.py (wrong status code, missing endpoint,
    incorrect response format, wrong config key read)
  - Seed-specific expected.json, config.json, spec.md, brief.md

The task structure stays the same: fix server.py so that GET /health (or the
seed-specific health endpoint) returns HTTP 200 with the correct body.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Port choices (avoid well-known ports and conflicts)
PORT_CHOICES = [8080, 8081, 8082, 8088, 8090, 8099, 9000, 9001, 9090]

# Health endpoint path variants
HEALTH_ENDPOINTS = ["/health", "/healthz", "/status", "/ping", "/ready"]

# Service mode key variants in config
SERVICE_MODE_KEYS = ["service_mode", "mode", "env", "run_mode", "environment"]

# Service mode values that mean "production"
PROD_MODE_VALUES = ["prod", "production", "live", "release"]

# Bug types the generator can introduce
BUG_TYPES = [
    "wrong_status_code_in_prod",   # returns 500 instead of 200 in prod mode
    "missing_health_endpoint",     # health endpoint not registered (falls to 404)
    "wrong_response_body",         # returns {"status":"degraded"} instead of {"status":"ok"}
    "wrong_config_key",            # reads wrong key from config so logic fails
    "inverted_condition",          # condition for prod vs non-prod is inverted
]


class Generator(TaskGenerator):
    task_id = "O1_service_health"
    domain = "operations"
    difficulty = "easy"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        port = rng.choice(PORT_CHOICES)
        health_path = rng.choice(HEALTH_ENDPOINTS)
        mode_key = rng.choice(SERVICE_MODE_KEYS)
        prod_value = rng.choice(PROD_MODE_VALUES)
        bug_type = rng.choice(BUG_TYPES)

        # Config file: the correct config that the server should read
        config = {mode_key: prod_value}

        # Expected ground truth
        expected = {
            "port": port,
            "health_endpoint": health_path,
            "mode_key": mode_key,
            "prod_value": prod_value,
            "bug_type": bug_type,
            "expected_health_status_code": 200,
            "expected_health_body": '{"status":"ok"}',
        }

        # Generate workspace files
        server_py = self._generate_buggy_server(port, health_path, mode_key, prod_value, bug_type)
        config_json = self._generate_config(mode_key, prod_value)
        run_service_sh = self._generate_run_service()

        workspace_files = {
            "server.py": server_py,
            "config.json": config_json,
            "run_service.sh": run_service_sh,
        }

        spec_md = self._generate_spec(port, health_path)
        brief_md = self._generate_brief(health_path)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_buggy_server(
        self,
        port: int,
        health_path: str,
        mode_key: str,
        prod_value: str,
        bug_type: str,
    ) -> str:
        """Generate a buggy server.py. The bug type varies per seed."""

        if bug_type == "wrong_status_code_in_prod":
            # In prod mode the server returns 500 instead of 200
            health_handler = f'''    def do_GET(self):
        if self.path == "{health_path}":
            try:
                cfg = load_config()
                mode = cfg["{mode_key}"]
                if mode != "{prod_value}":
                    self._send(200, json.dumps({{"status": "ok"}}))
                    return
                # BUG: should return 200 in prod mode, not 500
                self._send(500, json.dumps({{"status": "ok"}}))
            except Exception:
                traceback.print_exc()
                self._send(500, json.dumps({{"status": "error"}}))
        else:
            self._send(404, json.dumps({{"status": "not_found"}}))'''

        elif bug_type == "missing_health_endpoint":
            # Health path not handled — falls through to 404
            health_handler = f'''    def do_GET(self):
        # BUG: health endpoint check is missing — all requests return 404
        if self.path == "/metrics":
            self._send(200, json.dumps({{"metrics": []}}))
        else:
            self._send(404, json.dumps({{"status": "not_found"}}))'''

        elif bug_type == "wrong_response_body":
            # Returns wrong body (degraded instead of ok)
            health_handler = f'''    def do_GET(self):
        if self.path == "{health_path}":
            try:
                cfg = load_config()
                # BUG: returns "degraded" instead of "ok"
                self._send(200, json.dumps({{"status": "degraded"}}))
            except Exception:
                traceback.print_exc()
                self._send(500, json.dumps({{"status": "error"}}))
        else:
            self._send(404, json.dumps({{"status": "not_found"}}))'''

        elif bug_type == "wrong_config_key":
            # Reads wrong key from config (hardcoded wrong key)
            wrong_key = "service_type" if mode_key != "service_type" else "type"
            health_handler = f'''    def do_GET(self):
        if self.path == "{health_path}":
            try:
                cfg = load_config()
                # BUG: reads wrong config key "{wrong_key}" instead of "{mode_key}"
                mode = cfg["{wrong_key}"]
                if mode == "{prod_value}":
                    self._send(200, json.dumps({{"status": "ok"}}))
                    return
                self._send(500, json.dumps({{"status": "error"}}))
            except Exception:
                traceback.print_exc()
                self._send(500, json.dumps({{"status": "error"}}))
        else:
            self._send(404, json.dumps({{"status": "not_found"}}))'''

        else:  # inverted_condition
            # Condition is inverted: returns ok only in non-prod mode
            health_handler = f'''    def do_GET(self):
        if self.path == "{health_path}":
            try:
                cfg = load_config()
                mode = cfg["{mode_key}"]
                # BUG: condition is inverted — returns 200 only when NOT in prod mode
                if mode != "{prod_value}":
                    self._send(200, json.dumps({{"status": "ok"}}))
                    return
                self._send(503, json.dumps({{"status": "unavailable"}}))
            except Exception:
                traceback.print_exc()
                self._send(500, json.dumps({{"status": "error"}}))
        else:
            self._send(404, json.dumps({{"status": "not_found"}}))'''

        return f'''import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_PATH = "config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        print(format % args)

{health_handler}


def main():
    server = HTTPServer(("127.0.0.1", {port}), Handler)
    print("Serving on 127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
'''

    def _generate_config(self, mode_key: str, prod_value: str) -> str:
        import json
        return json.dumps({mode_key: prod_value}, indent=2) + "\n"

    def _generate_run_service(self) -> str:
        return '''#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${REPORTS_DIR:-../reports}/service.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Start the service and redirect stdout/stderr to logs
python server.py >"$LOG_FILE" 2>&1
'''

    def _generate_spec(self, port: int, health_path: str) -> str:
        return f"""# O1: Service Health Recovery (stdlib only)

## Goal
Bring up a local HTTP service that satisfies ALL requirements below.

## Hard Requirements

1. Running `bash run_service.sh` must start an HTTP server on `127.0.0.1:{port}`.
2. `GET {health_path}` must return HTTP **200**.
3. The response body must be **exactly**: `{{"status":"ok"}}` (no extra spaces, keys in this order).
4. `{health_path}` must **not** emit stack traces in logs.
5. Do **not** change the endpoint paths.
6. Service must keep running for at least **8 seconds** after start.

## Deliverables
- Working code in the workspace.
- Executor must write logs to `/shared/reports/service.log`.
- Verifier must create `/shared/submission/attestation.json` with `verdict="pass"`.
"""

    def _generate_brief(self, health_path: str) -> str:
        return f"""# O1: Service Health Recovery (Brief)

Fix the local service so that `{health_path}` works. Keep changes minimal.
Write runtime logs to `/shared/reports/service.log`.
"""
