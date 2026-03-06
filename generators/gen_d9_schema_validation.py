"""
Parameterized generator for D9: JSON Schema Validation Pipeline.

Each seed produces:
  - Different status enum values
  - Different sample data (valid + invalid records)
  - Same 5 bugs: missing required check, wrong type check, broken enum,
    timestamp coercion, boolean coercion
  - Different expected valid/invalid record counts
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool

STATUS_SETS = [
    ["active", "inactive", "pending"],
    ["enabled", "disabled", "suspended"],
    ["approved", "rejected", "under_review"],
]

TS_ANCHORS = [1704067200, 1717200000, 1730000000]


class Generator(TaskGenerator):
    task_id = "D9_schema_validation"
    domain = "data"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=30)

        statuses = STATUS_SETS[seed % len(STATUS_SETS)]
        ts_base = TS_ANCHORS[seed % len(TS_ANCHORS)]

        records = []

        # 6 clean valid records
        for i in range(6):
            rid = 100 + seed * 20 + i
            records.append({
                "id": rid,
                "name": names.next(),
                "email": f"user{rid}@example.com",
                "age": rng.randint(18, 65),
                "status": rng.choice(statuses),
                "created_at": ts_base + rng.randint(0, 86400 * 30),
                "verified": bool(i % 2 == 0),
            })

        # BUG1: missing email field — should be INVALID
        rid_missing_email = 200 + seed * 10
        records.append({
            "id": rid_missing_email,
            "name": names.next(),
            # email omitted deliberately
            "age": rng.randint(18, 65),
            "status": statuses[0],
            "created_at": ts_base + 1000,
            "verified": True,
        })

        # BUG2: string age — should be INVALID
        rid_string_age = 201 + seed * 10
        records.append({
            "id": rid_string_age,
            "name": names.next(),
            "email": f"user{rid_string_age}@example.com",
            "age": str(rng.randint(20, 50)),   # string, not int
            "status": statuses[0],
            "created_at": ts_base + 2000,
            "verified": False,
        })

        # BUG3: capitalized status — should be VALID after fix (normalize lowercase)
        rid_cap_status = 202 + seed * 10
        records.append({
            "id": rid_cap_status,
            "name": names.next(),
            "email": f"user{rid_cap_status}@example.com",
            "age": rng.randint(18, 65),
            "status": statuses[0].capitalize(),   # e.g. "Active" — valid after normalize
            "created_at": ts_base + 3000,
            "verified": True,
        })

        # BUG5: string boolean — should be VALID after coercion fix
        rid_str_bool = 203 + seed * 10
        records.append({
            "id": rid_str_bool,
            "name": names.next(),
            "email": f"user{rid_str_bool}@example.com",
            "age": rng.randint(18, 65),
            "status": statuses[1],
            "created_at": ts_base + 4000,
            "verified": "true",   # string, not bool
        })

        # After all 5 fixes:
        #   valid  = 6 clean + cap_status + str_bool = 8
        #   invalid = missing_email + string_age     = 2
        expected_valid_count = 8
        expected_invalid_count = 2

        expected = {
            "valid_count": expected_valid_count,
            "invalid_count": expected_invalid_count,
            "missing_email_id": rid_missing_email,
            "string_age_id": rid_string_age,
            "capitalized_status_id": rid_cap_status,
            "string_bool_id": rid_str_bool,
            "statuses": statuses,
            "bugs": [
                "missing_required_email_check",
                "wrong_type_check_age_accepts_string",
                "enum_case_sensitive_rejects_capitalized",
                "timestamp_serialized_as_string",
                "boolean_not_coerced_from_string",
            ],
        }

        workspace_files = self._build_workspace(records, statuses)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._spec(statuses),
            brief_md=self._brief(),
            expected=expected,
            workspace_files=workspace_files,
        )

    def _build_workspace(self, records: list[dict], statuses: list[str]) -> dict[str, str]:
        files: dict[str, str] = {}

        files["data/input/records.json"] = json.dumps(records, indent=2)

        buggy_schema = {
            "type": "object",
            "required": ["id", "name", "age", "status", "created_at", "verified"],
            # BUG1: "email" missing from required
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "email": {"type": "string"},
                "age": {"type": ["integer", "string"]},  # BUG2: accepts string
                "status": {"type": "string", "enum": statuses},  # BUG3: case-sensitive
                "created_at": {"type": "integer"},
                "verified": {"type": "boolean"},
            },
        }
        files["data/schema.json"] = json.dumps(buggy_schema, indent=2)

        statuses_repr = repr(statuses)

        files["pipeline.py"] = f'''\
"""JSON schema validation pipeline.

Reads records from data/input/records.json, validates against schema,
writes valid records to data/output/valid.json and invalid to data/output/invalid.json.

Bugs to fix:
  BUG1: Does not check that "email" field is present (required field missing from check)
  BUG2: Accepts string values for "age" field (should require integer type only)
  BUG3: Status enum check is case-sensitive — rejects valid capitalized values like "Active"
  BUG4: Timestamp (created_at) serialized as string in output — must remain integer
  BUG5: Boolean (verified) not coerced from string "true"/"false" to real bool
