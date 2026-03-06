"""
Parameterized generator for PIPE2: Data Pipeline Fix.

Each seed produces an ETL pipeline with 3 cascading bugs:
  1. Extractor drops rows where ANY column is null (should only drop key-column nulls)
  2. Transformer truncates strings to 50 chars (should be 255)
  3. Loader swaps column 2 and column 3 in output mapping
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized schema pools ──────────────────────────────────────

SCHEMAS = [
    {
        "name": "employees",
        "columns": ["emp_id", "full_name", "department", "notes"],
        "key_columns": ["emp_id", "full_name"],
        "col_types": ["int", "str", "str", "str"],
        "truncation_limit": 255,
        "rows": [
            ["1", "Alice Johnson", "Engineering", "Senior engineer with 10 years of experience in distributed systems and cloud architecture"],
            ["2", "Bob Smith", "Marketing", ""],
            ["3", "Charlie Brown", "Engineering", "Recently promoted to tech lead after successful delivery of the platform migration project"],
            ["4", "", "Sales", "New hire"],
            ["5", "Eve Davis", "", "Transferred from the London office; specializes in data analytics and machine learning pipelines"],
            ["6", "Frank Miller", "HR", "Head of talent acquisition with expertise in technical recruiting across multiple regions"],
            ["7", "Grace Lee", "Engineering", ""],
            ["8", "", "", "Should be dropped - both key columns null"],
        ],
        "expected_kept_count": 6,
    },
    {
        "name": "products",
        "columns": ["product_id", "product_name", "category", "description"],
        "key_columns": ["product_id", "product_name"],
        "col_types": ["int", "str", "str", "str"],
        "truncation_limit": 255,
        "rows": [
            ["101", "Widget Pro", "Electronics", "Professional-grade widget with advanced features including wireless connectivity and real-time monitoring"],
            ["102", "Gadget X", "Electronics", ""],
            ["103", "Tool Kit", "Hardware", "Complete toolkit for home improvement containing over fifty individual precision-crafted tools for every occasion"],
            ["104", "", "Software", "Missing product name"],
            ["105", "Cable Set", "", "High-quality cable set compatible with all major devices; includes USB-C, Lightning, and micro-USB connectors"],
            ["106", "Monitor Stand", "Furniture", "Ergonomic adjustable monitor stand designed for dual-monitor setups with integrated cable management system"],
            ["107", "Keyboard", "Electronics", ""],
            ["108", "", "", "Both key columns null"],
        ],
        "expected_kept_count": 6,
    },
    {
        "name": "transactions",
        "columns": ["txn_id", "account_name", "amount", "memo"],
        "key_columns": ["txn_id", "account_name"],
        "col_types": ["int", "str", "float", "str"],
        "truncation_limit": 255,
        "rows": [
            ["1001", "Acme Corp", "5000.00", "Quarterly payment for consulting services including project management and technical advisory support"],
            ["1002", "Beta Inc", "2500.50", ""],
            ["1003", "Gamma LLC", "7800.00", "Annual license renewal for enterprise software suite with premium support and training modules included"],
            ["1004", "", "100.00", "Missing account name"],
            ["1005", "Delta Co", "", "Monthly subscription for cloud infrastructure services spanning three availability zones worldwide"],
            ["1006", "Epsilon Ltd", "3200.00", "One-time setup fee for new data center integration with full redundancy and disaster recovery capabilities"],
            ["1007", "Zeta Group", "900.00", ""],
            ["1008", "", "", "Both key columns null"],
        ],
        "expected_kept_count": 6,
    },
    {
        "name": "customers",
        "columns": ["customer_id", "contact_name", "region", "preferences"],
        "key_columns": ["customer_id", "contact_name"],
        "col_types": ["int", "str", "str", "str"],
        "truncation_limit": 255,
        "rows": [
            ["201", "Diana Prince", "North America", "Prefers email communication; interested in enterprise solutions with dedicated account management and support"],
            ["202", "Clark Kent", "Europe", ""],
            ["203", "Bruce Wayne", "North America", "VIP customer requiring white-glove service with quarterly business reviews and custom reporting dashboards"],
            ["204", "", "Asia", "Missing contact name"],
            ["205", "Tony Stark", "", "Interested in cutting-edge technology solutions including AI-powered analytics and automated deployment pipelines"],
            ["206", "Steve Rogers", "South America", "Long-term customer since founding; requires bilingual support staff and documentation in English and Portuguese"],
            ["207", "Natasha Romanoff", "Europe", ""],
            ["208", "", "", "Both keys null"],
        ],
        "expected_kept_count": 6,
    },
    {
        "name": "projects",
        "columns": ["project_id", "project_name", "owner", "summary"],
        "key_columns": ["project_id", "project_name"],
        "col_types": ["int", "str", "str", "str"],
        "truncation_limit": 255,
        "rows": [
            ["301", "Project Alpha", "Engineering", "Complete rewrite of the legacy authentication system using modern OAuth2 and OpenID Connect standards"],
            ["302", "Project Beta", "Marketing", ""],
            ["303", "Project Gamma", "Engineering", "Migration of all on-premises databases to cloud-managed instances with zero-downtime cutover strategy"],
            ["304", "", "Sales", "Missing project name"],
            ["305", "Project Epsilon", "", "Implement real-time event streaming pipeline replacing the existing batch processing system for faster insights"],
            ["306", "Project Zeta", "Operations", "Infrastructure automation initiative covering provisioning, monitoring, alerting, and incident response workflows"],
            ["307", "Project Eta", "Engineering", ""],
            ["308", "", "", "Both keys null"],
        ],
        "expected_kept_count": 6,
    },
]


class Generator(TaskGenerator):
    task_id = "PIPE2_data_pipeline"
    domain = "DataEngineering"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        schema = SCHEMAS[seed % len(SCHEMAS)]

        workspace_files = self._make_workspace(schema)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "PIPE2_data_pipeline")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="PIPE2_data_pipeline",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "schema_name": schema["name"],
                "columns": schema["columns"],
                "key_columns": schema["key_columns"],
                "truncation_limit": schema["truncation_limit"],
                "expected_output_rows": schema["expected_kept_count"],
                "bugs_fixed": 3,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "DataEngineering"},
        )

    def _make_workspace(self, schema: dict) -> dict:
        files = {}
        name = schema["name"]
        columns = schema["columns"]
        key_cols = schema["key_columns"]
        col_types = schema["col_types"]
        rows = schema["rows"]
        trunc_limit = schema["truncation_limit"]
        expected_count = schema["expected_kept_count"]

        col0, col1, col2, col3 = columns

        # ── data/source.csv ──────────────────────────────────────────────
        csv_header = ",".join(columns)
        csv_rows = []
        for row in rows:
            csv_rows.append(",".join(row))
        files["data/source.csv"] = csv_header + "\n" + "\n".join(csv_rows) + "\n"

        # ── Build expected output (correct pipeline behavior) ────────────
        # Step 1: Extract - keep rows where key columns are non-empty
        kept_rows = []
        for row in rows:
            key_vals = [row[columns.index(k)] for k in key_cols]
            if all(v.strip() for v in key_vals):
                kept_rows.append(list(row))

        # Step 2: Transform - truncate strings to 255 chars (no-op for our data < 255)
        transformed_rows = []
        for row in kept_rows:
            new_row = []
            for i, val in enumerate(row):
                if col_types[i] == "str" and len(val) > trunc_limit:
                    new_row.append(val[:trunc_limit])
                else:
                    new_row.append(val)
            transformed_rows.append(new_row)

        # Step 3: Load - correct column order (no swap)
        expected_csv_header = ",".join(columns)
        expected_csv_rows = []
        for row in transformed_rows:
            expected_csv_rows.append(",".join(row))

        files["data/expected_output.csv"] = (
            expected_csv_header + "\n" + "\n".join(expected_csv_rows) + "\n"
        )

        # ── PIPELINE_SPEC.md ─────────────────────────────────────────────
        key_col_list = ", ".join(f"`{k}`" for k in key_cols)
        col_list = ", ".join(f"`{c}`" for c in columns)
        files["PIPELINE_SPEC.md"] = (
            f"# {name.capitalize()} Data Pipeline Specification\n\n"
            f"## Schema\n\n"
            f"Columns: {col_list}\n\n"
            f"Key columns: {key_col_list}\n\n"
            f"## Stage 1: Extract\n\n"
            f"- Read `data/source.csv`\n"
            f"- Drop rows where ANY **key column** ({key_col_list}) is empty or null\n"
            f"- Preserve rows where non-key columns are empty (keep the empty value)\n\n"
            f"## Stage 2: Transform\n\n"
            f"- Normalize all string fields (strip leading/trailing whitespace)\n"
            f"- Truncate string fields longer than **{trunc_limit}** characters\n\n"
            f"## Stage 3: Load\n\n"
            f"- Map columns to output schema in order: {col_list}\n"
            f"- Write to `data/output.csv`\n\n"
            f"## Output\n\n"
            f"The pipeline writes `data/output.csv` with the same column headers.\n"
            f"Expected output row count (excluding header): rows with non-null key columns.\n"
        )

        # ── pipeline/extract.py (BUG: drops rows where ANY column is null) ──
        files["pipeline/__init__.py"] = ""
        files["pipeline/extract.py"] = (
            'import csv\n'
            'import os\n'
            '\n'
            '\n'
            f'COLUMNS = {columns!r}\n'
            f'KEY_COLUMNS = {key_cols!r}\n'
            '\n'
            '\n'
            'def extract(input_path: str) -> list[dict]:\n'
            '    """\n'
            '    Read CSV and filter out invalid rows.\n'
            '\n'
            '    BUG: Drops rows where ANY column is empty.\n'
            '    Should only drop rows where KEY columns are empty.\n'
            '    """\n'
            '    rows = []\n'
            '    with open(input_path, newline="") as f:\n'
            '        reader = csv.DictReader(f)\n'
            '        for row in reader:\n'
            '            # BUG: checks ALL columns instead of only key columns\n'
            '            if all(row.get(col, "").strip() for col in COLUMNS):\n'
            '                rows.append(row)\n'
            '    return rows\n'
        )

        # ── pipeline/transform.py (BUG: truncates to 50 instead of 255) ──
        files["pipeline/transform.py"] = (
            f'COLUMNS = {columns!r}\n'
            f'COL_TYPES = {col_types!r}\n'
            '\n'
            '# BUG: truncation limit should be 255 per PIPELINE_SPEC.md\n'
            'TRUNCATION_LIMIT = 50\n'
            '\n'
            '\n'
            'def transform(rows: list[dict]) -> list[dict]:\n'
            '    """\n'
            '    Normalize and truncate string fields.\n'
            '\n'
            '    BUG: Uses truncation limit of 50 instead of 255.\n'
            '    """\n'
            '    result = []\n'
            '    for row in rows:\n'
            '        new_row = {}\n'
            '        for i, col in enumerate(COLUMNS):\n'
            '            val = row.get(col, "")\n'
            '            if COL_TYPES[i] == "str":\n'
            '                val = val.strip()\n'
            '                if len(val) > TRUNCATION_LIMIT:\n'
            '                    val = val[:TRUNCATION_LIMIT]\n'
            '            new_row[col] = val\n'
            '        result.append(new_row)\n'
            '    return result\n'
        )

        # ── pipeline/load.py (BUG: swaps col2 and col3) ─────────────────
        # Build the swapped mapping
        swapped_columns = list(columns)
        swapped_columns[1], swapped_columns[2] = swapped_columns[2], swapped_columns[1]

        files["pipeline/load.py"] = (
            'import csv\n'
            'import os\n'
            '\n'
            f'COLUMNS = {columns!r}\n'
            '\n'
            '# BUG: Output column order is wrong — col2 and col3 are swapped\n'
            f'OUTPUT_COLUMNS = {swapped_columns!r}\n'
            '\n'
            '\n'
            'def load(rows: list[dict], output_path: str) -> None:\n'
            '    """\n'
            '    Write transformed rows to output CSV.\n'
            '\n'
            '    BUG: Uses OUTPUT_COLUMNS which has col2 and col3 swapped.\n'
            '    Should use COLUMNS (the correct order from PIPELINE_SPEC.md).\n'
            '    """\n'
            '    os.makedirs(os.path.dirname(output_path), exist_ok=True)\n'
            '    with open(output_path, "w", newline="") as f:\n'
            '        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)\n'
            '        writer.writeheader()\n'
            '        for row in rows:\n'
            '            # Reorder row values according to OUTPUT_COLUMNS\n'
            '            ordered = {col: row.get(col, "") for col in OUTPUT_COLUMNS}\n'
            '            writer.writerow(ordered)\n'
        )

        # ── pipeline/run_pipeline.py ─────────────────────────────────────
        files["pipeline/run_pipeline.py"] = (
            'import os\n'
            'import sys\n'
            '\n'
            '# Add parent directory to path\n'
            'sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n'
            '\n'
            'from pipeline.extract import extract\n'
            'from pipeline.transform import transform\n'
            'from pipeline.load import load\n'
            '\n'
            '\n'
            'def main():\n'
            '    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
            '    input_path = os.path.join(base_dir, "data", "source.csv")\n'
            '    output_path = os.path.join(base_dir, "data", "output.csv")\n'
            '\n'
            '    # Stage 1: Extract\n'
            '    rows = extract(input_path)\n'
            '    print(f"Extracted {len(rows)} rows")\n'
            '\n'
            '    # Stage 2: Transform\n'
            '    rows = transform(rows)\n'
            '    print(f"Transformed {len(rows)} rows")\n'
            '\n'
            '    # Stage 3: Load\n'
            '    load(rows, output_path)\n'
            '    print(f"Loaded {len(rows)} rows to {output_path}")\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        )

        # ── tests/test_pipeline.py ───────────────────────────────────────
        files["tests/__init__.py"] = ""
        files["tests/test_pipeline.py"] = (
            'import csv\n'
            'import os\n'
            'import sys\n'
            'import pytest\n'
            '\n'
            'sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))\n'
            '\n'
            'from pipeline.extract import extract\n'
            'from pipeline.transform import transform\n'
            'from pipeline.load import load\n'
            '\n'
            '\n'
            '@pytest.fixture\n'
            'def base_dir():\n'
            '    return os.path.join(os.path.dirname(__file__), "..")\n'
            '\n'
            '\n'
            'def test_extract_keeps_rows_with_nonkey_nulls(base_dir):\n'
            '    """Rows with empty non-key columns should be kept."""\n'
            '    rows = extract(os.path.join(base_dir, "data", "source.csv"))\n'
            f'    # Should keep {expected_count} rows (drop only key-column-null rows)\n'
            f'    assert len(rows) == {expected_count}, \\\n'
            f'        f"Expected {expected_count} rows after extract, got {{len(rows)}}"\n'
            '\n'
            '\n'
            'def test_extract_drops_key_null_rows(base_dir):\n'
            '    """Rows with empty key columns should be dropped."""\n'
            '    rows = extract(os.path.join(base_dir, "data", "source.csv"))\n'
            '    for row in rows:\n'
            f'        for key_col in {key_cols!r}:\n'
            '            assert row.get(key_col, "").strip(), \\\n'
            '                f"Row with empty key column {{key_col}} should have been dropped"\n'
            '\n'
            '\n'
            f'def test_transform_truncation_limit(base_dir):\n'
            f'    """Strings should be truncated at {trunc_limit} chars, not 50."""\n'
            f'    rows = extract(os.path.join(base_dir, "data", "source.csv"))\n'
            f'    transformed = transform(rows)\n'
            f'    for row in transformed:\n'
            f'        for col in {columns!r}:\n'
            f'            val = row.get(col, "")\n'
            f'            assert len(val) <= {trunc_limit}, \\\n'
            f'                f"Column {{col}} value exceeds {trunc_limit} chars: {{len(val)}}"\n'
            '\n'
            '\n'
            'def test_transform_preserves_short_strings(base_dir):\n'
            '    """Strings shorter than limit should not be modified (except stripping)."""\n'
            '    rows = extract(os.path.join(base_dir, "data", "source.csv"))\n'
            '    transformed = transform(rows)\n'
            '    # At least some rows should have non-empty values preserved\n'
            '    assert any(row.get("' + col1 + '", "").strip() for row in transformed)\n'
            '\n'
            '\n'
            'def test_load_column_order(base_dir, tmp_path):\n'
            '    """Output columns must be in correct order."""\n'
            '    rows = extract(os.path.join(base_dir, "data", "source.csv"))\n'
            '    transformed = transform(rows)\n'
            '    output_path = str(tmp_path / "test_output.csv")\n'
            '    load(transformed, output_path)\n'
            '    with open(output_path) as f:\n'
            '        reader = csv.reader(f)\n'
            '        header = next(reader)\n'
            f'    assert header == {columns!r}, \\\n'
            f'        f"Column order mismatch: {{header}} != {columns!r}"\n'
            '\n'
            '\n'
            'def test_full_pipeline_matches_expected(base_dir):\n'
            '    """Full pipeline output must match expected_output.csv."""\n'
            '    import subprocess\n'
            '    subprocess.run(\n'
            '        [sys.executable, "pipeline/run_pipeline.py"],\n'
            '        cwd=base_dir, check=True, capture_output=True\n'
            '    )\n'
            '    with open(os.path.join(base_dir, "data", "output.csv")) as f:\n'
            '        actual = f.read().strip()\n'
            '    with open(os.path.join(base_dir, "data", "expected_output.csv")) as f:\n'
            '        expected = f.read().strip()\n'
            '    assert actual == expected, "Pipeline output does not match expected"\n'
        )

        files["requirements.txt"] = "pytest\n"

        return files
