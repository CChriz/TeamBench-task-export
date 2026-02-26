# MULTI3: Polyglot Interface Bug Fix — Full Specification (Planner Only)

## Overview

A two-component data pipeline for the **Config Sync** domain.  The Python
backend (`backend/processor.py`) serializes internal records into a wire format
defined by `shared/schema.json`.  The Python frontend (`frontend/handler.py`)
consumes that wire format.

The system has **4 bugs** spread across the two components and
the shared schema. All bugs must be fixed so that `python3 -m pytest
tests/test_contract.py -v` (or `python3 tests/test_contract.py`) passes all
tests.

---

## Interface Contract

### Wire Format — Envelope

Every response from the backend is wrapped in an envelope:

```json
{
  "data": [ <record>, ... ],
  "count": <integer>
}
```

- The array of records MUST be under the key **`"data"`** (not `"result"`, not `"items"`).
- `count` MUST equal the length of the `data` array.

### Wire Format — Record Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `config_id` | `int` | no | unique config entry identifier |
| `service_name` | `str` | no | target service identifier |
| `key` | `str` | no | configuration key name |
| `value` | `str` | no | configuration value (always string) |
| `updated_at` | `date` | no | last update date (YYYY-MM-DD) |
| `enabled` | `bool` | no | whether config entry is active |
| `note` | `str` | yes | operator note (optional) |

### Encoding Rules

| Concern | Rule |
|---------|------|
| **Dates** | ISO-8601 string `YYYY-MM-DD` — never `MM/DD/YYYY` |
| **Nulls** | JSON `null` (Python `None`) — never the string `"NULL"` or `"N/A"` |
| **Booleans** | JSON `true`/`false` (Python `bool`) — never integers `0`/`1` |
| **Strings** | UTF-8, stripped of leading/trailing whitespace |
| **ID field** | Key name MUST be `"config_id"` in the wire dict |

---

## Bug Inventory

- **Backend layer**: Backend serializer formats dates as MM/DD/YYYY instead of YYYY-MM-DD (ISO-8601)
- **Backend layer**: Backend serializer emits the ID field under the wrong key name
- **Frontend layer**: Frontend does not guard against None values in nullable fields, causing AttributeError
- **Schema layer**: shared/schema.json uses a wrong field name that disagrees with spec

### Additional schema bug

`shared/schema.json` declares one field under the wrong name
(`"service"` instead of `"service_name"`). The schema must
agree with the encoding rules table above.

---

## File Layout

```
workspace/
  backend/
    processor.py       # Python backend — serialize + batch functions
  frontend/
    handler.py         # Python frontend consumer — deserialize + display
  shared/
    schema.json        # Interface contract (JSON Schema-style)
  tests/
    test_contract.py   # Test suite — DO NOT MODIFY
```

---

## Expected Outcome

After all 4 fixes:

```
python3 tests/test_contract.py
```

Output:
```
.............
----------------------------------------------------------------------
Ran 13 tests in 0.XXXs

OK
```

All 13 tests pass:

1. `test_processor_imports` — backend module imports cleanly
2. `test_handler_imports` — frontend module imports cleanly
3. `test_schema_json_valid` — schema.json is valid JSON with required keys
4. `test_schema_fields_match_spec` — schema field names match the spec contract
5. `test_backend_id_field_name` — backend emits correct ID key `"config_id"`
6. `test_backend_date_format` — backend formats dates as `YYYY-MM-DD`
7. `test_backend_null_is_none` — backend emits `null` not sentinel string for `note`
8. `test_envelope_key` — backend wraps records under `"data"` key
9. `test_bool_is_bool` — backend emits Python `bool` not `int` for boolean fields
10. `test_frontend_id_field_read` — frontend reads ID from correct key `"config_id"`
11. `test_frontend_null_guard` — frontend handles `None` in `note` without crash
12. `test_frontend_date_parse` — frontend parses `updated_at` as `datetime.date`
13. `test_frontend_envelope_read` — frontend reads records from `"data"` key
14. `test_round_trip` — full serialize → deserialize round-trip reproduces original data

---

## Constraints

- Do NOT modify `tests/test_contract.py`
- Only Python standard library is required (`json`, `datetime`)
- `shared/schema.json` is informational — tests read it but the pipeline code must also be consistent with it
