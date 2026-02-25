"""
Parameterized generator for INT1: Multi-Service Pipeline Repair.

Each seed produces:
  - Different component names (fetcher/transformer/writer, etc.)
  - Different field names in the data flow
  - Different input CSV data (names, emails, scores)
  - Different config values
  - Same bug types: wrong output format, wrong field name, wrong field reference
  - Different expected values (valid count, error count, specific emails)
"""
from __future__ import annotations

import csv
import io
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool, ValuePool

# Component name triplets: (collector-role, processor-role, reporter-role)
COMPONENT_TRIPLETS = [
    ("collector", "processor", "reporter"),
    ("fetcher", "transformer", "writer"),
    ("ingester", "enricher", "exporter"),
    ("loader", "validator", "publisher"),
    ("reader", "normalizer", "emitter"),
]

# Field name sets: (name_field, id_field, score_field)
FIELD_SETS = [
    ("name", "email", "score"),
    ("full_name", "address", "rating"),
    ("display_name", "contact", "points"),
    ("user_name", "identifier", "grade"),
    ("label", "handle", "rank"),
]

# Domains for email generation
EMAIL_DOMAINS = [
    "example.com", "sample.org", "test.net", "demo.io", "mock.dev",
]

# Bug variants: (wrong_output_format_comment, wrong_field_in_processor, wrong_field_in_reporter)
BUG_VARIANTS = [
    # (collector writes NDJSON instead of JSON array, processor uses wrong field, reporter uses wrong field)
    ("newline-delimited JSON", "full_name", "full_name"),
    ("newline-delimited JSON", "display_name", "display_name"),
    ("newline-delimited JSON", "user_name", "user_name"),
]


