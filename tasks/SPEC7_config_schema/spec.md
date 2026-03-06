# SPEC7: Configuration Schema Validator

## Goal
Implement a configuration validator that enforces a 15-field JSON schema with
5 cross-field constraints.

## Requirements
1. Validate all 15 fields defined in `config_schema.json` (types, ranges, enums)
2. Implement 5 cross-field constraints (allOf conditions in the schema)
3. Return structured error messages listing every violation found
4. Pass all existing tests in `tests/test_validator.py` (covers 10 of 15 fields)
5. Handle the remaining 5 fields correctly per the schema (no tests provided)
6. A valid config must return no errors; an invalid config must list all violations

## Supporting Documents
- `config_schema.json` — JSON Schema defining 15 fields with types, ranges, enums, and cross-field constraints
- `validator.py` — Skeleton validator with stubs to implement
- `tests/test_validator.py` — Tests covering 10 of 15 fields and 3 of 5 cross-field constraints
- `sample_configs/valid.json` — Example valid configuration
- `sample_configs/invalid.json` — Example invalid configuration with multiple violations

## Cross-Field Constraints
The schema includes 5 conditional constraints using allOf:
- These are non-trivial: one field's valid values depend on another field's value
- Read the schema carefully — some constraints chain across 3 fields

## Important
Do NOT modify `config_schema.json` or the test files. Implement the validator
to match the schema exactly.
