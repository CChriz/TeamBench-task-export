# D8: CSV Data Cleanup

## Goal
Clean a messy CSV file (`data/raw.csv`) by fixing 5 data quality issues and
produce a clean output at `data/clean.csv`.

## Hard Requirements

1. **Remove duplicate rows**: Rows with identical values in the `id` column — keep the first occurrence.
2. **Drop empty columns**: Any column where every value is empty must be removed entirely.
3. **Normalize date formats**: The `date` column contains mixed formats (`MM/DD/YYYY`, `YYYY-MM-DD`, `DD-Mon-YYYY`). Normalize all to `YYYY-MM-DD`.
4. **Strip whitespace**: Trim leading/trailing whitespace from all string cells.
5. **Fix delimiter errors**: Some rows use semicolons instead of commas. Parse them correctly.

## Output Format
- File: `data/clean.csv`
- Encoding: UTF-8
- Delimiter: comma
- Header row preserved (minus dropped columns)
- Sorted by `id` ascending (numeric sort)

## Script
- Write or fix `clean.py` so that `python clean.py` produces the output.

## Deliverables
- Working `clean.py`
- Correct `data/clean.csv`
- Verifier confirms all 5 issues resolved.
