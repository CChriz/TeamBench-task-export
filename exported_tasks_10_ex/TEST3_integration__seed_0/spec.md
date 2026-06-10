        # TEST3: Integration Tests — Search Service Contract (Seed 0)

        ## Overview

        The `search_service` provides full-text search over indexed documents.
        A working implementation is provided at `server.py`. Your task is to write
        integration tests that fully verify the API contract below.

        ## Service Details

        | Property | Value |
        |----------|-------|
        | Base URL | `http://localhost:5003` |
        | Auth header | `X-API-Key` |
        | Valid API key | `search-api-key-def456` |
        | Rate limit | 300 requests/minute |
        | Request timeout | 2000 ms |
        | Port | 5003 |

        ## Authentication

        All endpoints marked "Auth required: Yes" must receive the header:

        ```
        X-API-Key: search-api-key-def456
        ```

        Requests missing this header or providing a wrong value **must** receive HTTP `401`.

        ## Endpoints (5 total)

                  ### `GET /search`

          **Summary**: Search documents; requires ?q= query param
          **Auth required**: Yes

          **Request schema**:
            - `q`: query param, required, 1-200 chars
- `page`: query param, optional integer >= 1 (default: 1)
- `page_size`: query param, optional integer 1-100 (default: 10)
- `category`: query param, optional, filter by document category

          **Response schema** (success):
            - `results`: array of result objects
- `total`: integer
- `page`: integer
- `page_size`: integer
- `query`: string (echoed back)

          **Status codes**:
            - `200`: Search results returned (may be empty)
- `400`: Missing or invalid query param
- `401`: Unauthorized

          **Expected test cases**:
            - valid search → 200 with results, total, page → 200
- missing q → 400 → 400
- no auth → 401 → 401
- page_size out of range → 400 → 400

          ### `GET /documents/{document_id}`

          **Summary**: Retrieve an indexed document by ID
          **Auth required**: Yes

          **Request schema**:
            _(no body)_

          **Response schema** (success):
            - `document_id`: string
- `title`: string
- `content`: string
- `category`: string or null
- `tags`: array
- `indexed_at`: string

          **Status codes**:
            - `200`: Document found
- `401`: Unauthorized
- `404`: Document not found

          **Expected test cases**:
            - get existing document → 200 → 200
- get non-existent → 404 → 404

          ### `DELETE /documents/{document_id}`

          **Summary**: Delete an indexed document
          **Auth required**: Yes

          **Request schema**:
            _(no body)_

          **Response schema** (success):
            - `deleted`: boolean true
- `document_id`: string

          **Status codes**:
            - `200`: Document deleted
- `401`: Unauthorized
- `404`: Document not found

          **Expected test cases**:
            - delete existing document → 200 → 200
- delete non-existent → 404 → 404

          ### `POST /documents`

          **Summary**: Index a new document
          **Auth required**: Yes

          **Request schema**:
            - `title`: string, required, max 500 chars
- `content`: string, required
- `category`: string, optional
- `tags`: array of strings, optional

          **Response schema** (success):
            - `document_id`: string (UUID)
- `title`: string
- `category`: string or null
- `indexed_at`: string (ISO-8601)

          **Status codes**:
            - `201`: Document indexed
- `400`: Validation error (missing title or content)
- `401`: Unauthorized

          **Expected test cases**:
            - index document → 201 with document_id → 201
- missing title → 400 → 400

          ### `GET /health`

          **Summary**: Health check endpoint
          **Auth required**: No

          **Request schema**:
            _(no body)_

          **Response schema** (success):
            - `status`: string 'ok'
- `service`: string 'search_service'

          **Status codes**:
            - `200`: Service healthy

          **Expected test cases**:
            - health returns 200 with status=ok → 200


        ## Error Response Format

        All error responses follow this shape:
        ```json
        {"error": "<human-readable message>"}
        ```

        ## Contract Guarantees

        1. All response bodies are JSON (`Content-Type: application/json`).
        2. Timestamps use ISO-8601 format (e.g. `"2024-01-15T10:30:00Z"`).
        3. IDs are UUID strings.
        4. The `/health` endpoint never requires authentication.
        5. Rate limiting: exceeding 300 requests/minute returns `429`.
        6. Timeouts: the server processes requests within 2000 ms under normal load.

        ## Deliverables

        - `tests/test_integration.py` with pytest tests.
        - Tests must pass against the running `server.py`.
        - Minimum 9 test functions.
        - Cover: status codes, response schemas, auth enforcement, error codes, 404 cases.

        ## Grading

        - Check 1: `tests/test_integration.py` exists.
        - Check 2: `/health` endpoint test present and passes.
        - Check 3: Auth enforcement tested (401 on missing key).
        - Check 4: 400 validation error cases tested.
        - Check 5: 404 not-found cases tested.
        - Check 6: Response schema fields verified (not just status codes).
        - Check 7: All tests pass against working server.
        - Check 8: Tests fail against broken server (mutation detection).
        - Check 9: Minimum test count (9+) met.
        - Check 10: Tests cover all 5 endpoints.
        - Check 11: No hardcoded UUIDs from prior runs (tests create fresh resources).
        - Check 12: Content-Type header verified in at least one test.
