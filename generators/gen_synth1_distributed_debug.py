"""
Parameterized generator for SYNTH1: Distributed System Debugging.

Each seed produces:
  - Different app domain (order management, event tracking, inventory, booking, etc.)
  - Different model names (User/Order varies with domain)
  - Different route names and URL patterns
  - Same 3 bug types: wrong field access, caching issue, timezone formatting
  - Different field/variable names per seed
  - Different test data and expected responses
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool

# Domain configurations: (domain_name, model1, model2, route_noun, item_noun, item_price_field)
DOMAINS = [
    {
        "name": "order management",
        "model1": "User",
        "model2": "Order",
        "route1": "users",
        "route2": "orders",
        "route3": "reports",
        "item_noun": "item",
        "price_field": "total",
        "update_field": "email",
        "wrong_update_field": "username",
        "cache_entity": "order",
    },
    {
        "name": "event tracking",
        "model1": "Account",
        "model2": "Event",
        "route1": "accounts",
        "route2": "events",
        "route3": "summaries",
        "item_noun": "ticket",
        "price_field": "amount",
        "update_field": "email",
        "wrong_update_field": "contact",
        "cache_entity": "event",
    },
    {
        "name": "inventory system",
        "model1": "Vendor",
        "model2": "Product",
        "route1": "vendors",
        "route2": "products",
        "route3": "reports",
        "item_noun": "unit",
        "price_field": "cost",
        "update_field": "email",
        "wrong_update_field": "address",
        "cache_entity": "product",
    },
    {
        "name": "booking system",
        "model1": "Guest",
        "model2": "Reservation",
        "route1": "guests",
        "route2": "reservations",
        "route3": "reports",
        "item_noun": "night",
        "price_field": "subtotal",
        "update_field": "email",
        "wrong_update_field": "phone",
        "cache_entity": "reservation",
    },
    {
        "name": "notification service",
        "model1": "Subscriber",
        "model2": "Message",
        "route1": "subscribers",
        "route2": "messages",
        "route3": "digests",
        "item_noun": "unit",
        "price_field": "cost",
        "update_field": "email",
        "wrong_update_field": "handle",
        "cache_entity": "message",
    },
]


class Generator(TaskGenerator):
    task_id = "SYNTH1_distributed_debug"
    domain = "debugging"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=10)

        # Pick domain config
        cfg = DOMAINS[seed % len(DOMAINS)]

        # Pick user ids and names for test data
        user_id_a = str(rng.randint(100, 500))
        user_id_b = str(rng.randint(501, 999))
        name_a = names.next()
        name_b = names.next()
        email_a = f"{name_a.lower()}@example.com"
        email_b = f"{name_b.lower()}@example.com"

        # Pick item price and quantity for caching test
        item_price = float(rng.randint(5, 50))
        item_qty = rng.randint(2, 6)
        discount_pct = rng.choice([10, 15, 20, 25])
        item_subtotal = item_price * item_qty
        discounted = round(item_subtotal * (1 - discount_pct / 100), 2)
        item_name = rng.choice(["Widget", "Gadget", "Gizmo", "Device", "Module", "Component"])

        expected = {
            "domain": cfg["name"],
            "model1": cfg["model1"],
            "model2": cfg["model2"],
            "route1": cfg["route1"],
            "route2": cfg["route2"],
            "user_id_a": user_id_a,
            "name_a": name_a,
            "email_a": email_a,
            "update_field": cfg["update_field"],
            "wrong_update_field": cfg["wrong_update_field"],
            "item_price": item_price,
            "item_qty": item_qty,
            "discount_pct": discount_pct,
            "discounted_total": discounted,
            "item_name": item_name,
            "bug1_fix": f"use get('{cfg['update_field']}') not get('{cfg['wrong_update_field']}')",
            "bug2_fix": "cache key must include discount state or cache invalidated on apply_discount",
            "bug3_fix": "convert datetime to local timezone before strftime",
        }

        workspace_files = self._build_workspace(
            cfg, user_id_a, user_id_b, name_a, name_b, email_a, email_b,
            item_price, item_qty, discount_pct, discounted, item_name,
        )

        spec_md = self._generate_spec(cfg, item_price, item_qty, discount_pct, discounted, item_name)
        brief_md = self._generate_brief(cfg)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _build_workspace(
        self, cfg, uid_a, uid_b, name_a, name_b, email_a, email_b,
        item_price, item_qty, discount_pct, discounted, item_name,
    ) -> dict[str, str]:
        files = {}
        r1 = cfg["route1"]
        r2 = cfg["route2"]
        r3 = cfg["route3"]
        m1 = cfg["model1"]
        m2 = cfg["model2"]
        update_field = cfg["update_field"]
        wrong_field = cfg["wrong_update_field"]
        price_field = cfg["price_field"]
        cache_entity = cfg["cache_entity"]

        files["app/__init__.py"] = ""

        files["app/server.py"] = f'''"""Flask-like application server (simplified for testing)."""
import json


class Request:
    def __init__(self, method, path, body=None):
        self.method = method
        self.path = path
        self.json = json.loads(body) if body else {{}}


class Response:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body or {{}}

    def json(self):
        return self.body


class App:
    def __init__(self):
        self.routes = {{}}
        self._{r1} = {{
            "{uid_a}": {{"id": "{uid_a}", "name": "{name_a}", "{update_field}": "{email_a}"}},
            "{uid_b}": {{"id": "{uid_b}", "name": "{name_b}", "{update_field}": "{email_b}"}},
        }}

    def route(self, path, methods=None):
        def decorator(func):
            self.routes[(path, tuple(methods or ["GET"]))] = func
            return func
        return decorator

    def handle(self, request):
        for (path_pattern, methods), handler in self.routes.items():
            if request.method in methods and self._match_path(path_pattern, request.path):
                params = self._extract_params(path_pattern, request.path)
                return handler(request, **params)
        return Response(404, {{"error": "not_found"}})

    def _match_path(self, pattern, path):
        p_parts = pattern.strip("/").split("/")
        r_parts = path.strip("/").split("/")
        if len(p_parts) != len(r_parts):
            return False
        return all(
            pp.startswith("<") or pp == rp
            for pp, rp in zip(p_parts, r_parts)
        )

    def _extract_params(self, pattern, path):
        p_parts = pattern.strip("/").split("/")
        r_parts = path.strip("/").split("/")
        params = {{}}
        for pp, rp in zip(p_parts, r_parts):
            if pp.startswith("<") and pp.endswith(">"):
                params[pp[1:-1]] = rp
        return params

    def get_{r1[:-1]}(self, entity_id):
        return self._{r1}.get(entity_id)

    def update_{r1[:-1]}(self, entity_id, data):
        if entity_id in self._{r1}:
            self._{r1}[entity_id].update(data)
            return self._{r1}[entity_id]
        return None


app = App()
'''

        files["app/models/__init__.py"] = ""

        files[f"app/models/{r1[:-1]}.py"] = f'''"""{m1} model."""


class {m1}:
    def __init__(self, entity_id, name, {update_field}):
        self.id = entity_id
        self.name = name
        self.{update_field} = {update_field}

    def to_dict(self):
        return {{"id": self.id, "name": self.name, "{update_field}": self.{update_field}}}
'''

        files[f"app/models/{r2[:-1]}.py"] = f'''"""{m2} model."""


class {m2}:
    def __init__(self, items):
        self.items = items  # list of (name, price, quantity)
        self._discount_pct = 0

    @property
    def item_total(self):
        return sum(price * qty for _, price, qty in self.items)

    def apply_discount(self, percent):
        self._discount_pct = percent

    @property
    def {price_field}(self):
        return self.item_total * (1 - self._discount_pct / 100)
'''

        files["app/routes/__init__.py"] = ""

        # BUG 1: wrong field reference in update handler
        files[f"app/routes/{r1}.py"] = f'''"""{m1} CRUD endpoints."""
from app.server import app, Request, Response


def handle_get_{r1[:-1]}(request, {r1[:-1]}_id):
    """GET /{r1}/<{r1[:-1]}_id>"""
    entity = app.get_{r1[:-1]}({r1[:-1]}_id)
    if not entity:
        return Response(404, {{"error": "not_found"}})
    return Response(200, entity)


def handle_update_{r1[:-1]}(request, {r1[:-1]}_id):
    """PUT /{r1}/<{r1[:-1]}_id>"""
    entity = app.get_{r1[:-1]}({r1[:-1]}_id)
    if not entity:
        return Response(404, {{"error": "not_found"}})

    updates = {{}}
    if "name" in request.json:
        updates["name"] = request.json["name"]
    if "{update_field}" in request.json:
        # BUG: reads from wrong field "{wrong_field}" instead of "{update_field}"
        updates["{update_field}"] = request.json.get("{wrong_field}")

    if updates:
        updated = app.update_{r1[:-1]}({r1[:-1]}_id, updates)
        return Response(200, updated)
    return Response(200, entity)
'''

        # BUG 2: cache not invalidated after apply_discount
        files[f"app/routes/{r2}.py"] = f'''"""{m2} processing endpoints."""
from app.utils.cache import cache


class {m2[0].upper() + m2[1:]}:
    def __init__(self, items):
        self.items = items  # list of (name, price, quantity)
        self._discount_pct = 0

    @property
    def item_total(self):
        return sum(price * qty for _, price, qty in self.items)

    def apply_discount(self, percent):
        self._discount_pct = percent

    @property
    def {price_field}(self):
        """{m2} {price_field} (uses cache for performance)."""
        cache_key = f"{cache_entity}_{{id(self)}}_{price_field}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        subtotal = self.item_total
        # BUG: caches subtotal before applying discount
        cache.set(cache_key, subtotal)

        if self._discount_pct > 0:
            return round(subtotal * (1 - self._discount_pct / 100), 2)
        return subtotal
'''

        files[f"app/routes/{r3}.py"] = f'''"""Report generation endpoints."""
from app.utils.formatter import format_date
from datetime import datetime, timezone


class Report:
    def __init__(self):
        self.entries = []

    def add_entry(self, title, event_time):
        """Add an entry with an event timestamp."""
        self.entries.append({{
            "title": title,
            "event_time": event_time,
        }})

    def generate(self):
        """Generate report with formatted dates."""
        lines = ["MONTHLY REPORT", "=" * 40]
        for entry in self.entries:
            formatted = format_date(entry["event_time"])
            lines.append(f"  {{entry[\'title\']}}: {{formatted}}")
        return "\\n".join(lines)
'''

        files["app/utils/__init__.py"] = ""

        files["app/utils/cache.py"] = '''"""Simple in-memory caching layer."""


class Cache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        """Get value from cache. Returns None if not found."""
        return self._store.get(key)

    def set(self, key, value):
        """Set value in cache."""
        self._store[key] = value

    def delete(self, key):
        """Delete a key from cache."""
        self._store.pop(key, None)

    def clear(self):
        """Clear all cached values."""
        self._store.clear()


# Global cache instance
cache = Cache()
'''

        # BUG 3: no timezone conversion in format_date
        files["app/utils/formatter.py"] = '''"""Data formatting utilities."""
from datetime import datetime, timezone


def format_date(dt):
    """Format a datetime for display in reports.

    Args:
        dt: datetime object (may be in any timezone)

    Returns:
        Formatted date string YYYY-MM-DD
    """
    # BUG: formats without converting to local timezone first
    return dt.strftime("%Y-%m-%d")
'''

        files["tests/__init__.py"] = ""

        # Test file parameterized to match the domain
        files["tests/test_app.py"] = f'''"""Application tests."""
import json
import threading
from datetime import datetime, timezone, timedelta
from app.server import app, Request, Response
from app.routes.{r1} import handle_get_{r1[:-1]}, handle_update_{r1[:-1]}
from app.routes.{r2} import {m2}
from app.routes.{r3} import Report
from app.utils.cache import cache
from app.utils.formatter import format_date


class Test{m1}Endpoints:
    def test_get_{r1[:-1]}(self):
        """Test GET /{r1}/{uid_a} returns entity data."""
        request = Request("GET", "/{r1}/{uid_a}")
        response = handle_get_{r1[:-1]}(request, {r1[:-1]}_id="{uid_a}")
        assert response.status == 200
        assert response.body["name"] == "{name_a}"

    def test_get_{r1[:-1]}_not_found(self):
        """Test GET /{r1}/9999 returns 404."""
        request = Request("GET", "/{r1}/9999")
        response = handle_get_{r1[:-1]}(request, {r1[:-1]}_id="9999")
        assert response.status == 404

    def test_update_{r1[:-1]}_{update_field}(self):
        """Test PUT /{r1}/{uid_a} updates {update_field}."""
        app._{r1}["{uid_a}"]["{update_field}"] = "{email_a}"

        request = Request("PUT", "/{r1}/{uid_a}", json.dumps({{"{update_field}": "new@example.com"}}))
        response = handle_update_{r1[:-1]}(request, {r1[:-1]}_id="{uid_a}")
        assert response.status == 200
        assert response.body["{update_field}"] != "{email_a}", \\
            "{update_field} should have changed after update"

        app._{r1}["{uid_a}"]["{update_field}"] = "{email_a}"


class Test{m2}s:
    def test_{r2[:-1]}_total_no_discount(self):
        """Test {r2[:-1]} {price_field} without discount."""
        cache.clear()
        entity = {m2}([("{item_name}", {item_price}, {item_qty})])
        assert entity.{price_field} == {item_price * item_qty}

    def test_{r2[:-1]}_total_with_discount(self):
        """Test {r2[:-1]} {price_field} with discount applied."""
        cache.clear()
        entity = {m2}([("{item_name}", {item_price}, {item_qty})])
        entity.apply_discount({discount_pct})
        total = entity.{price_field}
        assert total < {item_price * item_qty}, f"Discount not applied: total still {{total}}"

        total2 = entity.{price_field}
        assert total == total2, f"Inconsistent totals: {{total}} vs {{total2}}"


class TestReports:
    def test_report_generation(self):
        """Test basic report generation."""
        report = Report()
        dt = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        report.add_entry("Test Event", dt)
        output = report.generate()
        assert "MONTHLY REPORT" in output
        assert "Test Event" in output

    def test_report_timezone_conversion(self):
        """Test dates are shown in local timezone."""
        report = Report()
        est = timezone(timedelta(hours=-5))
        event_time = datetime(2024, 12, 31, 23, 0, tzinfo=est)
        report.add_entry("New Year Eve Event", event_time)
        output = report.generate()
        assert "New Year Eve Event" in output, "Event missing from report"

    def test_all_passing(self):
        """Meta-test: existing non-bug tests still pass."""
        request = Request("GET", "/{r1}/{uid_a}")
        response = handle_get_{r1[:-1]}(request, {r1[:-1]}_id="{uid_a}")
        assert response.status == 200
        cache.clear()
        entity = {m2}([("Item", 5.0, 2)])
        assert entity.{price_field} == 10.0
'''

        return files

    def _generate_spec(self, cfg, item_price, item_qty, discount_pct, discounted, item_name) -> str:
        r1 = cfg["route1"]
        r2 = cfg["route2"]
        m1 = cfg["model1"]
        m2 = cfg["model2"]
        update_field = cfg["update_field"]
        wrong_field = cfg["wrong_update_field"]
        price_field = cfg["price_field"]
        item_subtotal = item_price * item_qty

        return f"""# SYNTH1: Distributed Debugging

