"""
Parameterized generator for INC8: Cascading Timeout.

Each seed produces a 3-service chain (gateway -> order_service -> inventory_service)
with timeout cascade bugs and 4 retry configurations (2 correct, 2 harmful).
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed pools ────────────────────────────────────────────────────────────

SERVICE_NAME_SETS = [
    ("gateway", "order_service", "inventory_service"),
    ("api_gateway", "checkout_service", "stock_service"),
    ("edge_proxy", "booking_service", "availability_service"),
    ("frontend_gw", "billing_service", "catalog_service"),
    ("ingress", "fulfillment_service", "warehouse_service"),
    ("load_balancer", "payment_service", "product_service"),
]

# Broken timeout configs: upstream < downstream (the bug)
TIMEOUT_SETS = [
    (5, 10, 8),    # gw=5 < order=10 (cascade), order=10 > inv=8 (ok)
    (3, 8, 5),     # gw=3 < order=8 (cascade), order=8 > inv=5 (ok)
    (8, 15, 10),   # gw=8 < order=15 (cascade), order=15 > inv=10 (ok)
    (4, 12, 6),    # gw=4 < order=12 (cascade), order=12 > inv=6 (ok)
    (6, 10, 7),    # gw=6 < order=10 (cascade), order=10 > inv=7 (ok)
    (2, 5, 3),     # gw=2 < order=5 (cascade), order=5 > inv=3 (ok)
]

RETRY_COUNTS = [2, 3, 4, 5]

IDEMPOTENT_OPS = [
    ("GET /inventory/check", "GET /health"),
    ("GET /stock/available", "GET /health"),
    ("GET /availability/query", "GET /health"),
    ("GET /catalog/lookup", "GET /health"),
    ("GET /warehouse/status", "GET /health"),
    ("GET /products/info", "GET /health"),
]

HARMFUL_OPS = [
    ("POST /orders/create", "order_service -> inventory_service retry storm"),
    ("POST /checkout/submit", "checkout -> stock retry amplification"),
    ("POST /bookings/reserve", "booking -> availability retry cascade"),
    ("POST /invoices/generate", "billing -> catalog retry amplification"),
    ("POST /shipments/dispatch", "fulfillment -> warehouse retry storm"),
    ("POST /charges/process", "payment -> product retry amplification"),
]

APP_NAMES = [
    "ecommerce_platform", "booking_system", "billing_platform",
    "fulfillment_system", "payment_gateway", "marketplace",
]


class Generator(TaskGenerator):
    task_id = "INC8_cascading_timeout"
    domain = "Incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(SERVICE_NAME_SETS)

        svc_names = SERVICE_NAME_SETS[idx]
        timeouts = TIMEOUT_SETS[idx]
        retry_count = RETRY_COUNTS[seed % len(RETRY_COUNTS)]
        idempotent_ops = IDEMPOTENT_OPS[idx]
        harmful_ops = HARMFUL_OPS[idx]
        app_name = APP_NAMES[seed % len(APP_NAMES)]

        workspace_files = self._make_workspace(
            svc_names=svc_names,
            timeouts=timeouts,
            retry_count=retry_count,
            idempotent_ops=idempotent_ops,
            harmful_ops=harmful_ops,
            app_name=app_name,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "INC8_cascading_timeout")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="INC8_cascading_timeout",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "service_names": list(svc_names),
                "broken_timeouts": {
                    "gateway": timeouts[0],
                    "order_service": timeouts[1],
                    "inventory_service": timeouts[2],
                },
                "correct_retries": list(idempotent_ops),
                "harmful_retries": [harmful_ops[0], harmful_ops[1]],
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Incident"},
        )

    def _make_workspace(
        self,
        svc_names: tuple,
        timeouts: tuple,
        retry_count: int,
        idempotent_ops: tuple,
        harmful_ops: tuple,
        app_name: str,
    ) -> dict:
        files = {}
        gw_name, order_name, inv_name = svc_names
        gw_timeout, order_timeout, inv_timeout = timeouts
        safe_get_op, safe_health_op = idempotent_ops
        harmful_post_op, harmful_storm_desc = harmful_ops

        # ── config.py ────────────────────────────────────────────────────
        files["config.py"] = f"""\
\"\"\"
Service configuration for {app_name}.

TIMEOUT CASCADE BUG: {gw_name} timeout ({gw_timeout}s) < {order_name} timeout ({order_timeout}s).
When {order_name} takes {gw_timeout+1}-{order_timeout}s to respond, {gw_name} times out first,
returning an error while {order_name} continues processing (zombie request).
\"\"\"

