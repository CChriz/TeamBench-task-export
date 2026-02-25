"""
Parameterized generator for NEG1: Conflicting Constraints Negotiation.

Each seed produces:
  - Different service type (payment gateway, auth service, data pipeline, API gateway, messaging queue)
  - Different benchmark thresholds (latency targets vary slightly)
  - Different middleware component names
  - Different config parameter names and valid ranges
  - Same bug categories: validation too slow, TLS disabled, circuit breaker missing, hardcoded credentials
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Service type configurations
SERVICE_CONFIGS = [
    {
        "service_type": "payment gateway",
        "service_class": "PaymentGateway",
        "latency_ms": 80,
        "port": 8080,
        "sleep_ms": 200,  # validator sleep (bug)
        "cb_threshold": 3,
        "cb_timeout": 10,
        "retry_base_ms": 100,
        "max_retries": 3,
    },
    {
        "service_type": "auth service",
        "service_class": "AuthService",
        "latency_ms": 90,
        "port": 8081,
        "sleep_ms": 250,
        "cb_threshold": 3,
        "cb_timeout": 10,
        "retry_base_ms": 100,
        "max_retries": 3,
    },
    {
        "service_type": "data pipeline",
        "service_class": "DataPipeline",
        "latency_ms": 100,
        "port": 8082,
        "sleep_ms": 300,
        "cb_threshold": 3,
        "cb_timeout": 10,
        "retry_base_ms": 100,
        "max_retries": 3,
    },
    {
        "service_type": "API gateway",
        "service_class": "ApiGateway",
        "latency_ms": 75,
        "port": 8083,
        "sleep_ms": 200,
        "cb_threshold": 3,
        "cb_timeout": 10,
        "retry_base_ms": 100,
        "max_retries": 3,
    },
    {
        "service_type": "messaging queue",
        "service_class": "MessagingQueue",
        "latency_ms": 85,
        "port": 8084,
        "sleep_ms": 220,
        "cb_threshold": 3,
        "cb_timeout": 10,
        "retry_base_ms": 100,
        "max_retries": 3,
    },
]

# Hardcoded token variants (all obviously wrong)
HARDCODED_TOKENS = [
    "hardcoded-secret-token-12345",
    "super-secret-api-key-9999",
    "plaintext-credential-abc123",
    "insecure-token-do-not-use",
    "my-secret-key-12345",
]


class Generator(TaskGenerator):
    task_id = "NEG1_tradeoff_config"
    domain = "operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        cfg = SERVICE_CONFIGS[seed % len(SERVICE_CONFIGS)]
        token = HARDCODED_TOKENS[seed % len(HARDCODED_TOKENS)]

        expected = {
            "service_type": cfg["service_type"],
            "latency_threshold_ms": cfg["latency_ms"],
            "port": cfg["port"],
            "circuit_breaker_threshold": cfg["cb_threshold"],
            "circuit_breaker_timeout": cfg["cb_timeout"],
            "retry_base_ms": cfg["retry_base_ms"],
            "max_retries": cfg["max_retries"],
            "fixes": {
                "validator": "remove time.sleep() — keep validation logic",
                "tls": "set tls_enabled=true in config",
                "circuit_breaker": "implement retry + circuit breaker in call_external_service",
                "credentials": "remove hardcoded token from config",
            },
        }

        workspace_files = self._build_workspace(cfg, token, rng)
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

    def _build_workspace(self, cfg, token, rng) -> dict[str, str]:
        files = {}
        svc = cfg["service_type"]
        port = cfg["port"]
        sleep_s = cfg["sleep_ms"] / 1000.0
        latency = cfg["latency_ms"]
        cb_threshold = cfg["cb_threshold"]
        cb_timeout = cfg["cb_timeout"]

        # service/config.json  -- BUGS: tls_enabled=false, hardcoded token, circuit_breaker_enabled=false
        import json
        files["service/config.json"] = json.dumps({
            "port": port,
            "tls_enabled": False,
            "validate_input": True,
            "api_token": token,
            "tls_cert_path": "",
            "tls_key_path": "",
            "circuit_breaker_enabled": False,
            "circuit_breaker_threshold": cb_threshold,
            "circuit_breaker_timeout": cb_timeout,
            "session_cache_enabled": False,
        }, indent=2) + "\n"

        # service/server.py
        files["service/server.py"] = f'''"""HTTP service with request handling ({svc})."""
import json
import time
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from service.middleware.validator import validate_input
from service.middleware.tls_handler import get_tls_context
from service.middleware.circuit_breaker import call_external_service


class Config:
    """Service configuration."""
    def __init__(self, config_path="service/config.json"):
        with open(config_path) as f:
            self._config = json.load(f)

    @property
    def port(self):
        return self._config.get("port", {port})

    @property
    def tls_enabled(self):
        return self._config.get("tls_enabled", False)

    @property
    def validate_input(self):
        return self._config.get("validate_input", True)

    @property
    def api_token(self):
        return self._config.get("api_token", "")


config = Config()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        pass  # Suppress logs for benchmarking

    def do_POST(self):
        if self.path == "/process":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send(400, {{"error": "invalid_json"}})
                return

            # Validate input
            if config.validate_input:
                start = time.time()
                is_valid, errors = validate_input(data)
                elapsed = time.time() - start
                if not is_valid:
                    self._send(400, {{"error": "validation_failed", "details": errors}})
                    return

            # Call external service (with circuit breaker if configured)
            ext_result = call_external_service(data)

            self._send(200, {{"status": "processed", "result": ext_result}})

        elif self.path == "/health":
            self._send(200, {{"status": "ok"}})
        else:
            self._send(404, {{"error": "not_found"}})


def main():
    server = HTTPServer(("127.0.0.1", config.port), Handler)
    print(f"Serving on 127.0.0.1:{{config.port}}")
    server.serve_forever()


if __name__ == "__main__":
    main()
'''

        # service/middleware/__init__.py
        files["service/middleware/__init__.py"] = ""

        # service/middleware/validator.py  -- BUG: time.sleep makes it too slow
        files["service/middleware/validator.py"] = f'''"""Input validation middleware — currently too slow."""
import time
import re


def validate_input(data):
    """Validate request input data.

    Current implementation: uses heavyweight parsing approach.
    Takes ~{cfg["sleep_ms"]}ms per validation call.
    """
    errors = []

    # Simulate slow validation (heavyweight approach)
    # In production this would call an external validation service
    time.sleep({sleep_s:.3f})  # {cfg["sleep_ms"]}ms — this is the performance bottleneck

    # Basic field checks
    if not isinstance(data, dict):
        errors.append("input_must_be_object")
        return False, errors

    name = data.get("name", "")
    if not name or len(name) > 200:
        errors.append("invalid_name")

    email = data.get("email", "")
    if email and not re.match(r\'^[^@]+@[^@]+\\.[^@]+$\', email):
        errors.append("invalid_email")

    value = data.get("value")
    if value is not None:
        try:
            v = float(value)
            if v < 0 or v > 1000000:
                errors.append("value_out_of_range")
        except (ValueError, TypeError):
            errors.append("invalid_value")

    return len(errors) == 0, errors
'''

        # service/middleware/tls_handler.py
        files["service/middleware/tls_handler.py"] = '''"""TLS handler — currently disabled for 'performance'."""
import ssl


def get_tls_context(cert_path=None, key_path=None):
    """Get TLS context for the server.

    Currently returns None (TLS disabled) because enabling TLS
    was thought to add too much latency.

    With session caching, TLS overhead is only ~10ms per request.
    """
    if not cert_path or not key_path:
        return None

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    return context
'''

        # service/middleware/circuit_breaker.py  -- BUG: no circuit breaker or retry
        files["service/middleware/circuit_breaker.py"] = f'''"""Circuit breaker for external service calls — NOT IMPLEMENTED."""
import time
import random


# Simulated external service
def _external_service(data):
    """Simulate an external service call."""
    # Force failure when trigger_fail key is present
    if data.get("trigger_fail"):
        raise ConnectionError("External service unavailable")
    # Randomly fail ~10% of the time
    if random.random() < 0.1:
        raise ConnectionError("External service unavailable")
    time.sleep(0.01)  # 10ms latency
    return {{"processed": True, "input_hash": hash(str(data))}}


def call_external_service(data):
    """Call external service — no circuit breaker, no retry."""
    try:
        return _external_service(data)
    except ConnectionError:
        return {{"processed": False, "error": "service_unavailable"}}
'''

        # benchmarks/perf_test.py
        files["benchmarks/perf_test.py"] = f'''"""Performance benchmark: measures p95 latency."""
import json
import statistics
import time
import urllib.request
import subprocess
import sys
import os
import signal


def run_benchmark():
    """Start server and measure request latencies."""
    server_proc = subprocess.Popen(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, \'.\'); from service.server import main; main()"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    try:
        time.sleep(1)  # Wait for server to start

        latencies = []
        for i in range(20):
            payload = json.dumps({{"name": f"User{{i}}", "email": f"user{{i}}@example.com", "value": i * 10}}).encode()
            start = time.time()
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:{port}/process",
                    data=payload,
                    headers={{"Content-Type": "application/json"}},
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    resp.read()
                elapsed = (time.time() - start) * 1000  # ms
                latencies.append(elapsed)
            except Exception as e:
                latencies.append(2000)  # 2s timeout = fail

        if not latencies:
            print("FAIL: No successful requests")
            sys.exit(1)

        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[min(p95_idx, len(latencies) - 1)]

        print(f"Requests: {{len(latencies)}}")
        print(f"p50 latency: {{statistics.median(latencies):.1f}}ms")
        print(f"p95 latency: {{p95:.1f}}ms")
        print(f"Max latency: {{max(latencies):.1f}}ms")

        if p95 < {latency}:
            print("PERF_PASS: p95 < {latency}ms")
            sys.exit(0)
        else:
            print(f"PERF_FAIL: p95 = {{p95:.1f}}ms (must be < {latency}ms)")
            sys.exit(1)
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)


if __name__ == "__main__":
    run_benchmark()
'''

        # benchmarks/security_scan.py
        files["benchmarks/security_scan.py"] = f'''"""Security checker: validates TLS, input validation, etc."""
import json
import sys
import os


def run_security_scan():
    """Check security requirements."""
    issues = []

    config_path = "service/config.json"
    with open(config_path) as f:
        config = json.load(f)

    # 1. TLS must be enabled
    if not config.get("tls_enabled", False):
        issues.append("tls_disabled")

    # 2. Input validation must be enabled
    if not config.get("validate_input", True):
        issues.append("validation_disabled")

    # 3. Check validator is functional
    sys.path.insert(0, ".")
    from service.middleware.validator import validate_input
    if not callable(validate_input):
        issues.append("validator_not_callable")

    if issues:
        print(f"SECURITY_FAIL: {{issues}}")
        sys.exit(1)
    else:
        print("SECURITY_PASS: All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    run_security_scan()
'''

        # benchmarks/reliability_test.py
        files["benchmarks/reliability_test.py"] = f'''"""Fault injection test: checks circuit breaker behavior."""
import sys
import os

sys.path.insert(0, ".")


def run_reliability_test():
    """Test circuit breaker behavior."""
    issues = []

    import json
    with open("service/config.json") as f:
        config = json.load(f)

    if not config.get("circuit_breaker_enabled", False):
        issues.append("circuit_breaker_not_enabled")

    from service.middleware.circuit_breaker import call_external_service

    # Test 1: Normal operation should work
    result = call_external_service({{"test": 1}})
    if not isinstance(result, dict):
        issues.append("circuit_breaker_no_response")

    # Test 2: After consecutive failures, circuit should open
    failure_count = 0
    for _ in range(5):
        try:
            call_external_service({{"trigger_fail": True}})
        except Exception:
            failure_count += 1
    if failure_count < {cb_threshold}:
        issues.append("no_circuit_breaker_logic")

    # Test 3: After circuit opens, should reject quickly (not hang)
    import time
    start = time.time()
    try:
        call_external_service({{"test": 2}})
    except Exception:
        pass
    elapsed = time.time() - start
    if elapsed > 0.5:
        issues.append("no_backoff")

    if issues:
        print(f"RELIABILITY_FAIL: {{issues}}")
        sys.exit(1)
    else:
        print("RELIABILITY_PASS: All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    run_reliability_test()
'''

        return files

    def _generate_spec(self, cfg) -> str:
        svc = cfg["service_type"]
        latency = cfg["latency_ms"]
        cb_threshold = cfg["cb_threshold"]
        cb_timeout = cfg["cb_timeout"]
        retry_base = cfg["retry_base_ms"]
        max_retries = cfg["max_retries"]
        return f"""# NEG1: Conflicting Constraints Negotiation