class Generator(TaskGenerator):
    task_id = "INT1_pipeline_repair"
    domain = "integration"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=30)

        # Pick component triplet
        triplet = COMPONENT_TRIPLETS[seed % len(COMPONENT_TRIPLETS)]
        comp1, comp2, comp3 = triplet  # e.g. fetcher, transformer, writer

        # Pick field set
        field_set = FIELD_SETS[(seed // 3) % len(FIELD_SETS)]
        name_field, id_field, score_field = field_set

        # Pick email domain
        domain = EMAIL_DOMAINS[seed % len(EMAIL_DOMAINS)]

        # Pick bug variant
        bug = BUG_VARIANTS[seed % len(BUG_VARIANTS)]
        wrong_processor_field = bug[1]
        wrong_reporter_field = bug[2]

        # Generate input CSV records: 20 rows, 2 invalid
        csv_rows = []
        valid_emails = []
        plus_emails = []  # emails with + in local part

        person_names = names.get(20)

        for i, pname in enumerate(person_names):
            row_num = i + 1
            # Generate a score
            score = rng.randint(50, 100)

            # Determine email style
            local = pname.lower().replace(" ", ".")
            if i < 15:
                # Some get + emails
                if i % 5 == 2:
                    local = f"{local.split('.')[0]}+tag{row_num}"
                    email = f"{local}@{domain}"
                    plus_emails.append(email)
                else:
                    email = f"{local}@{domain}"
            elif i == 15:
                email = f"{local}@{domain}"  # will be valid
            elif i == 16:
                email = f"{local}@{domain}"
            elif i == 17:
                email = f"{local}@{domain}"
            elif i == 18:
                # Invalid: empty name row (will set name to "")
                email = f"missing{row_num}@{domain}"
                pname = ""  # empty name -> invalid
            else:
                # Invalid: score out of range
                score = 150
                email = f"{local}@{domain}"

            if pname and 0 <= score <= 100:
                valid_emails.append(email)

            csv_rows.append({
                name_field: pname,
                id_field: email,
                score_field: str(score),
            })

        valid_count = len(valid_emails)  # should be 18
        error_count = 20 - valid_count   # should be 2

        # Build expected
        expected = {
            "valid_count": valid_count,
            "error_count": error_count,
            "total_input": 20,
            "name_field": name_field,
            "id_field": id_field,
            "score_field": score_field,
            "comp1": comp1,
            "comp2": comp2,
            "comp3": comp3,
            "plus_emails": plus_emails,
            "output_format": "json_array",
            "processed_field": "name",  # must NOT be full_name etc.
        }

        # Generate files
        workspace_files = self._build_workspace(
            rng, csv_rows, comp1, comp2, comp3,
            name_field, id_field, score_field, domain,
            wrong_processor_field, wrong_reporter_field,
            valid_count,
        )

        spec_md = self._generate_spec(
            comp1, comp2, comp3, name_field, id_field, score_field,
            valid_count, error_count,
        )
        brief_md = self._generate_brief(comp1, comp2, comp3)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _csv_text(self, rows: list[dict]) -> str:
        if not rows:
            return ""
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return out.getvalue()

    def _build_workspace(
        self, rng, csv_rows, comp1, comp2, comp3,
        name_field, id_field, score_field, domain,
        wrong_processor_field, wrong_reporter_field,
        valid_count,
    ) -> dict[str, str]:
        files = {}

        # pipeline.py (orchestrator)
        files["pipeline.py"] = f'''"""Pipeline orchestrator — chains {comp1}, {comp2}, {comp3}."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from {comp1}.{comp1} import collect
from {comp2}.{comp2} import process
from {comp3}.{comp3} import generate_report


def run_pipeline():
    """Run the full data pipeline."""
    print("Starting pipeline...")

    # Step 1: Collect
    print("Step 1: Collecting data...")
    collected = collect("data/input.csv", "data/collected.json")
    print(f"  Collected {{collected}} records")

    # Step 2: Process
    print("Step 2: Processing records...")
    try:
        processed, errors = process(
            "data/collected.json",
            "data/processed.json",
            "data/errors.jsonl",
        )
        print(f"  Processed {{processed}} valid records")
        if errors:
            # Silently ignore errors
            pass
    except Exception as e:
        print(f"  Processing failed: {{e}}")
        processed = 0

    # Step 3: Report
    print("Step 3: Generating report...")
    report_count = generate_report("data/processed.json", "data/report.txt")
    print(f"  Report generated with {{report_count}} records")

    print("Pipeline complete!")
    return processed


if __name__ == "__main__":
    run_pipeline()
'''

        # comp1/__init__.py
        files[f"{comp1}/__init__.py"] = ""

        # comp1/config.yaml
        files[f"{comp1}/config.yaml"] = f"""input_path: data/input.csv
output_path: data/collected.json
encoding: utf-8
{name_field}_col: {name_field}
{id_field}_col: {id_field}
{score_field}_col: {score_field}
"""

        # comp1/comp1.py  -- BUG: writes NDJSON instead of JSON array
        files[f"{comp1}/{comp1}.py"] = f'''"""Collect data from CSV input."""
import csv
import json
import os


def collect(input_path, output_path):
    """Read CSV and output JSON records."""
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            records.append({{
                "name": row.get("{name_field}", "").strip(),
                "email": row.get("{id_field}", "").strip(),
                "score": row.get("{score_field}", "0").strip(),
                "raw_line": i,
            }})

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # BUG: Writes as newline-delimited JSON — processor expects a JSON array
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\\n")

    return len(records)


if __name__ == "__main__":
    count = collect("data/input.csv", "data/collected.json")
    print(f"Collected {{count}} records")
'''

        # comp2/__init__.py + schema.py
        files[f"{comp2}/__init__.py"] = ""
        files[f"{comp2}/schema.py"] = f'''"""Validation schema for records."""
import re

# Email pattern — standard validation (must accept + in local part)
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._+%-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$')


def validate_record(record):
    """Validate a single record. Returns list of issues (empty = valid)."""
    issues = []

    name = record.get("name", "")
    if not name or not name.strip():
        issues.append("empty_name")

    email = record.get("email", "")
    if not EMAIL_PATTERN.match(email):
        issues.append("invalid_email")

    try:
        score = int(record.get("score", ""))
        if score < 0 or score > 100:
            issues.append("score_out_of_range")
    except (ValueError, TypeError):
        issues.append("invalid_score")

    return issues
'''

        # comp2/comp2.py  -- BUG: uses wrong field name (full_name instead of name)
        files[f"{comp2}/{comp2}.py"] = f'''"""Process and validate collected records."""
import json
import os
from datetime import datetime, timezone
from {comp2}.schema import validate_record


def process(input_path, output_path, errors_path):
    """Validate and transform records."""
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    processed = []
    errors = []

    for record in records:
        issues = validate_record(record)
        if issues:
            errors.append({{"record": record, "issues": issues}})
            continue

        processed.append({{
            "{wrong_processor_field}": record["name"],  # BUG: should be "name"
            "email": record["email"],
            "score": int(record["score"]),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }})

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2)

    if errors:
        with open(errors_path, "w", encoding="utf-8") as f:
            for err in errors:
                f.write(json.dumps(err) + "\\n")

    return len(processed), len(errors)


if __name__ == "__main__":
    ok, err = process("data/collected.json", "data/processed.json", "data/errors.jsonl")
    print(f"Processed: {{ok}} valid, {{err}} errors")
'''

        # comp3/__init__.py
        files[f"{comp3}/__init__.py"] = ""

        # comp3/templates/summary.txt  -- BUG: references wrong field
        files[f"{comp3}/templates/summary.txt"] = f"""==================================================
DATA PROCESSING REPORT
==================================================

Total records processed: {{{{ total_records }}}}

RECORDS (sorted by score, descending):
--------------------------------------------------
{{% for record in records %}}
{{{{ loop.index }}}}. {{{{ record.{wrong_reporter_field} }}}} ({{{{ record.email }}}}) - Score: {{{{ record.score }}}}
{{% endfor %}}

==================================================
END OF REPORT
"""

        # comp3/comp3.py  -- BUG: references wrong field (full_name instead of name)
        files[f"{comp3}/{comp3}.py"] = f'''"""Generate summary report from processed records."""
import json
import os


def generate_report(input_path, output_path, template_path=None):
    """Generate a text report from processed records."""
    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Sort by score descending
    records.sort(key=lambda r: r.get("score", 0), reverse=True)

    lines = ["=" * 50, "DATA PROCESSING REPORT", "=" * 50, ""]
    lines.append(f"Total records processed: {{len(records)}}")
    lines.append("")
    lines.append("RECORDS (sorted by score, descending):")
    lines.append("-" * 50)

    for i, record in enumerate(records, 1):
        # BUG: references "{wrong_reporter_field}" instead of "name"
        lines.append(f"{{i}}. {{record['{wrong_reporter_field}']}} ({{record['email']}}) - Score: {{record['score']}}")

    lines.append("")
    lines.append("=" * 50)
    lines.append("END OF REPORT")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\\n".join(lines))

    return len(records)


if __name__ == "__main__":
    count = generate_report("data/processed.json", "data/report.txt")
    print(f"Report generated with {{count}} records")
'''

        # data/input.csv
        files["data/input.csv"] = self._csv_text(csv_rows)

        # tests/test_pipeline.py
        files["tests/test_pipeline.py"] = f'''"""Integration tests for the data pipeline."""
import json
import os
import subprocess
import sys


def test_pipeline_end_to_end():
    """Run the full pipeline and verify outputs."""
    result = subprocess.run(
        [sys.executable, "pipeline.py"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"Pipeline failed: {{result.stderr}}"

    assert os.path.isfile("data/processed.json"), "processed.json missing"
    with open("data/processed.json") as f:
        processed = json.load(f)
    assert len(processed) > 0, "No records processed"

    for rec in processed:
        assert "name" in rec, f"Missing 'name' field in {{rec}}"
        assert "email" in rec, f"Missing 'email' field in {{rec}}"
        assert "score" in rec, f"Missing 'score' field in {{rec}}"
        assert "processed_at" in rec, f"Missing 'processed_at' field in {{rec}}"

    assert os.path.isfile("data/errors.jsonl"), "errors.jsonl missing"
    with open("data/errors.jsonl") as f:
        errors = [json.loads(line) for line in f if line.strip()]
    assert len(errors) >= 0

    assert os.path.isfile("data/report.txt"), "report.txt missing"
    with open("data/report.txt") as f:
        report = f.read()
    assert len(report) > 0, "Report is empty"

    print(f"Pipeline test passed: {{len(processed)}} records, {{len(errors)}} errors")
'''

        return files

    def _generate_spec(
        self, comp1, comp2, comp3, name_field, id_field, score_field,
        valid_count, error_count,
    ) -> str:
        return f"""# INT1: Multi-Service Pipeline Repair

## Goal
Fix the data processing pipeline so it runs end-to-end correctly.

## Architecture & API Contracts

### {comp1.capitalize()} ({comp1}/{comp1}.py)
- Reads `data/input.csv`
- **Output format**: A single JSON array containing all records (not newline-delimited JSON)
- Output file: `data/collected.json`
- Each record must include: `name` (string), `email` (string), `score` (integer), `raw_line` (integer)
- Input CSV columns: `{name_field}` (name), `{id_field}` (email), `{score_field}` (score)

### {comp2.capitalize()} ({comp2}/{comp2}.py)
- **Input**: The JSON array produced by the {comp1}
- Validates each record:
  - Email addresses with a `+` character in the local part are valid and must be accepted
  - Score must be an integer between 0 and 100 inclusive
  - Name must be non-empty
- **Output field naming**: The output record must use the field name `name` (not `full_name` or any other variant)
- Each valid output record must include: `name`, `email`, `score`, `processed_at` (ISO timestamp string)
- Output file: `data/processed.json`
- Records that fail validation must be written to `data/errors.jsonl` (one JSON object per line)

### {comp3.capitalize()} ({comp3}/{comp3}.py)
- **Input**: The list of processed records from the {comp2}
- Templates must reference `record.name`, `record.email`, and `record.score` — not any aliased fields
- Output file: `data/report.txt`
- Records in the report must appear sorted by score in descending order

### Pipeline (pipeline.py)
- Orchestrates the three stages: {comp1} → {comp2} → {comp3}
- Records rejected during processing must be logged to `data/errors.jsonl`, not silently dropped
- End-to-end: 20 input records → {valid_count} valid output records ({error_count} records have invalid data)

## Deliverables
- Fixed pipeline that passes integration test
- `data/processed.json` with {valid_count} records
- `data/errors.jsonl` with {error_count} error entries
- `data/report.txt` with formatted report
"""

    def _generate_brief(self, comp1, comp2, comp3) -> str:
        return f"""# INT1: Multi-Service Pipeline Repair (Brief)

Fix the 3-stage data pipeline: {comp1} → {comp2} → {comp3}.
There are integration bugs between the stages — field names and output formats are mismatched.
Run: `python pipeline.py`
"""