# Timeout configuration (seconds)
# TODO: fix timeout hierarchy — upstream must be >= downstream
GATEWAY_TIMEOUT = {gw_timeout}  # Bug: should be >= ORDER_SERVICE_TIMEOUT
ORDER_SERVICE_TIMEOUT = {order_timeout}  # downstream of gateway
INVENTORY_SERVICE_TIMEOUT = {inv_timeout}  # downstream of order_service

# Retry configuration for {gw_name}
GATEWAY_RETRY_CONFIG = {{
    "GET": {{
        "enabled": True,
        "max_retries": {retry_count},
        "description": "{safe_get_op} — idempotent, safe to retry",
    }},
    "health": {{
        "enabled": True,
        "max_retries": 2,
        "description": "{safe_health_op} — stateless, safe to retry",
    }},
    "POST": {{
        "enabled": True,  # Bug: non-idempotent POST should NOT retry
        "max_retries": {retry_count},
        "description": "{harmful_post_op} — NOT idempotent, retry causes double-charge",
    }},
}}

# Retry configuration for {order_name}
ORDER_RETRY_CONFIG = {{
    "GET": {{
        "enabled": True,
        "max_retries": {retry_count},
        "description": "inventory lookup — idempotent, safe to retry",
    }},
    "POST": {{
        "enabled": True,  # Bug: creates retry storm amplification
        "max_retries": {retry_count},
        "description": "{harmful_storm_desc} — amplifies to {retry_count}x{retry_count}={retry_count*retry_count} requests",
    }},
}}
"""

        # ── gateway.py ───────────────────────────────────────────────────
        files["gateway.py"] = f"""\
\"\"\"
{gw_name} — API Gateway for {app_name}.

Routes requests to downstream services with timeout and retry logic.
\"\"\"
import time
import random
from config import GATEWAY_TIMEOUT, GATEWAY_RETRY_CONFIG


class {_class_name(gw_name)}:
    \"\"\"API Gateway that routes requests to {order_name}.\"\"\"

    def __init__(self, downstream_service, timeout=GATEWAY_TIMEOUT):
        self.downstream = downstream_service
        # TODO: timeout should be >= downstream service timeout
        self.timeout = timeout
        self.retry_config = GATEWAY_RETRY_CONFIG

    def handle_request(self, method: str, path: str, body: dict = None) -> dict:
        \"\"\"
        Handle an incoming request by forwarding to downstream.

        Uses timeout and retry based on configuration.
        \"\"\"
        config_key = method.upper()
        if path == "/health":
            config_key = "health"

        retry_cfg = self.retry_config.get(config_key, {{}})
        max_retries = retry_cfg.get("max_retries", 0) if retry_cfg.get("enabled", False) else 0

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = self._call_downstream(method, path, body)
                return {{"status": "success", "data": result, "attempt": attempt + 1}}
            except TimeoutError as e:
                last_error = e
                if attempt < max_retries:
                    continue
            except Exception as e:
                last_error = e
                break

        return {{
            "status": "error",
            "error": str(last_error),
            "attempts": max_retries + 1,
        }}

    def _call_downstream(self, method: str, path: str, body: dict = None) -> dict:
        \"\"\"Call downstream service with timeout.\"\"\"
        start = time.time()
        result = self.downstream.handle_request(method, path, body)
        elapsed = time.time() - start
        if elapsed > self.timeout:
            raise TimeoutError(
                f"{gw_name} timeout after {{elapsed:.1f}}s (limit: {{self.timeout}}s)"
            )
        return result

    def health_check(self) -> dict:
        \"\"\"Check gateway and downstream health.\"\"\"
        return self.handle_request("GET", "/health")
"""

        # ── order_service.py ─────────────────────────────────────────────
        files["order_service.py"] = f"""\
\"\"\"
{order_name} — Order Processing Service for {app_name}.

Processes orders by coordinating with {inv_name}.
\"\"\"
import time
import random
from config import ORDER_SERVICE_TIMEOUT, ORDER_RETRY_CONFIG


