# TEST8: Unit Test Basics — Find and Fix Bugs

## Goal
A Python module `mathutils.py` contains 3 utility functions, each with a bug.
Write unit tests that expose the bugs, then fix the functions.

## Hard Requirements

1. **Identify all 3 bugs** in `mathutils.py`:
   - Each function has exactly one bug (off-by-one, wrong return type, or missing edge case).
2. **Write tests** in `test_mathutils.py`:
   - At least 2 test cases per function (6+ total).
   - Tests must use `pytest` or plain `assert`.
   - Tests must **pass** after fixes are applied.
3. **Fix the bugs** in `mathutils.py`:
   - Minimal changes only — do not rewrite functions from scratch.
4. **Run**: `python -m pytest test_mathutils.py` must exit 0.

## Deliverables
- Fixed `mathutils.py`
- New `test_mathutils.py` with passing tests
- Verifier confirms all tests pass and all 3 bugs are fixed.
