"""
Parameterized generator for D2: Data Quality + Spec Compliance.

Each seed produces:
  - Different column names (score-like field, department-like field)
  - Different number of rows (20-40)
  - Different duplicate entries (which ids are duped)
  - Different missing value placements
  - Different invalid format / out-of-range values
  - Different expected row count and spot-check values
  - A buggy clean.py with intentional errors
  - Seed-specific spec.md and brief.md
"""
from __future__ import annotations

import csv
import io
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import (
    SeededRandom, NamePool, ValuePool, DEPARTMENTS,
)

# Possible column name aliases for the "score" and "department" fields
SCORE_ALIASES = ["score", "rating", "points", "grade", "marks"]
DEPT_ALIASES = ["department", "division", "team", "group", "unit"]

# Fill sentinel used in the buggy clean.py (wrong value — should be MISSING)
WRONG_FILL = "N/A"
CORRECT_FILL = "MISSING"


class Generator(TaskGenerator):
    task_id = "D2_data_quality"
    domain = "data"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=50)

        # ── Pick seed-specific column names ──
        score_col = rng.choice(SCORE_ALIASES)
        dept_col = rng.choice(DEPT_ALIASES)

        # Choose departments pool for this seed
        dept_pool = rng.sample(DEPARTMENTS, 5)

        # ── Decide row count ──
        n_rows = rng.randint(20, 40)

        # ── Generate base records ──
        records = []
        for i in range(1, n_rows + 1):
            dept = rng.choice(dept_pool)
            score = rng.randint(0, 100)
            records.append({
                "id": str(i),
                "name": names.next(),
                score_col: str(score),
                dept_col: dept,
            })

        # ── Inject duplicate rows ──
        # Pick 2 ids to duplicate
        dup_ids = rng.sample([r["id"] for r in records[:n_rows // 2]], 2)
        dup_records = []
        dup_map = {}  # id -> (original_score, dup_score, winner_score)
        for did in dup_ids:
            orig = next(r for r in records if r["id"] == did)
            orig_score = int(orig[score_col])
            # Generate a different score for the duplicate
            new_score = rng.randint(0, 100)
            while new_score == orig_score:
                new_score = rng.randint(0, 100)
            winner = max(orig_score, new_score)
            dup_map[did] = {
                "original_score": orig_score,
                "dup_score": new_score,
                "winner_score": winner,
            }
            dup_records.append({
                "id": did,
                "name": names.next(),  # different name in duplicate
                score_col: str(new_score),
                dept_col: rng.choice(dept_pool),
            })

        # ── Inject out-of-range rows (score > 100 or < 0) ──
        # Pick 2 ids for out-of-range — will be dropped
        out_of_range_ids = []
        out_of_range_id_counter = n_rows + 1
        for _ in range(2):
            bad_score = rng.choice([rng.randint(101, 200), rng.randint(-50, -1)])
            out_of_range_ids.append(str(out_of_range_id_counter))
            records.append({
                "id": str(out_of_range_id_counter),
                "name": names.next(),
                score_col: str(bad_score),
                dept_col: rng.choice(dept_pool),
            })
            out_of_range_id_counter += 1

        # ── Inject missing value rows ──
        # Pick 3 rows to have missing values
        missing_candidates = [r for r in records if r["id"] not in dup_ids and r["id"] not in out_of_range_ids]
        missing_rows = rng.sample(missing_candidates, min(3, len(missing_candidates)))
        missing_ids = []
        low_score_missing_dept_id = None  # id where dept missing AND score < 50

        for i, row in enumerate(missing_rows):
            if i == 0:
                # Missing score
                row[score_col] = ""
                missing_ids.append(row["id"])
            elif i == 1:
                # Missing dept — and score < 50 so review_needed applies
                row[dept_col] = ""
                # Force score < 50
                row[score_col] = str(rng.randint(0, 49))
                missing_ids.append(row["id"])
                low_score_missing_dept_id = row["id"]
            else:
                # Missing name
                row["name"] = ""
                missing_ids.append(row["id"])

        # ── Build the full CSV rows (base + dups, shuffled) ──
        all_rows = records + dup_records
        rng.shuffle(all_rows)

        # ── Compute expected output ──
        # 1. Dedup: keep higher score
        by_id: dict[str, dict] = {}
        for row in all_rows:
            rid = row["id"]
            try:
                s = int(row[score_col]) if row[score_col] else 0
            except ValueError:
                s = 0
            if rid not in by_id:
                by_id[rid] = row.copy()
            else:
                try:
                    existing_s = int(by_id[rid][score_col]) if by_id[rid][score_col] else 0
                except ValueError:
                    existing_s = 0
                if s > existing_s:
                    by_id[rid] = row.copy()

        deduped = list(by_id.values())

        # 2. Drop out-of-range rows (score outside 0-100, skip if empty/MISSING)
        filtered = []
        for row in deduped:
            s_str = row[score_col]
            if s_str == "" or s_str is None:
                filtered.append(row)  # missing score rows kept (will be filled)
                continue
            try:
                s = int(s_str)
                if 0 <= s <= 100:
                    filtered.append(row)
                # else drop it
            except ValueError:
                filtered.append(row)

        # 3. Fill missing values with MISSING
        for row in filtered:
            for key in [score_col, dept_col, "name"]:
                if row.get(key) == "" or row.get(key) is None:
                    row[key] = CORRECT_FILL

        # 4. Department correction: MISSING dept + score < 50 -> review_needed
        for row in filtered:
            if row[dept_col] == CORRECT_FILL:
                try:
                    s = int(row[score_col]) if row[score_col] != CORRECT_FILL else 999
                except ValueError:
                    s = 999
                if s < 50:
                    row[dept_col] = "review_needed"

        # 5. Sort: score descending, name ascending
        def sort_key(r):
            s_str = r[score_col]
            s = -1 if s_str == CORRECT_FILL else int(s_str)
            return (-s, r["name"])

        filtered.sort(key=sort_key)

        expected_row_count = len(filtered)

        # Build spot-check maps
        id_score_map = {r["id"]: r[score_col] for r in filtered}
        id_dept_map = {r["id"]: r[dept_col] for r in filtered}

        expected = {
            "row_count": expected_row_count,
            "columns": ["id", "name", score_col, dept_col],
            "score_col": score_col,
            "dept_col": dept_col,
            "dup_ids": dup_ids,
            "dup_winner_scores": {did: str(info["winner_score"]) for did, info in dup_map.items()},
            "out_of_range_ids": out_of_range_ids,
            "missing_ids": missing_ids,
            "low_score_missing_dept_id": low_score_missing_dept_id,
            "correct_fill": CORRECT_FILL,
            "review_needed_id": low_score_missing_dept_id,
        }

        # ── Generate workspace files ──
        def to_csv(rows: list[dict], cols: list[str]) -> str:
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=cols)
            writer.writeheader()
            writer.writerows(rows)
            return out.getvalue()

        csv_cols = ["id", "name", score_col, dept_col]
        input_csv = to_csv(all_rows, csv_cols)

        clean_py = self._generate_buggy_clean(score_col, dept_col)
        spec_md = self._generate_spec(score_col, dept_col)
        brief_md = self._generate_brief()

        workspace_files = {
            "data/input/records.csv": input_csv,
            "clean.py": clean_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_buggy_clean(self, score_col: str, dept_col: str) -> str:
        """Generate a buggy clean.py with intentional errors the agent must fix."""
        return f'''"""Data quality pipeline — clean and validate records."""
import csv
import os

# BUG: fill_value should be "MISSING", not "N/A"
# BUG: dedup_keep should be "highest", not "first"
# BUG: sort_by should be score desc + name asc, not just name
# BUG: range check only filters score > max, missing score < min check
RULES = {{
    "fill_value": "N/A",
    "dedup_keep": "first",
    "sort_by": "name",
    "range_min": 0,
    "range_max": 100,
}}


def run():
    input_path = "data/input/records.csv"
    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # BUG: keeps first occurrence, should keep highest score
    seen_ids = set()
    deduped = []
    for row in rows:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            deduped.append(row)

    # BUG: only drops score > max, not score < min
    filtered = []
    for row in deduped:
        score = int(row["{score_col}"]) if row["{score_col}"] else 0
        if score > RULES["range_max"]:
            continue
        filtered.append(row)

    # Fill missing values
    for row in filtered:
        for key in row:
            if row[key] == "" or row[key] is None:
                row[key] = RULES["fill_value"]

    # BUG: no department correction logic (MISSING + score < 50 -> review_needed)

    # BUG: sorts by name only, not score desc then name asc
    filtered.sort(key=lambda r: r[RULES["sort_by"]])

    with open(os.path.join(output_dir, "clean.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "{score_col}", "{dept_col}"])
        writer.writeheader()
        for row in filtered:
            writer.writerow(row)


if __name__ == "__main__":
    run()
'''

    def _generate_spec(self, score_col: str, dept_col: str) -> str:
        return f"""# D2: Data Quality + Spec Compliance

## Goal
Process the input dataset and produce output that satisfies ALL quality rules.

## Hard Requirements

1. Read `data/input/records.csv` and produce `data/output/clean.csv`.
2. Script: `python clean.py`
3. Quality rules:
   - **Missing values**: Any cell with empty string or `"N/A"` must be replaced with `"MISSING"`.
   - **Sort order**: Output must be sorted by `{score_col}` descending, then by `name` ascending (alphabetical).
   - **Deduplication**: Rows with the same `id` must be deduplicated, keeping the row with the higher `{score_col}`.
   - **Range check**: `{score_col}` must be between 0 and 100 inclusive. Rows outside this range must be dropped entirely.
   - **Department correction**: Rows where `{dept_col}` resolves to `"MISSING"` AND `{score_col}` is less than 50 must have their `{dept_col}` value set to `"review_needed"` rather than left as `"MISSING"`.
4. Output columns: `[id, name, {score_col}, {dept_col}]` — exact order.
5. No header row modifications (keep original column names).
6. Output must use UTF-8 encoding with Unix line endings.

## Deliverables
- Fixed `clean.py` in workspace.
- Verifier must confirm all quality rules and produce attestation.
"""

    def _generate_brief(self) -> str:
        return """# D2: Data Quality (Brief)

Process the dataset according to the data quality rules.
The Planner has the specific rule definitions.
Run: `python clean.py`
Input: `data/input/records.csv` -> Output: `data/output/clean.csv`
"""