class {_class_name(order_name)}:
    \"\"\"Order processing service.\"\"\"

    def __init__(self, inventory_service, timeout=ORDER_SERVICE_TIMEOUT):
        self.inventory = inventory_service
        self.timeout = timeout
        self.retry_config = ORDER_RETRY_CONFIG
        self._orders = {{}}

    def handle_request(self, method: str, path: str, body: dict = None) -> dict:
        \"\"\"Handle request from gateway.\"\"\"
        if path == "/health":
            return {{"service": "{order_name}", "status": "healthy"}}

        if method.upper() == "POST" and path.startswith("/orders"):
            return self._create_order(body or {{}})

        if method.upper() == "GET" and path.startswith("/inventory"):
            return self._check_inventory(body or {{}})

        return {{"error": "not found"}}

    def _create_order(self, body: dict) -> dict:
        \"\"\"
        Create a new order.

        WARNING: This is NOT idempotent. Retrying this operation will create
        duplicate orders and potentially double-charge the customer.
        \"\"\"
        order_id = f"ORD-{{len(self._orders) + 1:04d}}"

        # Check inventory (may be slow)
        config_key = "POST"
        retry_cfg = self.retry_config.get(config_key, {{}})
        max_retries = retry_cfg.get("max_retries", 0) if retry_cfg.get("enabled", False) else 0

        last_error = None
        inventory_result = None
        for attempt in range(max_retries + 1):
            try:
                inventory_result = self._call_inventory("GET", "/check", body)
                break
            except TimeoutError as e:
                last_error = e
                # TODO: retry storm — each retry fans out to inventory_service
                if attempt < max_retries:
                    continue

        if inventory_result is None:
            return {{"error": f"inventory check failed: {{last_error}}"}}

        self._orders[order_id] = {{
            "id": order_id,
            "items": body.get("items", []),
            "status": "confirmed",
            "inventory_check": inventory_result,
        }}

        return {{"order_id": order_id, "status": "confirmed"}}

    def _check_inventory(self, body: dict) -> dict:
        \"\"\"Check inventory availability (idempotent read operation).\"\"\"
        return self._call_inventory("GET", "/check", body)

    def _call_inventory(self, method: str, path: str, body: dict = None) -> dict:
        \"\"\"Call inventory service with timeout.\"\"\"
        start = time.time()
        result = self.inventory.handle_request(method, path, body)
        elapsed = time.time() - start
        if elapsed > self.timeout:
            raise TimeoutError(
                f"{order_name} timeout after {{elapsed:.1f}}s (limit: {{self.timeout}}s)"
            )
        return result
"""

        # ── inventory_service.py ─────────────────────────────────────────
        files["inventory_service.py"] = f"""\
\"\"\"
{inv_name} — Inventory Checking Service for {app_name}.

Provides stock availability data.
\"\"\"
import time
import random
from config import INVENTORY_SERVICE_TIMEOUT


class {_class_name(inv_name)}:
    \"\"\"Inventory service providing stock data.\"\"\"

    def __init__(self, simulated_latency: float = 0.0):
        self.simulated_latency = simulated_latency
        self._stock = {{
            "ITEM-001": 100,
            "ITEM-002": 50,
            "ITEM-003": 0,
            "ITEM-004": 200,
        }}

    def handle_request(self, method: str, path: str, body: dict = None) -> dict:
        \"\"\"Handle request from {order_name}.\"\"\"
        if self.simulated_latency > 0:
            time.sleep(self.simulated_latency)

        if path == "/health":
            return {{"service": "{inv_name}", "status": "healthy"}}

        if method.upper() == "GET" and path == "/check":
            return self._check_stock(body or {{}})

        return {{"error": "not found"}}

    def _check_stock(self, body: dict) -> dict:
        \"\"\"Check stock availability for items.\"\"\"
        items = body.get("items", [])
        results = {{}}
        for item_id in items:
            results[item_id] = {{
                "available": self._stock.get(item_id, 0) > 0,
                "quantity": self._stock.get(item_id, 0),
            }}
        return {{"stock": results}}
"""

        # ── INCIDENT_REPORT.md ───────────────────────────────────────────
        files["INCIDENT_REPORT.md"] = f"""\
# Incident Report: Cascading Timeout Failure

**Date**: 2024-11-15
**Severity**: P1 — Customer Impact
**Duration**: 47 minutes
**Services Affected**: {gw_name}, {order_name}, {inv_name}

## Timeline

- **14:02** — {inv_name} latency increases from ~200ms to ~{gw_timeout+2}s due to
  database connection pool exhaustion.
- **14:03** — {gw_name} starts returning 504 Gateway Timeout to clients because
  its {gw_timeout}s timeout expires before {order_name} can respond.
- **14:04** — {order_name} retries against {inv_name} amplify load: each client
  request generates up to {retry_count*retry_count} calls to {inv_name}.
- **14:08** — {inv_name} enters cascading failure under {retry_count*retry_count}x amplified load.
- **14:15** — On-call paged. Begins investigation.
- **14:32** — Root cause identified: {gw_name} timeout ({gw_timeout}s) < {order_name}
  timeout ({order_timeout}s). Gateway times out first, returning errors to clients while
  {order_name} continues processing orders (zombie requests).