## Goal
Fix 3 reported bugs in the web application so the test suite passes.

## Bug Report 1: "{m1}s can't update their {update_field}"
- **Symptom**: `PUT /{r1}/{{id}}` returns 200 but the `{update_field}` field is not updated
- **Steps to reproduce**: Send a PUT request with `{{"{update_field}": "new@example.com"}}` to `/{r1}/{{id}}`
- **Server logs**: Request is received, handler completes with 200 status, no errors logged
- **Expected**: After a successful PUT, subsequent GET of the same entity must reflect the new `{update_field}` value
- **Constraint**: The handler must read the `{update_field}` value from the correct field in the JSON request body (not `{wrong_field}`)

## Bug Report 2: "{m2} totals are wrong after applying discounts"
- **Symptom**: A {r2[:-1]} for {item_qty} {cfg['item_noun']}s at ${item_price:.1f} each with a {discount_pct}% discount shows a {price_field} of ${item_subtotal:.1f} instead of ${discounted:.1f}
- **Steps to reproduce**: Create a {r2[:-1]}, apply a {discount_pct}% discount, then retrieve the {price_field}
- **Server logs**: Cache hit rate is high, response times are normal
- **Monitoring data**: The caching layer is returning values that do not reflect recent changes
- **Expected**: The {r2[:-1]} {price_field} after applying a discount must reflect the discounted price
- **Constraint**: The root cause is in the caching layer, not the {r2[:-1]} calculation logic itself

## Bug Report 3: "Monthly reports show dates in wrong timezone"
- **Symptom**: A report generated for an event that occurred at 11pm EST on 2024-12-31 shows the date as 2025-01-01
- **Steps to reproduce**: Create an event at 2024-12-31 23:00 EST, then generate the monthly report
- **Server logs**: Date formatting is performed in UTC
- **Expected**: Dates displayed in reports must reflect the local timezone (US/Eastern), not UTC
- **Constraint**: The formatting logic must convert timestamps to the correct local timezone before rendering the date string

## Deliverables
- Fix all 3 bugs (minimal changes)
- All 8 tests in `test_app.py` must pass
- Total diff < 25 lines
"""

    def _generate_brief(self, cfg) -> str:
        return f"""# SYNTH1: Distributed Debugging (Brief)

Fix 3 bugs in the {cfg['name']} web application.
Bugs: wrong field access in update handler, stale cache after discount, wrong timezone in date formatter.
Run: `python -m pytest tests/test_app.py -v`
"""
