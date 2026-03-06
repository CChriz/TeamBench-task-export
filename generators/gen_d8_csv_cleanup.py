"""
Parameterized generator for D8: CSV Data Cleanup.

Each seed produces:
  - Different column names and row counts
  - Different data quality issues (duplicates, dates, whitespace, delimiters)
  - A messy CSV and a stub clean.py
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool

DATE_FORMATS_CORRECT = [
    "2023-01-15", "2023-03-22", "2023-06-01", "2023-07-14",
    "2023-08-30", "2023-09-12", "2023-10-05", "2023-11-20",
    "2023-12-01", "2024-01-10", "2024-02-28", "2024-03-15",
]
DATE_FORMATS_MMDDYYYY = [
    "01/15/2023", "03/22/2023", "06/01/2023", "07/14/2023",
]
DATE_FORMATS_DDMONYYYY = [
    "15-Jan-2023", "22-Mar-2023", "01-Jun-2023", "14-Jul-2023",
]

CATEGORY_POOLS = [
    ["electronics", "clothing", "food", "books", "toys"],
    ["hardware", "software", "services", "consulting", "support"],
    ["alpha", "beta", "gamma", "delta", "epsilon"],
]

EMPTY_COL_NAMES = ["notes", "comments", "remarks", "memo", "annotation"]


class Generator(TaskGenerator):
    task_id = "D8_csv_cleanup"
    domain = "data"
    difficulty = "easy"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=30)
        categories = CATEGORY_POOLS[seed % len(CATEGORY_POOLS)]
        empty_col = rng.choice(EMPTY_COL_NAMES)

        n_rows = rng.randint(15, 25)
        rows = []
        for i in range(1, n_rows + 1):
            name = names.next()
            cat = rng.choice(categories)
            amount = rng.randint(10, 500)
            date = rng.choice(DATE_FORMATS_CORRECT)
            rows.append({
                "id": str(i),
                "name": name,
                "category": cat,
                "amount": str(amount),
                "date": date,
                empty_col: "",
            })

        # Inject duplicates: pick 2 IDs to duplicate
        dup_ids = rng.sample([r["id"] for r in rows[:n_rows // 2]], 2)
        dup_rows = []
        for did in dup_ids:
            orig = next(r for r in rows if r["id"] == did)
            dup_rows.append(dict(orig))

        # Inject mixed date formats for 4 rows
        date_mix_ids = rng.sample([r["id"] for r in rows if r["id"] not in dup_ids], 4)
        date_checks = {}
        for i, did in enumerate(date_mix_ids):
            row = next(r for r in rows if r["id"] == did)
            correct_date = row["date"]
            if i < 2:
                # MM/DD/YYYY format
                parts = correct_date.split("-")
                row["date"] = f"{parts[1]}/{parts[2]}/{parts[0]}"
            else:
                # DD-Mon-YYYY format
                months = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                          "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                          "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
                parts = correct_date.split("-")
                row["date"] = f"{parts[2]}-{months[parts[1]]}-{parts[0]}"
            date_checks[did] = correct_date

        # Inject trailing whitespace for 3 rows
        ws_ids = rng.sample([r["id"] for r in rows if r["id"] not in dup_ids and r["id"] not in date_mix_ids], 3)
        for did in ws_ids:
            row = next(r for r in rows if r["id"] == did)
            row["name"] = row["name"] + "   "
            row["category"] = "  " + row["category"]

        # Combine and shuffle
        all_rows = rows + dup_rows
        rng.shuffle(all_rows)

        # Build CSV with some semicolon-delimited rows
        cols = ["id", "name", "category", "amount", "date", empty_col]
        header = ",".join(cols)
        csv_lines = [header]
        semi_ids = rng.sample([r["id"] for r in rows if r["id"] not in dup_ids][:8], 3)
        for row in all_rows:
            vals = [row.get(c, "") for c in cols]
            if row["id"] in semi_ids and all_rows.index(row) == [i for i, r in enumerate(all_rows) if r["id"] == row["id"]][0]:
                csv_lines.append(";".join(vals))
            else:
                csv_lines.append(",".join(vals))

        raw_csv = "\n".join(csv_lines) + "\n"

        # Expected: unique rows, no empty col, dates normalized, whitespace stripped, sorted by id
        expected_row_count = n_rows  # duplicates removed

        clean_py = self._make_clean_py(cols, empty_col)

        workspace_files = {
            "data/raw.csv": raw_csv,
            "clean.py": clean_py,
        }

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "row_count": expected_row_count,
                "dropped_columns": [empty_col],
                "date_checks": date_checks,
                "dup_ids": dup_ids,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "Data Engineering"},
        )

    def _make_clean_py(self, cols: list, empty_col: str) -> str:
        return f'''"""CSV cleanup script — fix data quality issues."""
import csv
import os

def run():
    os.makedirs("data", exist_ok=True)

    with open("data/raw.csv", "r", encoding="utf-8") as f:
        # BUG: does not handle semicolon-delimited rows
        reader = csv.DictReader(f)
        rows = list(reader)

    # BUG: no deduplication
    # BUG: no date normalization
    # BUG: no whitespace stripping
    # BUG: does not drop empty column "{empty_col}"

    # Write output (just copies input — all bugs remain)
    out_cols = list(rows[0].keys()) if rows else []
    with open("data/clean.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

if __name__ == "__main__":
    run()
'''
