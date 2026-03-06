# D7: ETL Reconciliation

## Goal
Fix an ETL pipeline that produces incorrect output totals. There are 3 transform
bugs and 2 data quality issues to resolve, then reconcile output against the source.

## Requirements
1. Fix currency conversion: `etl/transform.py` uses the wrong exchange rate column
2. Fix date filtering: off-by-one error excludes the last day of the date range
3. Fix aggregation: aggregate function double-counts refunded orders
4. Handle negative quantities: filter rows with quantity < 0 (invalid data)
5. Handle future dates: flag rows with dates beyond the processing date (do not filter — add a `flagged` column)
6. Output must match `data/expected_output.csv` after all fixes
7. Write `RECONCILIATION_REPORT.md` documenting each issue found

## Supporting Documents
- `etl/extract.py` — Extracts data from source CSV
- `etl/transform.py` — Transform logic (bugs here)
- `etl/load.py` — Loads transformed data to output CSV
- `data/source.csv` — Source data
- `data/expected_output.csv` — Expected correct output
- `data/actual_output.csv` — Current wrong output (for comparison)
- `data/exchange_rates.csv` — Exchange rate reference data
- `RECONCILIATION_SPEC.md` — Defines expected ETL behavior and data quality rules

## Data Quality Rules
- Negative quantities are invalid and must be excluded before transformation
- Future-dated rows must be flagged but NOT filtered (they may represent pre-orders)
- The `flagged` column should contain "future_date" for flagged rows, empty otherwise

## Important
Do NOT modify `data/source.csv`, `data/expected_output.csv`, or `data/exchange_rates.csv`.
Fix `etl/transform.py` and create `RECONCILIATION_REPORT.md`.
