"""
Parameterized generator for LH2: Budgeted Workflow.

Each seed produces:
- Different number of data files (3-5)
- Different file contents (varying field names, values, defects)
- Different budget limit (15-30)
- Different specific defect values (same 3 defect categories but different field names,
  datetime strings, and duplicate item sets)
- Seed-specific validate_all.py and budgeted_task.py
"""
from __future__ import annotations

import json
import random
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool


# Pool of plausible "wrong" field names for the schema violation defect
WRONG_FIELD_NAMES = [
    ("version", "ver"),
    ("version", "vers"),
    ("version", "v"),
    ("version", "schema_version"),
    ("version", "api_version"),
]

# Pool of config names for generated files
CONFIG_NAMES = [
    "config_alpha", "config_beta", "config_gamma", "config_delta",
    "config_epsilon", "config_zeta", "config_eta", "config_theta",
    "config_iota", "config_kappa", "data_source", "pipeline_run",
    "batch_job", "etl_config", "export_config",
]

# Item pools for generating unique and duplicate items
ITEM_POOLS = [
    ["apple", "banana", "Cherry", "cherry", "Date", "date", "elderberry"],
    ["project", "Query", "report", "Project", "query", "summary"],
    ["alpha", "Beta", "gamma", "ALPHA", "beta", "delta"],
    ["read", "Write", "execute", "READ", "write", "append"],
    ["north", "South", "east", "NORTH", "south", "west"],
    ["cat", "Dog", "Fish", "CAT", "dog", "bird"],
    ["red", "Blue", "green", "RED", "blue", "yellow"],
    ["open", "Close", "pending", "OPEN", "close", "resolved"],
]

# Datetime strings missing timezone
MISSING_TZ_DATETIMES = [
    "2025-06-15T00:00:00",
    "2025-03-20T08:30:00",
    "2025-09-01T12:00:00",
    "2025-11-11T11:11:11",
    "2025-07-04T15:00:00",
    "2025-01-01T00:00:00",
    "2025-05-15T09:45:00",
    "2024-12-31T23:59:59",
]

# Valid timezone-aware datetime strings
VALID_DATETIMES = [
    "2025-06-01T10:00:00Z",
    "2025-04-10T14:30:00+00:00",
    "2025-08-20T16:00:00Z",
    "2025-02-14T09:00:00+00:00",
    "2025-10-31T20:00:00Z",
]


