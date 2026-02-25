# INT1: Multi-Service Pipeline Repair

## Goal
Fix the data processing pipeline so it runs end-to-end correctly.

## Architecture & API Contracts

### Collector (collector/collector.py)
- Reads `data/input.csv`
- **Output format**: A single JSON array containing all records (not newline-delimited JSON)
- Output file: `data/collected.json`
- Each record must include: `name` (string), `email` (string), `score` (integer), `raw_line` (integer)

### Processor (processor/processor.py)
- **Input**: The JSON array produced by the collector
- Validates each record against the following rules:
  - Email addresses with a `+` character in the local part (e.g., `user+tag@example.com`) are valid and must be accepted
  - Score must be an integer between 0 and 100 inclusive
  - Name must be non-empty
- **Output field naming**: The output record must use the field name `name` (not `full_name` or any other variant)
- Each valid output record must include: `name`, `email`, `score`, `processed_at` (ISO timestamp string)
- Output file: `data/processed.json`
- Records that fail validation must be written to `data/errors.jsonl` (one JSON object per line) — they must not be silently dropped

### Reporter (reporter/reporter.py)
- **Input**: The list of processed records from the processor
- Templates must reference `record.name`, `record.email`, and `record.score` — not any aliased or renamed fields
- Output file: `data/report.txt`
- Records in the report must appear sorted by score in descending order

### Pipeline (pipeline.py)
- Orchestrates the three stages: collector → processor → reporter
- Records rejected during processing must be logged to `data/errors.jsonl`, not silently dropped
- End-to-end: 20 input records → 18 valid output records (2 records in the input have genuinely invalid data)

## Deliverables
- Fixed pipeline that passes integration test
- `data/processed.json` with 18 records
- `data/errors.jsonl` with 2 error entries
- `data/report.txt` with formatted report
