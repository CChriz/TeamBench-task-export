"""
Integration tests for Search Service.

The service provides full-text search over indexed documents.

Start the server before running tests:
    python server.py &

Run tests:
    python -m pytest tests/test_integration.py -v

Base URL: http://localhost:5003
Auth header: X-API-Key: search-api-key-def456
"""
import pytest
import requests

BASE_URL = "http://localhost:5003"
AUTH_HEADERS = {"X-API-Key": "search-api-key-def456"}

# Endpoints covered by this contract:
# GET /search — Search documents; requires ?q= query param
# GET /documents/{document_id} — Retrieve an indexed document by ID
# DELETE /documents/{document_id} — Delete an indexed document
# POST /documents — Index a new document
# GET /health — Health check endpoint


# ---------------------------------------------------------------------------
# TODO: Write integration tests below.
# Your tests must verify:
#   1. Each endpoint returns the correct HTTP status code
#   2. Response bodies contain the required fields
#   3. Authentication is enforced (missing/wrong key → 401)
#   4. Validation errors return 400 with meaningful error response
#   5. Not-found cases return 404
#   6. The /health endpoint is reachable without auth
# ---------------------------------------------------------------------------


# TODO: Implement tests for the /health endpoint
class TestHealth:
    def test_health_returns_200(self):
        # TODO: GET http://localhost:5003/health and assert status == 200
        pass

    def test_health_response_schema(self):
        # TODO: assert response JSON has 'status' == 'ok' and 'service' fields
        pass


# TODO: Implement tests for each authenticated endpoint
# Example structure:

# class TestCreateResource:
#     def test_valid_request_returns_201(self):
#         pass
#
#     def test_missing_field_returns_400(self):
#         pass
#
#     def test_no_auth_returns_401(self):
#         pass

# class TestGetResource:
#     def test_existing_resource_returns_200(self):
#         pass
#
#     def test_nonexistent_returns_404(self):
#         pass