class Generator(TaskGenerator):
    task_id = "LH2_budgeted_workflow"
    domain = "data"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Vary number of data files (3-5)
        num_files = rng.randint(3, 5)

        # Budget limit (15-30)
        budget_limit = rng.randint(15, 30)

        # Pick wrong field name for file_a defect
        wrong_field_idx = rng.randint(0, len(WRONG_FIELD_NAMES) - 1)
        correct_field, wrong_field = WRONG_FIELD_NAMES[wrong_field_idx]

        # Pick missing-tz datetime for file_b defect
        bad_dt_idx = rng.randint(0, len(MISSING_TZ_DATETIMES) - 1)
        bad_datetime = MISSING_TZ_DATETIMES[bad_dt_idx]

        # Pick valid datetimes for non-defect files
        valid_dt_pool = rng.sample(VALID_DATETIMES, min(num_files, len(VALID_DATETIMES)))

        # Pick item pool for file_c duplicates
        item_pool_idx = rng.randint(0, len(ITEM_POOLS) - 1)
        item_pool = ITEM_POOLS[item_pool_idx]

        # Build items with case-insensitive duplicates from pool
        # Must have at least one duplicate pair
        all_items = list(item_pool)
        rng.shuffle(all_items)
        file_c_items = all_items[:5]  # 5 items with some duplicates

        # Compute deduplicated items (keep lowercase, case-insensitive dedup)
        seen_lower = {}
        for item in file_c_items:
            k = item.lower()
            if k not in seen_lower:
                seen_lower[k] = item.lower()
        deduped_items = list(seen_lower.values())

        # Config names for files
        config_names = rng.sample(CONFIG_NAMES, num_files)

        # Build file contents
        data_files = {}
        file_defects = {}

        for i in range(num_files):
            fname = f"file_{chr(ord('a') + i)}.json"
            if i == 0:
                # file_a: wrong field name (schema violation)
                content = {
                    "name": config_names[i],
                    wrong_field: "1.0",
                    "created": valid_dt_pool[0],
                    "items": ["x", "y", "z"],
                }
                file_defects[fname] = {
                    "type": "schema_violation",
                    "wrong_field": wrong_field,
                    "correct_field": correct_field,
                }
            elif i == 1:
                # file_b: missing timezone
                content = {
                    "name": config_names[i],
                    "version": "1.0",
                    "created": bad_datetime,
                    "items": ["a", "b", "c"],
                }
                file_defects[fname] = {
                    "type": "format_error",
                    "bad_datetime": bad_datetime,
                }
            elif i == 2:
                # file_c: case-insensitive duplicates
                content = {
                    "name": config_names[i],
                    "version": "2.1",
                    "created": valid_dt_pool[min(2, len(valid_dt_pool) - 1)],
                    "items": file_c_items,
                }
                file_defects[fname] = {
                    "type": "data_integrity_error",
                    "items_with_duplicates": file_c_items,
                    "deduped_items": deduped_items,
                }
            else:
                # Extra files (for 4-5 file seeds): valid files
                valid_items = rng.sample(["p", "q", "r", "s", "t", "u"], 3)
                content = {
                    "name": config_names[i],
                    "version": "1.0",
                    "created": valid_dt_pool[min(i, len(valid_dt_pool) - 1)],
                    "items": valid_items,
                }
                file_defects[fname] = None  # no defect

            data_files[fname] = content

        # Files that need fixing (always 3 fixed for compatibility with grade.sh)
        files_to_fix = ["file_a.json", "file_b.json", "file_c.json"]

        expected = {
            "files_fixed": 3,
            "budget_limit": budget_limit,
            "num_files": num_files,
            "defects": file_defects,
            "wrong_field_name": wrong_field,
            "correct_field_name": correct_field,
            "bad_datetime": bad_datetime,
            "file_c_items_with_dups": file_c_items,
            "file_c_deduped": deduped_items,
        }

        # Generate workspace files
        workspace_files = {}

        for fname, content in data_files.items():
            workspace_files[f"data/{fname}"] = json.dumps(content, indent=2)

        workspace_files["budgeted_task.py"] = self._generate_budgeted_task(
            budget_limit, num_files,
        )
        workspace_files["validate_all.py"] = self._generate_validate_all(num_files)

        spec_md = self._generate_spec(budget_limit, wrong_field, correct_field, bad_datetime, file_c_items)
        brief_md = self._generate_brief(budget_limit)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_budgeted_task(self, budget_limit: int, num_files: int) -> str:
        file_list = [f'"file_{chr(ord("a") + i)}.json"' for i in range(num_files)]
        files_str = ", ".join(file_list)
        return f'''"""
Budgeted task: fix data files within execution budget.
Each significant operation is logged to budget_log.jsonl.
"""
import json
import os
from datetime import datetime, timezone


BUDGET_LOG = "budget_log.jsonl"
BUDGET_LIMIT = {budget_limit}


def log_execution(action, detail=""):
    entry = {{
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "detail": detail,
    }}
    with open(BUDGET_LOG, "a") as f:
        f.write(json.dumps(entry) + "\\n")


def get_budget_used():
    if not os.path.exists(BUDGET_LOG):
        return 0
    with open(BUDGET_LOG) as f:
        return sum(1 for line in f if line.strip())


def check_budget():
    used = get_budget_used()
    if used >= BUDGET_LIMIT:
        raise RuntimeError(f"Budget exhausted: {{used}}/{{BUDGET_LIMIT}}")
    return used


def load_file(path):
    check_budget()
    log_execution("read", path)
    with open(path, "r") as f:
        return json.load(f)


def save_file(path, data):
    check_budget()
    log_execution("write", path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def validate_file(path):
    """Validate a single data file. Returns (valid, errors)."""
    check_budget()
    log_execution("validate", path)
    data = json.load(open(path))
    errors = []

    if "version" not in data:
        errors.append("missing_version")

    created = data.get("created", "")
    try:
        datetime.fromisoformat(created.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        errors.append("invalid_date_format")

    items = data.get("items", [])
    if len(items) != len(set(items)):
        errors.append("duplicate_items")

    return len(errors) == 0, errors


def fix_file(path, errors):
    """Attempt to fix known errors in a data file."""
    check_budget()
    log_execution("fix", path)
    data = json.load(open(path))

    if "missing_version" in errors:
        data["version"] = "1.0"
    if "invalid_date_format" in errors:
        data["created"] = datetime.now(timezone.utc).isoformat()
    if "duplicate_items" in errors:
        data["items"] = list(dict.fromkeys(data["items"]))

    # Write fixed data to staging area
    staging = path + ".tmp"
    with open(staging, "w") as f:
        json.dump(data, f, indent=2)


def main():
    log_execution("start", "budgeted_task.py")
    os.makedirs("output", exist_ok=True)

    data_dir = "data"
    files = [{files_str}]

    results = {{}}
    for fname in files:
        path = os.path.join(data_dir, fname)
        data = load_file(path)

        valid, errors = validate_file(path)
        if not valid:
            print(f"{{fname}}: {{errors}}")
            fix_file(path, errors)
            results[fname] = "fixed"
        else:
            print(f"{{fname}}: OK")
            results[fname] = "ok"

    log_execution("end", "budgeted_task.py")

    budget_used = get_budget_used()
    report = {{
        "files_fixed": 0,
        "budget_total": BUDGET_LIMIT,
        "budget_used": budget_used,
        "all_valid": False,
    }}
    with open("output/budget_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Budget: {{budget_used}}/{{BUDGET_LIMIT}}")


if __name__ == "__main__":
    main()
'''

    def _generate_validate_all(self, num_files: int) -> str:
        file_list = [f'"file_{chr(ord("a") + i)}.json"' for i in range(num_files)]
        files_str = ", ".join(file_list)
        return f'''"""Validate all data files."""
import json
import os
import sys
from datetime import datetime


def validate_file(path):
    """Validate a data file against schema requirements."""
    data = json.load(open(path))
    errors = []

    # Run validation checks
    for check_name, check_fn in _get_checks():
        if not check_fn(data):
            errors.append(check_name)

    return errors


def _get_checks():
    """Internal validation checks."""
    return [
        ("schema_violation", lambda d: "version" in d),
        ("format_error", lambda d: _check_format(d)),
        ("data_integrity_error", lambda d: _check_integrity(d)),
    ]


def _check_format(data):
    created = data.get("created", "")
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return dt.tzinfo is not None
    except (ValueError, AttributeError):
        return False


def _check_integrity(data):
    items = data.get("items", [])
    seen = set()
    for i in items:
        k = i.lower() if isinstance(i, str) else str(i)
        if k in seen:
            return False
        seen.add(k)
    return True


def main():
    data_dir = "data"
    files = [{files_str}]
    all_valid = True

    for fname in files:
        path = os.path.join(data_dir, fname)
        errors = validate_file(path)
        if errors:
            print(f"FAIL {{fname}}: validation failed ({{len(errors)}} issue(s))")
            all_valid = False
        else:
            print(f"PASS {{fname}}")

    if all_valid:
        print("\\nALL FILES VALID")
        sys.exit(0)
    else:
        print("\\nVALIDATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    def _generate_spec(
        self,
        budget_limit: int,
        wrong_field: str,
        correct_field: str,
        bad_datetime: str,
        file_c_items: list,
    ) -> str:
        items_display = ", ".join(f'"{i}"' for i in file_c_items)
        return f"""# LH2: Budgeted Workflow

## Goal
Complete a multi-step task within a strict command execution budget.

## Hard Requirements

1. Run `python budgeted_task.py` to process data files.
2. The task requires finding and fixing 3 broken data files in `data/`.
3. **Budget**: Maximum {budget_limit} command executions total.
4. All 3 data files must be fixed. Each file contains a data quality defect that prevents it from passing validation:
   - `data/file_a.json`: contains a field named `{wrong_field}` whose name does not match the required schema field name `{correct_field}`.
   - `data/file_b.json`: contains a datetime field (`{bad_datetime}`) whose value is missing required timezone information.
   - `data/file_c.json`: contains an array field with case-insensitive duplicate entries [{items_display}] that must be deduplicated, retaining only the lowercase form of each duplicate group.
5. After fixing, run `python validate_all.py` which checks all files.
6. Final output: `output/budget_report.json`
7. `budget_used` must be <= {budget_limit}.

## Deliverables
- Fixed data files + `output/budget_report.json`.
- Verifier must confirm budget compliance and produce attestation.
"""

    def _generate_brief(self, budget_limit: int) -> str:
        return f"""# LH2: Budgeted Workflow (Brief)

Fix 3 broken data files within a budget of {budget_limit} command executions.
Run: `python budgeted_task.py`
Then validate: `python validate_all.py`
Output: `output/budget_report.json`
"""
