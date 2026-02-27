# EA2: Coverage Gap — Add Tests to Reach 90% Branch Coverage

## Goal

A Python data validation library has insufficient test coverage. Add tests to reach at least
90% branch coverage. The existing tests cover only the happy paths.

## Coverage Measurement

```
pytest --cov=validator --cov-branch --cov-report=term-missing
```

Target: **≥ 90% branch coverage** across all modules in `validator/`.

## Library Structure

- `validator/core.py` — core validation functions: a domain-specific string validator
  (email/username/phone depending on seed), `validate_range`, `validate_string`
- `validator/rules.py` — rule classes: `RequiredRule`, `TypeRule`, `PatternRule`, `RangeRule`,
  `ValidationError`
- `validator/pipeline.py` — `Pipeline` class for chaining validation rules

## What the Existing Tests Cover

`tests/test_basic.py` has 7 tests covering only success paths — valid inputs that pass
validation. Coverage is approximately 40%. All the error/edge-case branches are uncovered.

## Guidance on Where Gaps Typically Occur

Validation code commonly has uncovered branches in:

- **Rejection paths**: what happens when the input is invalid, malformed, empty, or None
- **Boundary conditions**: behavior when values exactly equal the minimum or maximum thresholds
- **Configuration errors**: what happens when the validator itself is misconfigured
  (e.g., min > max in a range)
- **Pipeline behavior**: what happens when there are no rules, when the first rule fails
  (early exit), when a duplicate rule is added, or when `clear()` is called on an empty pipeline
- **Type coercion**: behavior when values are of unexpected types

Use `pytest --cov=validator --cov-branch --cov-report=term-missing` to see exactly which
lines and branches are uncovered.

## Deliverables

- `tests/test_validator.py` with comprehensive tests targeting the uncovered branches
- Branch coverage ≥ 90% verified by pytest
- All existing tests still pass
