# TRAP7: Test Pollution vs Real Bugs

## Goal

The test suite has 8 failing tests. Some failures are caused by real bugs in the application
code, while others are caused by test pollution — shared mutable state between tests that
causes cascading failures.

## Requirements

1. Fix all 8 failing tests so they pass
2. Real bugs must be fixed in the **application code** (not by changing test assertions)
3. Test pollution must be fixed in the **test infrastructure** (proper isolation/teardown)
4. Do NOT "fix" pollution tests by changing their assertions to accept wrong state —
   the tests are correct, the test infrastructure leaks state between tests
5. All tests must pass: `pytest tests/ -v`

## Supporting Documents

- `TEST_ANALYSIS.md` — Documents known test infrastructure issues including shared state
- Source code in `app/` — Contains the application with real bugs

## Key Distinction

- **Real bugs**: The application code produces wrong output. Fix the code.
- **Test pollution**: Tests share mutable state (global dicts, class caches, module counters).
  When one test modifies shared state, subsequent tests see stale values. Fix by adding
  proper setup/teardown or making state test-local.