"""
import json
import os


REQUIRED_FIELDS = ["id", "name", "age", "status", "created_at", "verified"]
# BUG1: "email" is missing from REQUIRED_FIELDS — must be added

VALID_STATUSES = {statuses_repr}


def validate_record(record: dict) -> list[str]:
    """Validate a single record. Returns list of error messages (empty = valid)."""
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"Missing required field: {{field}}")

    # BUG2: accepts string age because int("25") succeeds — must check isinstance first
    age = record.get("age")
    if age is not None:
        try:
            int(age)   # wrong: accepts "25"
        except (TypeError, ValueError):
            errors.append("Field 'age' must be an integer")

    # BUG3: case-sensitive status check
    status = record.get("status", "")
    if status not in VALID_STATUSES:   # should use: status.lower() not in VALID_STATUSES
        errors.append(f"Invalid status: {{status!r}}. Must be one of {{VALID_STATUSES}}")

    email = record.get("email", "")
    if email and "@" not in email:
        errors.append("Invalid email format")

    return errors


def serialize_record(record: dict) -> dict:
    """Prepare record for JSON output."""
    out = dict(record)

    # BUG4: must keep created_at as integer, not convert to string
    if "created_at" in out:
        out["created_at"] = str(out["created_at"])   # BUG4: wrong

    # BUG5: no coercion for verified — "true"/"false" strings pass through unchanged

    return out


def run_pipeline(
    input_path: str = "data/input/records.json",
    valid_path: str = "data/output/valid.json",
    invalid_path: str = "data/output/invalid.json",
) -> tuple[int, int]:
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    valid_records = []
    invalid_records = []

    for record in records:
        errors = validate_record(record)
        if errors:
            invalid_records.append({{"record": record, "errors": errors}})
        else:
            valid_records.append(serialize_record(record))

    os.makedirs(os.path.dirname(valid_path), exist_ok=True)
    with open(valid_path, "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2)
    with open(invalid_path, "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2)

    return len(valid_records), len(invalid_records)


if __name__ == "__main__":
    v, i = run_pipeline()
    print(f"Valid: {{v}}, Invalid: {{i}}")
'''

        files["tests/test_pipeline.py"] = f'''\
"""Tests for the schema validation pipeline."""
import json
import subprocess
import sys


def _run():
    r = subprocess.run([sys.executable, "pipeline.py"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"Pipeline failed:\\n{{r.stderr}}"
    with open("data/output/valid.json") as f:
        valid = json.load(f)
    with open("data/output/invalid.json") as f:
        invalid = json.load(f)
    return valid, invalid


def test_counts():
    valid, invalid = _run()
    assert len(valid) == 8, f"Expected 8 valid, got {{len(valid)}}"
    assert len(invalid) == 2, f"Expected 2 invalid, got {{len(invalid)}}"


def test_timestamp_is_int():
    valid, _ = _run()
    for rec in valid:
        assert isinstance(rec.get("created_at"), int), (
            f"created_at must be int, got {{type(rec.get(\'created_at\')).__name__}}"
        )


def test_verified_is_bool():
    valid, _ = _run()
    for rec in valid:
        assert isinstance(rec.get("verified"), bool), (
            f"verified must be bool, got {{type(rec.get(\'verified\')).__name__}}"
        )


if __name__ == "__main__":
    test_counts()
    test_timestamp_is_int()
    test_verified_is_bool()
    print("All tests passed.")
'''

        return files

    def _spec(self, statuses: list[str]) -> str:
        return f"""\
# D9: JSON Schema Validation Pipeline

## Goal
Fix a JSON data pipeline (`pipeline.py`) that validates incoming records against a schema.
The pipeline has 3 schema validation bugs and 2 type coercion bugs.

## Hard Requirements

### Schema Validation Bugs
1. **Missing required field check**: The validator does not reject records missing the `email` field — it should.
2. **Wrong type check for `age`**: The validator accepts string ages like `"25"` — it must require integer type.
3. **Enum validation broken**: The `status` field should only accept `{statuses}` but the check is case-sensitive and rejects capitalized values like `"Active"`. Fix: normalize to lowercase before checking.

### Type Coercion Bugs
4. **Timestamp coercion**: The `created_at` field is a Unix timestamp (integer) but the output serializer writes it as a string. Fix: keep as integer in output JSON.
5. **Boolean coercion**: The `verified` field accepts `"true"`/`"false"` strings but should coerce them to actual JSON booleans in the output.

## Pipeline
- Input: `data/input/records.json` (array of objects)
- Schema: `data/schema.json`
- Valid output: `data/output/valid.json`
- Invalid output: `data/output/invalid.json` (with rejection reasons)
- Run: `python pipeline.py`

## Deliverables
- Fixed `pipeline.py`
- Correct output files
- Verifier confirms all 5 bugs fixed.
"""

    def _brief(self) -> str:
        return """\
# D9: JSON Schema Validation Pipeline (Brief)

Fix `pipeline.py` which validates JSON records. There are 5 bugs:
3 in validation logic and 2 in output serialization.
Run: `python pipeline.py`
Check: `data/output/valid.json` and `data/output/invalid.json`
"""
