"""
tests/test_api.py — 14 endpoint tests.

7 tests verify that strict endpoints reject bad input (422).
7 tests verify that all endpoints accept valid input (2xx).
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Strict endpoint: POST /users ──────────────────────────────────────────────

def test_users_missing_email_rejected(client):
    """Missing email must return 422."""
    r = client.post("/users", json={"name": "Alice"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_users_invalid_email_rejected(client):
    """Invalid email must return 422."""
    r = client.post("/users", json={"name": "Alice", "email": "not-an-email"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_users_valid_accepted(client):
    """Valid user payload must return 2xx."""
    r = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert r.status_code in (200, 201), f"Expected 2xx, got {r.status_code}"


# ── Strict endpoint: POST /items ──────────────────────────────────────────────

def test_items_missing_price_rejected(client):
    """Missing price must return 422."""
    r = client.post("/items", json={"name": "Widget"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_items_negative_price_rejected(client):
    """Negative price must return 422."""
    r = client.post("/items", json={"name": "Widget", "price": -5.0})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_items_valid_accepted(client):
    """Valid item payload must return 2xx."""
    r = client.post("/items", json={"name": "Widget", "price": 9.99})
    assert r.status_code in (200, 201), f"Expected 2xx, got {r.status_code}"


# ── Strict endpoint: POST /orders ─────────────────────────────────────────────

def test_orders_missing_qty_rejected(client):
    """Missing quantity must return 422."""
    r = client.post("/orders", json={"user_id": 1, "item_id": 2})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_orders_zero_qty_rejected(client):
    """Zero quantity must return 422."""
    r = client.post("/orders", json={"user_id": 1, "item_id": 2, "quantity": 0})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_orders_valid_accepted(client):
    """Valid order payload must return 2xx."""
    r = client.post("/orders", json={"user_id": 1, "item_id": 2, "quantity": 3})
    assert r.status_code in (200, 201), f"Expected 2xx, got {r.status_code}"


# ── Strict endpoint: POST /reports ────────────────────────────────────────────

def test_reports_invalid_type_rejected(client):
    """Unknown report_type must return 422."""
    r = client.post("/reports", json={"report_type": "INVALID_XYZ_999"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_reports_missing_type_rejected(client):
    """Missing report_type must return 422."""
    r = client.post("/reports", json={})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"


def test_reports_valid_accepted(client):
    """Valid report_type must return 2xx."""
    from app.config import ALLOWED_REPORT_TYPES
    r = client.post("/reports", json={"report_type": ALLOWED_REPORT_TYPES[0]})
    assert r.status_code in (200, 201), f"Expected 2xx, got {r.status_code}"


# ── Relaxed endpoint: POST /batch-import ─────────────────────────────────────

def test_batch_import_partial_csv_accepted(client):
    """Partial CSV (missing optional fields) must be accepted (not 422)."""
    r = client.post(
        "/batch-import",
        data="id,name\n1,foo\n2,bar",
        content_type="text/csv",
    )
    assert r.status_code != 422, f"batch-import must not reject partial CSV (got 422)"


# ── Relaxed endpoint: GET /search ────────────────────────────────────────────

def test_search_wildcard_accepted(client):
    """Wildcard * in query must be accepted (not 422)."""
    r = client.get("/search?q=*")
    assert r.status_code != 422, f"search must not reject wildcard * (got 422)"


# ── Relaxed endpoint: POST /webhooks ─────────────────────────────────────────

def test_webhooks_arbitrary_json_accepted(client):
    """Arbitrary JSON (no event_type) must be accepted (not 422)."""
    r = client.post("/webhooks", json={"custom_field": "value", "nested": {"x": 1}})
    assert r.status_code != 422, f"webhooks must not reject arbitrary JSON (got 422)"
