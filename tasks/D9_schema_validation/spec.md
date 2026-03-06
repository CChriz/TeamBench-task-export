# D9: JSON Schema Validation Pipeline

## Goal
Fix a JSON data pipeline (`pipeline.py`) that validates incoming records against a schema.
The pipeline has 3 schema validation bugs and 2 type coercion bugs.

## Hard Requirements

### Schema Validation Bugs
1. **Missing required field check**: The validator does not reject records missing the `email` field — it should.
2. **Wrong type check for `age`**: The validator accepts string ages like `"25"` — it must require integer type.
3. **Enum validation broken**: The `status` field should only accept `["active", "inactive", "pending"]` but the check is case-sensitive and rejects `"Active"`. Fix: normalize to lowercase before checking.

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
