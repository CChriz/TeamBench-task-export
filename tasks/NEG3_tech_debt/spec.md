# NEG3: Tech Debt Prioritization

## System Under Review
**Service**: InventoryService — warehouse inventory tracking service

The codebase has accumulated 6 tech debt items. You must prioritize and fix exactly 3 of them
within the available time budget.

## Time Budget
**Hard limit: 6 hours total.** Selecting items whose combined `fix_hours`
exceeds 6 hours will fail the budget check.

## Scoring Matrix

Use this matrix to score each item. Address **highest-value items first** (highest impact,
lowest effort = highest value score).

| Impact \ Effort | Low  | Medium | High |
|-----------------|------|--------|------|
| High   |     90 |     60 |     30 |
| Medium |     70 |     40 |     15 |
| Low    |     50 |     20 |      5 |

## Tech Debt Backlog

The following items have been identified. Review them carefully — their value scores determine
the optimal selection.

| ID    | Title | Impact | Effort | Hours | Score |
|-------|-------|--------|--------|-------|-------|
| TD007 | Outdated dependency with known API depreca *(blocks TD003)* | High   | Low    | 2h |    90 |
| TD010 | Dead code: commented-out debug block | Low    | Low    | 1h |    50 |
| TD001 | Dead code: unused legacy processor | Low    | Low    | 1h |    50 |
| TD003 | Duplicated validation logic *(requires TD007)* | High   | Medium | 3h |    60 |
| TD005 | Bare except clauses swallow errors | High   | Medium | 3h |    60 |
| TD004 | Hardcoded configuration values | Medium | Low    | 2h |    70 |

## Dependency Constraint

**TD007 must be completed before TD003.**

- TD007: Outdated dependency with known API deprecation
- TD003: Duplicated validation logic

If you select TD003, you must also select TD007 and schedule it first.
Selecting TD003 without TD007 will fail the dependency check.

## Prioritization Rubric

1. **Score each item** using the Impact × Effort matrix above.
2. **Select the 3 highest-scoring items** that fit within the 6-hour budget.
3. **Respect the dependency constraint** — if you select a dependent item, you must also
   select and schedule its blocker first.
4. **Fix the selected items** in `service.py` (and `tests/test_service.py` if applicable).
5. **Declare your plan** in `prioritize.py` by setting the `PLAN` list, then run
   `python prioritize.py` to validate.

## Deliverables

1. **`prioritize.py`** — `PLAN` list populated with exactly 3 item IDs in fix order.
   Running `python prioritize.py` must exit 0.
2. **`service.py`** — Selected tech debt items actually fixed (not just declared).
3. **`tests/test_service.py`** — If TD006 is in your plan, the stub must be replaced with
   real tests that pass under `pytest`.

## Grading Checks (10+)

| Check | Description |
|-------|-------------|
| `plan_valid_json` | `prioritize.py` runs without error and exits 0 |
| `exactly_3_items` | Plan selects exactly 3 items |
| `budget_not_exceeded` | Total fix_hours <= 6 |
| `dependency_order` | Blocker precedes dependent (if both selected) |
| `dependent_without_blocker` | Dependent not selected without blocker |
| `highest_value_items` | All 3 selected items are in the top-4 by score |
| `no_bare_except` | No bare `except:` in service.py (if TD005 fixed) |
| `named_constants` | Magic numbers extracted to constants (if TD004 fixed) |
| `no_old_format` | No `old_format()` calls (if TD007 fixed) |
| `type_annotations` | Public methods have type annotations (if TD002 fixed) |
| `no_legacy_function` | `_legacy_process` removed (if TD001 fixed) |
| `no_debug_block` | Debug comment block removed (if TD010 fixed) |
| `tests_pass` | `pytest` exits 0 (if TD006 fixed) |

## Common Traps

- **Fixing the cheapest items** (low hours) without considering value leads to low total score.
- **Ignoring the dependency**: selecting the dependent without the blocker fails the check.
- **Declaring but not fixing**: the `PLAN` list is checked against actual code changes.
- **Exceeding budget**: 4+ items or items whose hours sum > 6 fails immediately.
