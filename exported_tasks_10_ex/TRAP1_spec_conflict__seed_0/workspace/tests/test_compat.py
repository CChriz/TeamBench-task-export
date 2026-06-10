"""
tests/test_compat.py — backward compatibility tests.

These 6 tests represent existing client integrations that must not break.
All 6 must pass after validation is applied.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_compat_batch_import_no_optional_fields(client):
    """
    Existing bulk migration client sends CSV without optional columns.
    Must not receive 422.
    """
    csv_data = "id,name\n100,Alpha\n101,Beta\n102,Gamma"
    r = client.post("/batch-import", data=csv_data, content_type="text/csv")
    assert r.status_code != 422, (
        "Backward compat broken: batch-import client sends partial CSV rows"
    )


def test_compat_search_wildcard_query(client):
    """
    Partner search adapter sends wildcard * queries.
    Must not receive 422.
    """
    r = client.get("/search?q=*")
    assert r.status_code != 422, (
        "Backward compat broken: search partner sends wildcard * queries"
    )


def test_compat_search_prefix_wildcard(client):
    """
    Partner search adapter sends prefix wildcard queries like 'foo*'.
    Must not receive 422.
    """
    r = client.get("/search?q=foo*")
    assert r.status_code != 422, (
        "Backward compat broken: search partner sends prefix-wildcard queries"
    )


def test_compat_webhook_no_event_type(client):
    """
    Legacy webhook partner sends payload without event_type field.
    Must not receive 422.
    """
    r = client.post("/webhooks", json={"action": "update", "resource_id": 42})
    assert r.status_code != 422, (
        "Backward compat broken: webhook partner omits event_type"
    )


def test_compat_webhook_arbitrary_schema(client):
    """
    Registered partner sends deeply nested arbitrary payload.
    Must not receive 422.
    """
    r = client.post("/webhooks", json={"meta": {"source": "partner_x"}, "data": [1, 2, 3]})
    assert r.status_code != 422, (
        "Backward compat broken: webhook partner sends arbitrary nested JSON"
    )


def test_compat_valid_user_still_works(client):
    """
    Existing user-creation clients that send valid data must still get 2xx.
    (Regression: adding validation must not break happy-path.)
    """
    r = client.post(
        "/users",
        json={"name": "Bob", "email": "bob@example.com"},
    )
    assert r.status_code in (200, 201), (
        "Backward compat broken: valid user creation now fails"
    )
