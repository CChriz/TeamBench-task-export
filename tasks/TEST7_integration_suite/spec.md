# TEST7: Integration Test Suite

## Goal
Write integration tests for a three-service system (user_service, order_service, payment_service)
that detect all 8 contract violations embedded in the service implementations.

## Services
See `api_contracts.md` for the full API contract specification.

- **User Service** (user_service.py) — manages users
- **Order Service** (order_service.py) — manages orders, references users
- **Payment Service** (payment_service.py) — manages payments, references orders

## Known Violations
The service implementations contain 8 contract violations including:
- Wrong HTTP status codes (200 instead of 201 for creation, etc.)
- Missing required fields in responses
- Inconsistent field naming (camelCase vs snake_case)
- Plain text error responses instead of JSON
- Missing cross-service dependency validation
- Missing pagination on list endpoints
- Incorrect error status codes

## Strategy
- Use Flask test clients (provided as fixtures) to call each service
- Verify status codes, response schemas, error formats, and cross-service contracts
- Each violation should be detected by at least one test

## Deliverables
- `tests/test_integration.py` with at least 10 test functions
- All 8 violations must be detectable by the test suite
- Run: `python -m pytest tests/test_integration.py -v`
