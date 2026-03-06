"""
Parameterized generator for MULTI2: Microservice Debug.

Each seed produces a 3-service system (Python Flask API + Go worker + Node.js proxy)
with 4 bugs: wrong date format, off-by-one in batch loop, wrong header forwarding,
and config type bug (string instead of int).
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized pools ─────────────────────────────────────────────

SERVICE_NAMES = [
    "analytics-platform",
    "inventory-tracker",
    "notification-hub",
    "payment-gateway",
    "reporting-engine",
]

API_ENDPOINTS = [
    {"path": "/parse-date", "entity": "event", "field": "event_date"},
    {"path": "/parse-date", "entity": "record", "field": "record_date"},
    {"path": "/parse-date", "entity": "entry", "field": "entry_date"},
    {"path": "/parse-date", "entity": "log", "field": "log_date"},
    {"path": "/parse-date", "entity": "transaction", "field": "txn_date"},
]

# Date format pairs: (buggy_format, correct_format, sample_valid, sample_invalid_for_buggy)
DATE_FORMATS = [
    ("%d/%m/%Y", "%Y-%m-%d", "2024-03-15", "15/03/2024"),
    ("%m-%d-%Y", "%Y-%m-%d", "2024-06-20", "06-20-2024"),
    ("%Y/%m/%d", "%Y-%m-%dT%H:%M:%SZ", "2024-01-10T10:30:00Z", "2024/01/10"),
    ("%d-%b-%Y", "%Y-%m-%d", "2024-11-05", "05-Nov-2024"),
    ("%Y%m%d", "%Y-%m-%d", "2024-08-22", "20240822"),
]

PORT_SETS = [
    {"api": 5001, "proxy": 3001, "worker_batch": 10},
    {"api": 5002, "proxy": 3002, "worker_batch": 15},
    {"api": 5003, "proxy": 3003, "worker_batch": 20},
    {"api": 8081, "proxy": 4001, "worker_batch": 25},
    {"api": 8082, "proxy": 4002, "worker_batch": 12},
]

LOG_LEVELS = ["info", "debug", "warning", "error", "trace"]

QUEUE_RECORD_SETS = [
    ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"],
    ["mercury", "venus", "earth", "mars", "jupiter", "saturn"],
    ["apple", "banana", "cherry", "date", "elderberry", "fig"],
    ["north", "south", "east", "west", "center", "origin"],
    ["red", "orange", "yellow", "green", "blue", "purple"],
]

HEADER_BUGS = [
    {"buggy": "'Basic ' + apiKey", "correct": "req.headers['authorization']",
     "buggy_desc": "hardcodes Basic prefix instead of forwarding original"},
    {"buggy": "'Bearer hardcoded-token'", "correct": "req.headers.authorization",
     "buggy_desc": "hardcodes a static Bearer token"},
    {"buggy": "'Token ' + req.headers['x-api-key']", "correct": "req.headers['authorization']",
     "buggy_desc": "reads wrong header (x-api-key) with wrong prefix"},
    {"buggy": "req.headers['x-auth']", "correct": "req.headers['authorization']",
     "buggy_desc": "reads non-standard x-auth header"},
    {"buggy": "'ApiKey ' + (req.headers['authorization'] || '').split(' ')[1]",
     "correct": "req.headers['authorization']",
     "buggy_desc": "mangles the Authorization header by extracting and re-prefixing"},
]


class Generator(TaskGenerator):
    task_id = "MULTI2_microservice_debug"
    domain = "Multi-lang"
    difficulty = "hard"
    languages = ["python", "go", "javascript"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        svc_name = SERVICE_NAMES[seed % len(SERVICE_NAMES)]
        api_ep = API_ENDPOINTS[seed % len(API_ENDPOINTS)]
        date_fmt = DATE_FORMATS[seed % len(DATE_FORMATS)]
        ports = PORT_SETS[seed % len(PORT_SETS)]
        log_level = LOG_LEVELS[seed % len(LOG_LEVELS)]
        records = QUEUE_RECORD_SETS[seed % len(QUEUE_RECORD_SETS)]
        header_bug = HEADER_BUGS[seed % len(HEADER_BUGS)]

        buggy_fmt, correct_fmt, sample_valid, sample_buggy = date_fmt
        api_port = ports["api"]
        proxy_port = ports["proxy"]
        batch_size = ports["worker_batch"]

        workspace_files = self._make_workspace(
            svc_name=svc_name,
            api_ep=api_ep,
            buggy_fmt=buggy_fmt,
            correct_fmt=correct_fmt,
            sample_valid=sample_valid,
            api_port=api_port,
            proxy_port=proxy_port,
            batch_size=batch_size,
            log_level=log_level,
            records=records,
            header_bug=header_bug,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "MULTI2_microservice_debug")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="MULTI2_microservice_debug",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "correct_date_format": correct_fmt,
                "buggy_date_format": buggy_fmt,
                "config_retry_timeout": 30,
                "batch_size": batch_size,
                "record_count": len(records),
                "header_fix": "forward original Authorization header",
                "service_name": svc_name,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Multi-language"},
        )

    def _make_workspace(
        self,
        svc_name: str,
        api_ep: dict,
        buggy_fmt: str,
        correct_fmt: str,
        sample_valid: str,
        api_port: int,
        proxy_port: int,
        batch_size: int,
        log_level: str,
        records: list,
        header_bug: dict,
    ) -> dict:
        files = {}
        entity = api_ep["entity"]
        date_field = api_ep["field"]
        path = api_ep["path"]

        # ── config.json (BUG: retry_timeout is string "30" not int 30) ──
        files["config.json"] = (
            '{\n'
            f'  "service_name": "{svc_name}",\n'
            f'  "port": {api_port},\n'
            f'  "retry_timeout": "30",\n'
            f'  "log_level": "{log_level}",\n'
            f'  "batch_size": {batch_size},\n'
            '  "max_retries": 3\n'
            '}\n'
        )

        # ── API_SPEC.md ──────────────────────────────────────────────────
        files["API_SPEC.md"] = (
            f"# {svc_name} API Specification\n\n"
            f"## POST {path}\n\n"
            f"Parse a date string from the request body.\n\n"
            f"### Request Body\n\n"
            f"```json\n"
            f'{{"date": "{sample_valid}"}}\n'
            f"```\n\n"
            f"### Date Format\n\n"
            f"The API accepts dates in **`{correct_fmt}`** format.\n"
            f"Example valid date: `{sample_valid}`\n\n"
            f"### Responses\n\n"
            f"- **200 OK**: `{{\"parsed\": \"<date>\", \"{date_field}\": \"<date>\"}}`\n"
            f"- **400 Bad Request**: `{{\"error\": \"Invalid date format\"}}`\n\n"
            f"### Configuration\n\n"
            f"- `retry_timeout` in config.json must be an integer (seconds)\n"
            f"- All services read this value for HTTP timeout configuration\n"
        )

        # ── api/app.py (BUG: wrong date format string) ──────────────────
        files["api/app.py"] = (
            f'"""\n'
            f'{svc_name} — Flask REST API.\n'
            f'"""\n'
            f'import json\n'
            f'from datetime import datetime\n'
            f'from flask import Flask, request, jsonify\n'
            f'\n'
            f'app = Flask(__name__)\n'
            f'\n'
            f'# Load config\n'
            f'with open("../config.json") as _f:\n'
            f'    _config = json.load(_f)\n'
            f'\n'
            f'RETRY_TIMEOUT = int(_config["retry_timeout"])  # Works if int, fails silently if string "30"\n'
            f'\n'
            f'\n'
            f'@app.route("{path}", methods=["POST"])\n'
            f'def parse_date():\n'
            f'    """Parse a date string from the request body."""\n'
            f'    data = request.get_json(silent=True) or {{}}\n'
            f'    date_str = data.get("date", "")\n'
            f'    if not date_str:\n'
            f'        return jsonify({{"error": "date field is required"}}), 400\n'
            f'    try:\n'
            f'        parsed = datetime.strptime(date_str, "{buggy_fmt}")  # BUG: wrong format\n'
            f'        return jsonify({{\n'
            f'            "parsed": parsed.isoformat(),\n'
            f'            "{date_field}": parsed.strftime("%Y-%m-%d"),\n'
            f'        }}), 200\n'
            f'    except ValueError:\n'
            f'        return jsonify({{"error": "Invalid date format"}}), 400\n'
            f'\n'
            f'\n'
            f'@app.route("/health")\n'
            f'def health():\n'
            f'    return jsonify({{"status": "ok", "service": "{svc_name}"}})\n'
            f'\n'
            f'\n'
            f'if __name__ == "__main__":\n'
            f'    app.run(port={api_port})\n'
        )

        # ── api/requirements.txt ─────────────────────────────────────────
        files["api/requirements.txt"] = "flask\npytest\n"

        # ── worker/main.go (BUG: off-by-one in batch loop) ──────────────
        records_go_init = ""
        for r in records:
            records_go_init += f'\t\t"{r}",\n'

        files["worker/main.go"] = (
            'package main\n'
            '\n'
            'import (\n'
            '\t"encoding/json"\n'
            '\t"fmt"\n'
            '\t"os"\n'
            '\t"strconv"\n'
            ')\n'
            '\n'
            'type Config struct {\n'
            '\tServiceName  string `json:"service_name"`\n'
            '\tBatchSize    int    `json:"batch_size"`\n'
            '\tRetryTimeout int    `json:"retry_timeout"`\n'
            '}\n'
            '\n'
            'func loadConfig(path string) (Config, error) {\n'
            '\tdata, err := os.ReadFile(path)\n'
            '\tif err != nil {\n'
            '\t\treturn Config{}, err\n'
            '\t}\n'
            '\t// Parse retry_timeout which might be a string\n'
            '\tvar raw map[string]interface{}\n'
            '\tif err := json.Unmarshal(data, &raw); err != nil {\n'
            '\t\treturn Config{}, err\n'
            '\t}\n'
            '\tcfg := Config{}\n'
            '\tif v, ok := raw["service_name"].(string); ok {\n'
            '\t\tcfg.ServiceName = v\n'
            '\t}\n'
            '\tif v, ok := raw["batch_size"].(float64); ok {\n'
            '\t\tcfg.BatchSize = int(v)\n'
            '\t}\n'
            '\t// retry_timeout: handle both string and number\n'
            '\tswitch v := raw["retry_timeout"].(type) {\n'
            '\tcase float64:\n'
            '\t\tcfg.RetryTimeout = int(v)\n'
            '\tcase string:\n'
            '\t\tcfg.RetryTimeout, _ = strconv.Atoi(v)\n'
            '\t}\n'
            '\treturn cfg, nil\n'
            '}\n'
            '\n'
            'func processRecords(records []string, batchSize int, dryRun bool) int {\n'
            '\tprocessed := 0\n'
            '\tfor start := 0; start < len(records); start += batchSize {\n'
            '\t\tend := start + batchSize\n'
            '\t\tif end > len(records) {\n'
            '\t\t\tend = len(records)\n'
            '\t\t}\n'
            '\t\t// BUG: off-by-one — should be i < end, but uses i < end-1\n'
            '\t\t// This skips the last record in each batch\n'
            '\t\tfor i := start; i < end-1; i++ {\n'
            '\t\t\tif dryRun {\n'
            '\t\t\t\tfmt.Printf("Processing: %s\\n", records[i])\n'
            '\t\t\t}\n'
            '\t\t\tprocessed++\n'
            '\t\t}\n'
            '\t}\n'
            '\treturn processed\n'
            '}\n'
            '\n'
            'func main() {\n'
            '\tdryRun := false\n'
            '\tfor _, arg := range os.Args[1:] {\n'
            '\t\tif arg == "--dry-run" {\n'
            '\t\t\tdryRun = true\n'
            '\t\t}\n'
            '\t}\n'
            '\n'
            '\tcfg, err := loadConfig("../config.json")\n'
            '\tif err != nil {\n'
            '\t\tfmt.Fprintf(os.Stderr, "Config error: %v\\n", err)\n'
            '\t\tos.Exit(1)\n'
            '\t}\n'
            '\n'
            '\trecords := []string{\n'
            f'{records_go_init}'
            '\t}\n'
            '\n'
            '\tcount := processRecords(records, cfg.BatchSize, dryRun)\n'
            '\tfmt.Printf("Processed %d/%d records (batch_size=%d)\\n", count, len(records), cfg.BatchSize)\n'
            '\tif count != len(records) {\n'
            '\t\tfmt.Fprintf(os.Stderr, "ERROR: expected %d, processed %d\\n", len(records), count)\n'
            '\t\tos.Exit(1)\n'
            '\t}\n'
            '}\n'
        )

        files["worker/go.mod"] = (
            f'module {svc_name.replace("-", "_")}_worker\n\ngo 1.21\n'
        )

        # ── proxy/server.js (BUG: wrong header forwarding) ──────────────
        files["proxy/server.js"] = (
            'const http = require("http");\n'
            '\n'
            f'const API_PORT = {api_port};\n'
            f'const PROXY_PORT = {proxy_port};\n'
            '\n'
            'const server = http.createServer((req, res) => {\n'
            '  const options = {\n'
            '    hostname: "localhost",\n'
            f'    port: API_PORT,\n'
            '    path: req.url,\n'
            '    method: req.method,\n'
            '    headers: {\n'
            '      "Content-Type": "application/json",\n'
            f'      // BUG: {header_bug["buggy_desc"]}\n'
            f'      "Authorization": {header_bug["buggy"]},\n'
            '    },\n'
            '  };\n'
            '\n'
            '  const proxyReq = http.request(options, (proxyRes) => {\n'
            '    res.writeHead(proxyRes.statusCode, proxyRes.headers);\n'
            '    proxyRes.pipe(res);\n'
            '  });\n'
            '\n'
            '  proxyReq.on("error", (err) => {\n'
            '    res.writeHead(502);\n'
            '    res.end(JSON.stringify({ error: "Proxy error: " + err.message }));\n'
            '  });\n'
            '\n'
            '  req.pipe(proxyReq);\n'
            '});\n'
            '\n'
            f'server.listen(PROXY_PORT, () => {{\n'
            f'  console.log(`Proxy listening on port ${{PROXY_PORT}}, forwarding to ${{API_PORT}}`);\n'
            '});\n'
        )

        # ── proxy/package.json ───────────────────────────────────────────
        files["proxy/package.json"] = (
            '{\n'
            f'  "name": "{svc_name}-proxy",\n'
            '  "version": "1.0.0",\n'
            '  "main": "server.js"\n'
            '}\n'
        )

        # ── tests/test_api.py ────────────────────────────────────────────
        files["tests/test_api.py"] = (
            'import sys\n'
            'import os\n'
            'sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))\n'
            'import pytest\n'
            '\n'
            '\n'
            '@pytest.fixture\n'
            'def client():\n'
            '    # Change to api/ dir so config.json relative path works\n'
            '    orig = os.getcwd()\n'
            '    os.chdir(os.path.join(os.path.dirname(__file__), "..", "api"))\n'
            '    from app import app\n'
            '    app.config["TESTING"] = True\n'
            '    with app.test_client() as c:\n'
            '        yield c\n'
            '    os.chdir(orig)\n'
            '\n'
            '\n'
            f'def test_valid_date_accepted(client):\n'
            f'    """Valid date must return 200."""\n'
            f'    r = client.post("{path}", json={{"date": "{sample_valid}"}})\n'
            f'    assert r.status_code == 200, f"Expected 200, got {{r.status_code}}"\n'
            '\n'
            '\n'
            f'def test_invalid_date_rejected(client):\n'
            f'    """Invalid date must return 400."""\n'
            f'    r = client.post("{path}", json={{"date": "not-a-date"}})\n'
            f'    assert r.status_code == 400, f"Expected 400, got {{r.status_code}}"\n'
            '\n'
            '\n'
            f'def test_missing_date_rejected(client):\n'
            f'    """Missing date field must return 400."""\n'
            f'    r = client.post("{path}", json={{}})\n'
            f'    assert r.status_code == 400\n'
            '\n'
            '\n'
            f'def test_parsed_date_in_response(client):\n'
            f'    """Response must contain parsed date fields."""\n'
            f'    r = client.post("{path}", json={{"date": "{sample_valid}"}})\n'
            f'    assert r.status_code == 200\n'
            f'    data = r.get_json()\n'
            f'    assert "parsed" in data\n'
            f'    assert "{date_field}" in data\n'
        )

        # ── tests/validate_config.py ─────────────────────────────────────
        files["tests/validate_config.py"] = (
            'import json\n'
            'import sys\n'
            'import os\n'
            '\n'
            'config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")\n'
            'cfg = json.load(open(config_path))\n'
            '\n'
            'errors = []\n'
            'if not isinstance(cfg.get("retry_timeout"), int):\n'
            '    errors.append("retry_timeout must be an integer")\n'
            'if not isinstance(cfg.get("port"), int):\n'
            '    errors.append("port must be an integer")\n'
            'if not isinstance(cfg.get("service_name"), str):\n'
            '    errors.append("service_name must be a string")\n'
            '\n'
            'if errors:\n'
            '    for e in errors:\n'
            '        print(f"ERROR: {e}", file=sys.stderr)\n'
            '    sys.exit(1)\n'
            'else:\n'
            '    print("Config validation passed")\n'
        )

        # ── tests/test_worker.sh ─────────────────────────────────────────
        records_str = " ".join(records)
        files["tests/test_worker.sh"] = (
            '#!/usr/bin/env bash\n'
            'set -euo pipefail\n'
            'cd "$(dirname "$0")/../worker"\n'
            'go build -o /tmp/multi2_test_worker . 2>/dev/null\n'
            'output=$(/tmp/multi2_test_worker --dry-run 2>&1)\n'
            f'expected_count={len(records)}\n'
            'actual_count=$(echo "$output" | grep -c "Processing:" || true)\n'
            'if [ "$actual_count" -eq "$expected_count" ]; then\n'
            '    echo "PASS: processed $actual_count/$expected_count records"\n'
            'else\n'
            '    echo "FAIL: processed $actual_count/$expected_count records"\n'
            '    exit 1\n'
            'fi\n'
        )

        # ── tests/test_proxy.js ──────────────────────────────────────────
        files["tests/test_proxy.js"] = (
            '// Basic syntax and structure check for proxy/server.js\n'
            'const fs = require("fs");\n'
            'const path = require("path");\n'
            '\n'
            'const src = fs.readFileSync(\n'
            '  path.join(__dirname, "..", "proxy", "server.js"),\n'
            '  "utf8"\n'
            ');\n'
            '\n'
            '// Check that the proxy reads the original Authorization header\n'
            'if (\n'
            '  src.includes(\'req.headers["authorization"]\') ||\n'
            '  src.includes("req.headers[\'authorization\']") ||\n'
            '  src.includes("req.headers.authorization")\n'
            ') {\n'
            '  console.log("PASS: proxy forwards original Authorization header");\n'
            '} else {\n'
            '  console.error("FAIL: proxy does not forward original Authorization header");\n'
            '  process.exit(1);\n'
            '}\n'
        )

        return files