## Goal
Configure and fix the {svc} HTTP service so it simultaneously satisfies performance, security, and reliability requirements.

## Three Constraint Categories (ALL must pass)

### Performance
- p95 latency must be < {latency}ms per request
- The current implementation is significantly slower than this threshold due to the input validation step
- **Constraint**: Validation must not be disabled — the solution must make validation fast enough to meet the latency target, not skip it

### Security
- All inputs must be validated before processing (validation cannot be disabled or bypassed)
- TLS must be enabled for all connections
- No plaintext credentials may appear in config files or source code
- Session tokens must be generated using a cryptographically secure method

### Reliability
- External service calls must be wrapped with a circuit breaker
- Failed requests must be retried with exponential backoff: base delay of {retry_base}ms, maximum of {max_retries} retry attempts
- The circuit breaker must open after {cb_threshold} consecutive failures and remain open for {cb_timeout} seconds before attempting recovery

## Common Traps
- Disabling validation satisfies the performance requirement but violates security
- Enabling all features without optimizing validation satisfies security but fails the performance benchmark
- Implementing only the circuit breaker satisfies reliability but leaves performance and security unaddressed

## Deliverables
- Fixed service code meeting all 3 constraint categories
- All 3 benchmarks pass simultaneously
"""

    def _generate_brief(self, cfg) -> str:
        svc = cfg["service_type"]
        latency = cfg["latency_ms"]
        return f"""# NEG1: Conflicting Constraints Negotiation (Brief)

Fix the {svc} to simultaneously satisfy performance (p95 < {latency}ms), security (TLS + validation), and reliability (circuit breaker + retry).
The key tension: validation is required but currently too slow.
Run benchmarks: `python benchmarks/perf_test.py`, `python benchmarks/security_scan.py`, `python benchmarks/reliability_test.py`
"""
