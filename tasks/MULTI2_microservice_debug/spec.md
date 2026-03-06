# MULTI2: Microservice Debug

## Goal

A microservice system has 4 bugs spread across 3 services written in different languages
plus a shared configuration file. All 4 bugs must be fixed for the system to work correctly.

## Architecture

- **Python Flask API** (`api/app.py`): REST endpoint that parses date strings from requests
- **Go Background Worker** (`worker/main.go`): Batch-processes records from a queue file
- **Node.js Frontend Proxy** (`proxy/server.js`): Forwards requests to the API with auth headers
- **Shared Config** (`config.json`): Common configuration used by all three services

## Requirements

1. **Fix the date parsing bug in the Python API**: The API parses date strings using the wrong
   format string. Check the expected format documented in `API_SPEC.md` and fix `app.py` to
   match. The API must accept dates in the documented format and return 400 for invalid dates.

2. **Fix the off-by-one bug in the Go worker**: The Go worker processes records in batches
   from `queue.txt`. It has an off-by-one error in the batch loop that causes the last record
   in each batch to be skipped. Fix the loop bounds so all records are processed.

3. **Fix the header forwarding bug in the Node.js proxy**: The proxy forwards requests to
   the Python API but incorrectly constructs the Authorization header. It should forward the
   original `Authorization` header value from the incoming request, but instead it hardcodes
   a wrong prefix. Fix the header construction.

4. **Fix the config type bug**: The `config.json` file has a `retry_timeout` field that is
   a string `"30"` instead of an integer `30`. All three services parse this field as a number.
   The string value causes silent failures in timeout calculations. Fix it to be a proper integer.

## Supporting Documents

- `API_SPEC.md` — Documents the expected date format and API contract
- `config.json` — Shared configuration (has a type bug)
- `tests/test_api.py` — Python API tests
- `tests/test_worker.sh` — Go worker verification script
- `tests/test_proxy.js` — Node.js proxy tests

## Verification

- Python tests: `cd api && python -m pytest ../tests/test_api.py`
- Go worker: `cd worker && go build -o worker . && ./worker --dry-run`
- Node.js proxy: `node tests/test_proxy.js`
- Config validation: `python tests/validate_config.py`
