# D1: Schema Drift ETL Repair

## Goal
Fix the ETL pipeline so it correctly processes all input CSV files despite schema changes across batches.

## Hard Requirements

1. The pipeline reads CSV files from `data/input/` and writes a single `data/output/result.csv`.
2. Input files have varying schemas across 5 batches:
   - `batch_001.csv`: columns `[id, name, value]`
   - `batch_002.csv`: columns `[id, name, value, category]` (new column added)
   - `batch_003.csv`: columns `[id, full_name, value, category]` (column renamed relative to batch_001/002)
   - `batch_004.csv`: columns `[record_id, name, amount, category, region]` (multiple column name changes plus an extra column)
   - `batch_005.csv`: columns `[id, name, value, category, _timestamp]` (extra metadata column; contains duplicate records)
3. The canonical output schema is `[id, name, value, category]` — exact column order.
   - Columns from incoming batches that do not belong to the canonical schema must be dropped.
   - Columns in incoming batches that represent the same semantic field as a canonical column but carry a different name must be normalised to the canonical name before output.
4. Missing `category` values must be filled with `"unknown"`.
5. Handle duplicate `id`s: keep the row with the HIGHER `value`. If values are equal, keep the last occurrence.
6. Rows where `value` is non-numeric or negative: replace `value` with `0`.
7. Output must be sorted by `category` ascending, then by `id` ascending (numeric sort).
8. No duplicate rows allowed in the output (by `id`).
9. The pipeline script is `etl.py` — run with `python etl.py`.

## Deliverables
- Fixed `etl.py` in workspace.
- Verifier must verify output schema, row count, sort order, dedup, and produce attestation.