- **14:35** — Additionally identified: POST /orders/create retry causing duplicate
  orders. 23 customers were double-charged.
- **14:49** — Mitigated by increasing {gw_name} timeout to {order_timeout + 5}s and
  disabling POST retries.

## Root Causes

1. **Timeout Cascade**: {gw_name} timeout ({gw_timeout}s) is shorter than {order_name}
   timeout ({order_timeout}s). When {order_name} takes longer than {gw_timeout}s but less
   than {order_timeout}s, the gateway gives up but the downstream keeps processing.

2. **Non-Idempotent Retry**: {harmful_post_op} was configured with retries.
   When a request timed out at the gateway but succeeded downstream, the retry
   created a duplicate order and double-charged the customer.

3. **Retry Storm Amplification**: {order_name} retries {retry_count} times against
   {inv_name}. Combined with {gw_name} retries, a single client request could
   generate {retry_count}x{retry_count}={retry_count*retry_count} calls to {inv_name}.

## Action Items

- [ ] Fix timeout hierarchy: gateway >= order_service >= inventory_service
- [ ] Disable retries for non-idempotent POST operations
- [ ] Add retry budget or circuit breaker to prevent amplification
- [ ] Preserve safe retries for idempotent GET and health checks
"""

        # ── RETRY_POLICY.md ──────────────────────────────────────────────
        files["RETRY_POLICY.md"] = f"""\
# Retry Policy for {app_name}

## Principles

1. **Only retry idempotent operations**. A retry of a non-idempotent operation
   can cause duplicate side effects (double-charge, duplicate records).

2. **Use retry budgets**. Without budgets, retry amplification across service
   layers creates exponential load (N retries at layer 1 x M retries at
   layer 2 = N*M total requests).

3. **Health checks are always safe to retry** (stateless, read-only).

## Idempotent Operations (Safe to Retry)

| Operation | Service | Why Safe |
|-----------|---------|----------|
| {safe_get_op} | {inv_name} | Read-only stock check, no side effects |
| {safe_health_op} | all | Stateless health check |

## Non-Idempotent Operations (DO NOT Retry)

| Operation | Service | Why Unsafe |
|-----------|---------|------------|
| {harmful_post_op} | {order_name} | Creates order + charges customer |
| POST /inventory/reserve | {inv_name} | Decrements stock counter |

## Retry Budget Guidelines

Each service layer should have a maximum total retry count per request.
If a downstream service has already retried N times, the upstream should
NOT add more retries on top.

**Example**: If {order_name} retries {retry_count} times against {inv_name},
{gw_name} should NOT retry the same request, as this amplifies to
{retry_count}x = {retry_count*retry_count} requests.
"""

        # ── tests/__init__.py ────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_services.py ───────────────────────────────────────
        files["tests/test_services.py"] = f"""\
\"\"\"
Tests for the 3-service chain.

These tests verify basic functionality under normal conditions.
They do NOT test timeout cascading or retry amplification edge cases.
\"\"\"
import pytest
from gateway import {_class_name(gw_name)}
from order_service import {_class_name(order_name)}
from inventory_service import {_class_name(inv_name)}


@pytest.fixture
def services():
    inv = {_class_name(inv_name)}()
    order = {_class_name(order_name)}(inv)
    gw = {_class_name(gw_name)}(order)
    return gw, order, inv


def test_health_check(services):
    gw, order, inv = services
    result = gw.health_check()
    assert result["status"] == "success"


def test_inventory_check(services):
    gw, order, inv = services
    result = gw.handle_request("GET", "/inventory/check",
                                {{"items": ["ITEM-001", "ITEM-002"]}})
    assert result["status"] == "success"


def test_create_order(services):
    gw, order, inv = services
    result = gw.handle_request("POST", "/orders/create",
                                {{"items": ["ITEM-001"]}})
    assert result["status"] == "success"
    assert "order_id" in result.get("data", {{}})


def test_inventory_service_directly():
    inv = {_class_name(inv_name)}()
    result = inv.handle_request("GET", "/check", {{"items": ["ITEM-001"]}})
    assert "stock" in result


def test_order_service_directly():
    inv = {_class_name(inv_name)}()
    order = {_class_name(order_name)}(inv)
    result = order.handle_request("POST", "/orders/create",
                                   {{"items": ["ITEM-004"]}})
    assert "order_id" in result
"""

        files["requirements.txt"] = "pytest\n"

        return files


def _class_name(service_name: str) -> str:
    """Convert service_name to PascalCase class name."""
    return "".join(word.capitalize() for word in service_name.split("_"))
