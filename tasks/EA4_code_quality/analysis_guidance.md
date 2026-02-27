# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `cd /workspace && ruff check app/ 2>&1` — fast linter
- `cd /workspace && pylint app/ 2>&1` — comprehensive linter with score
- `find /workspace/app -name "*.py"` — list files

## Expected Findings (25 violations total)
- ~8 violations in `app/processor.py`
- ~8 violations in `app/helpers.py`
- ~6 violations in `app/models.py`
- ~3 violations in `app/compat.py`

## False Positives (Intentional Style — DO NOT FIX)
- `app/processor.py`: `value > 1000` — PLR2004, intentional domain constant inline
- `app/helpers.py`: `calculate_weighted_moving_average_with_decay` — C0103, public API naming exception
- `app/compat.py`: bare `except:` — E722, Python 2/3 compat shim

## Key Distinction
22 of 25 violations need real fixes. 3 are intentional — identify them by context, then add appropriate `# noqa` or `# pylint: disable` comments ONLY for those 3.
