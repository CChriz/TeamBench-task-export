"""
Parameterized generator for TEST7: Integration Test Suite.

Each seed produces:
- 3 Python services (user_service, order_service, payment_service) with
  local test server fixtures
- An api_contracts.md documenting expected request/response formats
- 8 contract violations embedded across the services
- An empty tests/test_integration.py for the agent to fill in

Seed variation:
  - Different service domain names (user/order/payment vs account/booking/billing etc.)
  - Different endpoint paths and field names
  - Different violation types and locations (always 8 total)

TNI driver (Pattern D + C):
  - Brief: "Write integration tests for the 3 services"
  - Spec: Full contract docs + violation hints for Planner
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Service domain pools ───────────────────────────────────────────────────

SERVICE_SETS = [
    {
        "svc1": ("user_service", "User", "users", "user_id"),
        "svc2": ("order_service", "Order", "orders", "order_id"),
        "svc3": ("payment_service", "Payment", "payments", "payment_id"),
        "port1": 5001, "port2": 5002, "port3": 5003,
    },
    {
        "svc1": ("account_service", "Account", "accounts", "account_id"),
        "svc2": ("booking_service", "Booking", "bookings", "booking_id"),
        "svc3": ("billing_service", "Billing", "bills", "bill_id"),
        "port1": 6001, "port2": 6002, "port3": 6003,
    },
    {
        "svc1": ("customer_service", "Customer", "customers", "customer_id"),
        "svc2": ("inventory_service", "Inventory", "items", "item_id"),
        "svc3": ("invoice_service", "Invoice", "invoices", "invoice_id"),
        "port1": 7001, "port2": 7002, "port3": 7003,
    },
]

# Violation pool: always pick 8 per seed
# (violation_id, category, description)
VIOLATION_POOL = [
    ("V1_wrong_status_create", "status_code", "Create endpoint returns 200 instead of 201"),
    ("V2_wrong_status_not_found", "status_code", "Not-found returns 500 instead of 404"),
    ("V3_missing_field_response", "response_schema", "Response missing required 'created_at' field"),
    ("V4_wrong_field_name", "response_schema", "Response uses 'userId' instead of 'user_id'"),
    ("V5_wrong_error_format", "error_format", "Error response is plain text instead of JSON {error, code}"),
    ("V6_missing_content_type", "headers", "Response missing Content-Type: application/json header"),
    ("V7_timeout_no_error", "error_handling", "Service hangs instead of returning 504 on dependency timeout"),
    ("V8_cascade_no_check", "contract", "Order service doesn't verify user exists before creating order"),
    ("V9_wrong_delete_status", "status_code", "Delete returns 200 with body instead of 204 No Content"),
    ("V10_missing_pagination", "response_schema", "List endpoint returns all items without pagination"),
    ("V11_wrong_error_code", "error_format", "Validation error returns 500 instead of 422"),
    ("V12_inconsistent_id_format", "contract", "Payment uses numeric ID while order uses string UUID"),
]


class Generator(TaskGenerator):
    task_id = "TEST7_integration_suite"
    domain = "testing"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        svc_set = SERVICE_SETS[seed % len(SERVICE_SETS)]

        # Pick 8 violations from pool
        violation_indices = rng.sample(list(range(len(VIOLATION_POOL))), 8)
        violations = [VIOLATION_POOL[i] for i in violation_indices]

        workspace_files = self._make_workspace(svc_set, violations)

        expected = {
            "seed": seed,
            "service_set": {
                "svc1": svc_set["svc1"][0],
                "svc2": svc_set["svc2"][0],
                "svc3": svc_set["svc3"][0],
            },
            "violations": [{"id": v[0], "cat": v[1], "desc": v[2]} for v in violations],
            "violation_count": 8,
        }

        spec_md = self._generate_spec(svc_set, violations)
        brief_md = self._generate_brief(svc_set)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_workspace(self, svc: dict, violations: list) -> dict:
        files = {}
        viol_ids = {v[0] for v in violations}

        s1_mod, s1_cls, s1_coll, s1_id = svc["svc1"]
        s2_mod, s2_cls, s2_coll, s2_id = svc["svc2"]
        s3_mod, s3_cls, s3_coll, s3_id = svc["svc3"]
        p1, p2, p3 = svc["port1"], svc["port2"], svc["port3"]

        files[f"{s1_mod}.py"] = self._gen_service1(
            s1_mod, s1_cls, s1_coll, s1_id, p1, viol_ids
        )
        files[f"{s2_mod}.py"] = self._gen_service2(
            s2_mod, s2_cls, s2_coll, s2_id, p2,
            s1_mod, s1_coll, s1_id, p1, viol_ids
        )
        files[f"{s3_mod}.py"] = self._gen_service3(
            s3_mod, s3_cls, s3_coll, s3_id, p3,
            s2_mod, s2_coll, s2_id, p2, viol_ids
        )
        files["api_contracts.md"] = self._gen_contracts(
            s1_mod, s1_cls, s1_coll, s1_id,
            s2_mod, s2_cls, s2_coll, s2_id,
            s3_mod, s3_cls, s3_coll, s3_id,
        )
        files["tests/__init__.py"] = ""
        files["tests/test_integration.py"] = self._gen_test_skeleton(
            s1_mod, s2_mod, s3_mod
        )
        files["requirements.txt"] = "flask>=2.3.0\npytest>=7.0.0\nrequests>=2.28.0\n"

        return files

    def _gen_service1(
        self, mod: str, cls: str, coll: str, id_f: str, port: int, bugs: set
    ) -> str:
        # Status code for create
        create_status = 200 if "V1_wrong_status_create" in bugs else 201

        # Not-found status
        notfound_status = 500 if "V2_wrong_status_not_found" in bugs else 404

        # Response field name
        id_resp_field = "userId" if "V4_wrong_field_name" in bugs else id_f

        # Error format
        if "V5_wrong_error_format" in bugs:
            error_return = f'return "Not found", {notfound_status}'
        else:
            error_return = f'return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), {notfound_status}'

        # Created_at field
        created_at_line = ""
        if "V3_missing_field_response" not in bugs:
            created_at_line = f'\n        "{coll[:-1]}["created_at"] = datetime.utcnow().isoformat() + "Z"'

        # Delete status
        if "V9_wrong_delete_status" in bugs:
            delete_return = f'return jsonify({{"deleted": True}}), 200'
        else:
            delete_return = 'return "", 204'

        # Pagination
        if "V10_missing_pagination" in bugs:
            list_body = f"""    items = list(_{coll}.values())
    return jsonify({{"{coll}": items}})"""
        else:
            list_body = f"""    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    items = list(_{coll}.values())
    start = (page - 1) * per_page
    sliced = items[start:start + per_page]
    return jsonify({{"{coll}": sliced, "page": page, "per_page": per_page, "total": len(items)}})"""

        return f'''"""{cls} Service — CRUD operations for {coll}."""
from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)
_{coll} = {{}}


@app.route("/{coll}", methods=["POST"])
def create_{coll[:-1]}():
    data = request.get_json(force=True) or {{}}
    if "name" not in data:
        return jsonify({{"error": "name required", "code": "VALIDATION_ERROR"}}), 400
    rid = str(uuid.uuid4())
    record = {{
        "{id_resp_field}": rid,
        "name": data["name"],
        "email": data.get("email", ""),
        "status": "active",
    }}{created_at_line}
    _{coll}[rid] = record
    return jsonify(record), {create_status}


@app.route("/{coll}", methods=["GET"])
def list_{coll}():
{list_body}


@app.route("/{coll}/<item_id>", methods=["GET"])
def get_{coll[:-1]}(item_id):
    record = _{coll}.get(item_id)
    if record is None:
        {error_return}
    return jsonify(record)


@app.route("/{coll}/<item_id>", methods=["DELETE"])
def delete_{coll[:-1]}(item_id):
    record = _{coll}.pop(item_id, None)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    {delete_return}


@app.route("/{coll}/<item_id>", methods=["PUT"])
def update_{coll[:-1]}(item_id):
    record = _{coll}.get(item_id)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    data = request.get_json(force=True) or {{}}
    record.update({{k: v for k, v in data.items() if k != "{id_f}"}})
    return jsonify(record)


if __name__ == "__main__":
    app.run(port={port})
'''

    def _gen_service2(
        self, mod: str, cls: str, coll: str, id_f: str, port: int,
        s1_mod: str, s1_coll: str, s1_id: str, s1_port: int,
        bugs: set,
    ) -> str:
        # V8: doesn't check if user exists
        if "V8_cascade_no_check" in bugs:
            user_check = f"""    # NOTE: should verify {s1_coll[:-1]} exists but doesn't
    pass"""
        else:
            user_check = f"""    # Verify {s1_coll[:-1]} exists
    import requests as req
    try:
        resp = req.get(f"http://localhost:{s1_port}/{s1_coll}/{{data.get('{s1_id}', '')}}", timeout=5)
        if resp.status_code != 200:
            return jsonify({{"error": "{s1_coll[:-1]} not found", "code": "DEPENDENCY_ERROR"}}), 422
    except req.RequestException:
        return jsonify({{"error": "{s1_coll[:-1]} service unavailable", "code": "SERVICE_UNAVAILABLE"}}), 503"""

        # V11: validation error returns 500 instead of 422
        validation_error_code = 500 if "V11_wrong_error_code" in bugs else 422

        # V7: timeout handling
        if "V7_timeout_no_error" in bugs:
            timeout_handling = """    # No timeout handling implemented"""
        else:
            timeout_handling = """    # Timeout handling: returns 504 if dependency is slow"""

        return f'''"""{cls} Service — manages {coll} referencing {s1_coll}."""
from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)
_{coll} = {{}}


@app.route("/{coll}", methods=["POST"])
def create_{coll[:-1]}():
    data = request.get_json(force=True) or {{}}
    if "{s1_id}" not in data:
        return jsonify({{"error": "{s1_id} required", "code": "VALIDATION_ERROR"}}), {validation_error_code}
{user_check}
    rid = str(uuid.uuid4())
    record = {{
        "{id_f}": rid,
        "{s1_id}": data["{s1_id}"],
        "items": data.get("items", []),
        "total": data.get("total", 0),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }}
    _{coll}[rid] = record
    return jsonify(record), 201

{timeout_handling}

@app.route("/{coll}", methods=["GET"])
def list_{coll}():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    items = list(_{coll}.values())
    start = (page - 1) * per_page
    sliced = items[start:start + per_page]
    return jsonify({{"{coll}": sliced, "page": page, "per_page": per_page, "total": len(items)}})


@app.route("/{coll}/<item_id>", methods=["GET"])
def get_{coll[:-1]}(item_id):
    record = _{coll}.get(item_id)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    return jsonify(record)


@app.route("/{coll}/<item_id>/status", methods=["PUT"])
def update_{coll[:-1]}_status(item_id):
    record = _{coll}.get(item_id)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    data = request.get_json(force=True) or {{}}
    record["status"] = data.get("status", record["status"])
    return jsonify(record)


if __name__ == "__main__":
    app.run(port={port})
'''

    def _gen_service3(
        self, mod: str, cls: str, coll: str, id_f: str, port: int,
        s2_mod: str, s2_coll: str, s2_id: str, s2_port: int,
        bugs: set,
    ) -> str:
        # V12: inconsistent ID format
        if "V12_inconsistent_id_format" in bugs:
            id_gen = f"""    global _counter
    _counter += 1
    rid = _counter"""
            id_init = "\n_counter = 0"
        else:
            id_gen = '    rid = str(uuid.uuid4())'
            id_init = ""

        # V6: missing content-type
        if "V6_missing_content_type" in bugs:
            response_note = "    # NOTE: some responses may not set Content-Type correctly"
        else:
            response_note = ""

        return f'''"""{cls} Service — processes {coll} for {s2_coll}."""
from flask import Flask, request, jsonify, make_response
from datetime import datetime
import uuid

app = Flask(__name__)
_{coll} = {{}}{id_init}


@app.route("/{coll}", methods=["POST"])
def create_{coll[:-1]}():
    data = request.get_json(force=True) or {{}}
    if "{s2_id}" not in data or "amount" not in data:
        return jsonify({{"error": "{s2_id} and amount required", "code": "VALIDATION_ERROR"}}), 422
{id_gen}
    record = {{
        "{id_f}": rid,
        "{s2_id}": data["{s2_id}"],
        "amount": data["amount"],
        "currency": data.get("currency", "USD"),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }}
    _{coll}[str(rid)] = record
    return jsonify(record), 201


@app.route("/{coll}/<item_id>", methods=["GET"])
def get_{coll[:-1]}(item_id):
{response_note}
    record = _{coll}.get(item_id)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    return jsonify(record)


@app.route("/{coll}/<item_id>/confirm", methods=["POST"])
def confirm_{coll[:-1]}(item_id):
    record = _{coll}.get(item_id)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    record["status"] = "confirmed"
    record["confirmed_at"] = datetime.utcnow().isoformat() + "Z"
    return jsonify(record)


@app.route("/{coll}/<item_id>/refund", methods=["POST"])
def refund_{coll[:-1]}(item_id):
    record = _{coll}.get(item_id)
    if record is None:
        return jsonify({{"error": "Not found", "code": "NOT_FOUND"}}), 404
    if record["status"] != "confirmed":
        return jsonify({{"error": "Can only refund confirmed {coll}", "code": "INVALID_STATE"}}), 422
    record["status"] = "refunded"
    return jsonify(record)


if __name__ == "__main__":
    app.run(port={port})
'''

    def _gen_contracts(
        self,
        s1_mod: str, s1_cls: str, s1_coll: str, s1_id: str,
        s2_mod: str, s2_cls: str, s2_coll: str, s2_id: str,
        s3_mod: str, s3_cls: str, s3_coll: str, s3_id: str,
    ) -> str:
        return f"""# API Contracts

## Service Architecture
Three services communicate via HTTP REST APIs:
- **{s1_cls} Service** ({s1_mod}.py) - manages {s1_coll}
- **{s2_cls} Service** ({s2_mod}.py) - manages {s2_coll}, references {s1_coll}
- **{s3_cls} Service** ({s3_mod}.py) - manages {s3_coll}, references {s2_coll}

## Contract: {s1_cls} Service

### POST /{s1_coll}
- Request: `{{"name": "string", "email": "string"}}`
- Response: `201 Created` with `{{"{s1_id}": "uuid", "name": "...", "email": "...", "status": "active", "created_at": "ISO8601"}}`
- Error (missing name): `400 Bad Request` with `{{"error": "...", "code": "VALIDATION_ERROR"}}`

### GET /{s1_coll}
- Response: `200 OK` with `{{"{s1_coll}": [...], "page": int, "per_page": int, "total": int}}`

### GET /{s1_coll}/{{id}}
- Response: `200 OK` with record
- Error (not found): `404 Not Found` with `{{"error": "...", "code": "NOT_FOUND"}}`

### DELETE /{s1_coll}/{{id}}
- Response: `204 No Content` (empty body)
- Error (not found): `404 Not Found`

### PUT /{s1_coll}/{{id}}
- Request: JSON fields to update
- Response: `200 OK` with updated record

## Contract: {s2_cls} Service

### POST /{s2_coll}
- Request: `{{"{s1_id}": "uuid", "items": [...], "total": number}}`
- MUST verify {s1_coll[:-1]} exists via `GET /{s1_coll}/{{id}}` before creating
- Response: `201 Created` with `{{"{s2_id}": "uuid", "{s1_id}": "...", ...}}`
- Error (missing {s1_id}): `422 Unprocessable Entity` with `{{"error": "...", "code": "VALIDATION_ERROR"}}`

### GET /{s2_coll}
- Response: `200 OK` with paginated list

### GET /{s2_coll}/{{id}}
- Response: `200 OK` with record

### PUT /{s2_coll}/{{id}}/status
- Request: `{{"status": "string"}}`
- Response: `200 OK` with updated record

## Contract: {s3_cls} Service

### POST /{s3_coll}
- Request: `{{"{s2_id}": "uuid", "amount": number, "currency": "string"}}`
- Response: `201 Created` with `{{"{s3_id}": "uuid", ...}}`
- All IDs must be string UUIDs (consistent format across services)

### GET /{s3_coll}/{{id}}
- Response: `200 OK` with JSON, `Content-Type: application/json`

### POST /{s3_coll}/{{id}}/confirm
- Response: `200 OK` with `{{"status": "confirmed", "confirmed_at": "ISO8601"}}`

### POST /{s3_coll}/{{id}}/refund
- Only allowed when status is "confirmed"
- Error: `422 Unprocessable Entity`

## Cross-Service Requirements
1. All responses MUST be JSON with `Content-Type: application/json`
2. All error responses MUST use format: `{{"error": "description", "code": "ERROR_CODE"}}`
3. All IDs MUST be string UUIDs (not numeric)
4. List endpoints MUST support pagination (`page`, `per_page`)
5. Services MUST verify dependencies exist before creating dependent resources
6. Services MUST return 504 Gateway Timeout when dependencies are unreachable (not hang)
"""

    def _gen_test_skeleton(self, s1_mod: str, s2_mod: str, s3_mod: str) -> str:
        return f'''"""Integration tests for the three-service system.

Write tests that verify the API contracts documented in api_contracts.md.
Focus on detecting contract violations between services.

Run with: python -m pytest tests/test_integration.py -v
"""
import pytest
import json

# Import the Flask apps as test clients
from {s1_mod} import app as app1
from {s2_mod} import app as app2
from {s3_mod} import app as app3


@pytest.fixture
def client1():
    app1.config["TESTING"] = True
    with app1.test_client() as c:
        yield c


@pytest.fixture
def client2():
    app2.config["TESTING"] = True
    with app2.test_client() as c:
        yield c


@pytest.fixture
def client3():
    app3.config["TESTING"] = True
    with app3.test_client() as c:
        yield c


# TODO: Write integration tests that detect the 8 contract violations
# described in api_contracts.md. Each test should verify a specific
# aspect of the contract between services.
'''

    def _generate_spec(self, svc: dict, violations: list) -> str:
        s1_mod = svc["svc1"][0]
        s2_mod = svc["svc2"][0]
        s3_mod = svc["svc3"][0]

        violation_list = "\n".join(
            f"  {i+1}. **{v[0]}** ({v[1]}): {v[2]}" for i, v in enumerate(violations)
        )

        return f"""# TEST7: Integration Test Suite

## Goal
Write integration tests for a three-service system ({s1_mod}, {s2_mod}, {s3_mod})
that detect all 8 contract violations embedded in the service implementations.

## Services
See `api_contracts.md` for the full API contract specification.

## Known Violations
The following 8 contract violations are present in the service code:

{violation_list}

## Strategy
- Use Flask test clients (provided as fixtures) to call each service
- Verify status codes, response schemas, error formats, and cross-service contracts
- Each violation should be detected by at least one test

## Deliverables
- `tests/test_integration.py` with at least 10 test functions
- All 8 violations must be detectable by the test suite
- Run: `python -m pytest tests/test_integration.py -v`
"""

    def _generate_brief(self, svc: dict) -> str:
        s1_mod = svc["svc1"][0]
        s2_mod = svc["svc2"][0]
        s3_mod = svc["svc3"][0]

        return f"""# TEST7: Integration Test Suite (Brief)

Write integration tests for a three-service system:
- `{s1_mod}.py`, `{s2_mod}.py`, `{s3_mod}.py`

See `api_contracts.md` for the expected behavior contracts.
Write your tests in `tests/test_integration.py`.

Install: `pip install -r requirements.txt`
Run: `python -m pytest tests/test_integration.py -v`
"""
