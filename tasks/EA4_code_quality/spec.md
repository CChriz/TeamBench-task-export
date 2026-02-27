# EA4: Code Quality — Fix Lint Violations

## Goal

A Python application has code quality issues. Fix ruff and pylint violations to meet the
quality targets, while preserving three intentional style choices documented below.

## Quality Commands

```
ruff check app/ 2>&1
pylint app/ 2>&1
```

## Quality Targets

- `ruff check app/` reports **0 errors**
- `pylint app/` score **≥ 9.0/10**

## Application Modules

- `app/processor.py` — data processing: item processing, batch transformation, aggregation
- `app/helpers.py` — utilities: data filtering, statistical computation, validation, routing
- `app/models.py` — data model classes: `DataRecord`, `DataCollection`
- `app/compat.py` — Python 2/3 compatibility shim

## Intentional Style Choices (DO NOT CHANGE)

Three patterns in the codebase are intentional and must be preserved. Ruff/pylint will flag
them — they should be suppressed with appropriate `# noqa:` comments rather than refactored.

### Business Domain Constant

A numeric comparison in `app/processor.py` that implements a specific business threshold.
The team has explicitly decided to keep this threshold visible inline rather than extracting
it to a named constant — the inline value makes the business rule immediately readable.
This triggers a **PLR2004** (magic value) violation — suppress with `# noqa: PLR2004`.

### Statistical Function Name

A long descriptive function name in `app/helpers.py` used for a public statistical API.
The full name is required for mathematical clarity and API discoverability in the statistical
analysis pipeline. This triggers a naming length violation — preserve the name as-is.

### Compatibility Broad Exception

A bare `except:` clause in `app/compat.py` inside a Python 2/3 compatibility shim. This
function must catch ALL exceptions to work correctly across both Python versions. Narrowing
the exception type would break Python 2 compatibility. The `# noqa: E722` suppression is
already present — do not remove it or change the except clause.

## Deliverables

- 0 ruff violations (using `# noqa:` suppressions for the 3 intentional patterns)
- pylint score ≥ 9.0/10
- The 3 intentional patterns remain functionally unchanged
