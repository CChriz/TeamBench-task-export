"""
Parameterized generator for D7: ETL Reconciliation.

Each seed produces:
  - Different product names, order IDs, currencies, exchange rates
  - Different date ranges (off-by-one at different boundary dates)
  - Different refunded order IDs (double-counting bug)
  - Different negative-quantity rows and future-dated rows
  - Different expected totals after all 5 fixes
"""
from __future__ import annotations

import csv
import io
import math
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool

# Seed-varying currency pools
CURRENCY_SETS = [
    [("USD", 1.0), ("EUR", 1.08), ("GBP", 1.27), ("JPY", 0.0067)],
    [("USD", 1.0), ("CAD", 0.74), ("AUD", 0.65), ("MXN", 0.059)],
    [("USD", 1.0), ("CHF", 1.11), ("SEK", 0.096), ("NOK", 0.093)],
]

# Product name pools per seed
PRODUCT_POOLS = [
    ["Widget-A", "Widget-B", "Gadget-X", "Gadget-Y", "Module-Z"],
    ["Alpha-Pro", "Beta-Lite", "Gamma-Max", "Delta-Core", "Epsilon-Plus"],
    ["Bolt-100", "Spark-200", "Flux-300", "Wave-400", "Pulse-500"],
]

# Processing date anchors
PROC_DATES = ["2024-03-31", "2024-06-30", "2024-09-30"]


class Generator(TaskGenerator):
    task_id = "D7_etl_reconciliation"
    domain = "data"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=20)

        cidx = seed % len(CURRENCY_SETS)
        currencies = CURRENCY_SETS[cidx]
        products = PRODUCT_POOLS[seed % len(PRODUCT_POOLS)]
        proc_date = PROC_DATES[seed % len(PROC_DATES)]

        # Date range: start to end (end exclusive in buggy code via < instead of <=)
        year = int(proc_date[:4])
        month = int(proc_date[5:7])
        # Range is month - 2 to proc_date month
        start_month = month - 2
        start_year = year
        if start_month < 1:
            start_month += 12
            start_year -= 1
        date_start = f"{start_year}-{start_month:02d}-01"
        date_end = proc_date  # inclusive (boundary bug: buggy code uses <, not <=)

        # Build exchange rate table: currency -> (correct_col, wrong_col)
        # BUG 1: transform.py reads "rate_v1" (wrong) instead of "rate_usd" (correct)
        exc_rows = []
        for curr, rate in currencies:
            wrong_rate = round(rate * rng.uniform(0.85, 0.95), 4)
            exc_rows.append({
                "currency": curr,
                "rate_usd": round(rate, 4),
                "rate_v1": round(wrong_rate, 4),    # wrong column used by buggy code
                "rate_prev": round(rate * 0.98, 4),  # another decoy column
            })
        exc_map_correct = {r["currency"]: r["rate_usd"] for r in exc_rows}
        exc_map_wrong = {r["currency"]: r["rate_v1"] for r in exc_rows}

        # Generate orders
        orders = []
        order_id = 1000 + seed * 100
        all_ids = []

        # Normal orders (within date range, positive qty)
        for i in range(12):
            order_id += 1
            curr = rng.choice([c[0] for c in currencies])
            product = rng.choice(products)
            qty = rng.randint(1, 20)
            unit_price = round(rng.uniform(10.0, 500.0), 2)
            # Date within range
            m = start_month + (i % 3)
            if m > 12:
                m -= 12
            d = rng.randint(1, 28)
            order_date = f"{start_year}-{m:02d}-{d:02d}"
            # Clamp to range
            if order_date < date_start:
                order_date = date_start[:7] + f"-{d:02d}"
            orders.append({
                "order_id": str(order_id),
                "customer": names.next(),
                "product": product,
                "quantity": str(qty),
                "unit_price": str(unit_price),
                "currency": curr,
                "order_date": order_date,
                "status": "completed",
            })
            all_ids.append(order_id)

        # Boundary date order (on proc_date — should be INCLUDED, buggy code excludes it)
        order_id += 1
        boundary_currency = rng.choice([c[0] for c in currencies])
        boundary_qty = rng.randint(2, 8)
        boundary_price = round(rng.uniform(50.0, 300.0), 2)
        boundary_amount_correct = round(
            boundary_qty * boundary_price * exc_map_correct[boundary_currency], 2
        )
        orders.append({
            "order_id": str(order_id),
            "customer": names.next(),
            "product": rng.choice(products),
            "quantity": str(boundary_qty),
            "unit_price": str(boundary_price),
            "currency": boundary_currency,
            "order_date": proc_date,   # exactly on proc_date (off-by-one excludes this)
            "status": "completed",
        })
        boundary_id = order_id
        all_ids.append(order_id)

        # Refunded order (BUG 3: double-counted in aggregation)
        order_id += 1
        refund_currency = rng.choice([c[0] for c in currencies])
        refund_qty = rng.randint(1, 5)
        refund_price = round(rng.uniform(20.0, 150.0), 2)
        refund_m = start_month + 1
        if refund_m > 12:
            refund_m -= 12
        orders.append({
            "order_id": str(order_id),
            "customer": names.next(),
            "product": rng.choice(products),
            "quantity": str(refund_qty),
            "unit_price": str(refund_price),
            "currency": refund_currency,
            "order_date": f"{start_year}-{refund_m:02d}-15",
            "status": "refunded",
        })
        refunded_id = order_id
        all_ids.append(order_id)

        # Negative quantity row (BUG 4: should be filtered)
        order_id += 1
        neg_currency = rng.choice([c[0] for c in currencies])
        orders.append({
            "order_id": str(order_id),
            "customer": names.next(),
            "product": rng.choice(products),
            "quantity": str(-rng.randint(1, 5)),  # negative
            "unit_price": str(round(rng.uniform(30.0, 200.0), 2)),
            "currency": neg_currency,
            "order_date": f"{start_year}-{start_month:02d}-10",
            "status": "completed",
        })
        neg_id = order_id
        all_ids.append(order_id)

        # Future-dated row (BUG 5: should be flagged, NOT filtered)
        order_id += 1
        future_year = year + 1
        future_currency = rng.choice([c[0] for c in currencies])
        future_qty = rng.randint(1, 10)
        future_price = round(rng.uniform(25.0, 250.0), 2)
        future_amount = round(
            future_qty * future_price * exc_map_correct[future_currency], 2
        )
        orders.append({
            "order_id": str(order_id),
            "customer": names.next(),
            "product": rng.choice(products),
            "quantity": str(future_qty),
            "unit_price": str(future_price),
            "currency": future_currency,
            "order_date": f"{future_year}-01-15",
            "status": "completed",
        })
        future_id = order_id
        all_ids.append(order_id)

        # ── Compute expected totals ──
        # Correct: include all rows except negative qty, use correct exchange rate,
        # include boundary-date row, exclude refunded, flag future
        correct_total = 0.0
        for o in orders:
            oid = int(o["order_id"])
            qty = int(o["quantity"])
            price = float(o["unit_price"])
            curr = o["currency"]
            status = o["status"]
            if qty < 0:
                continue  # filter negatives
            if status == "refunded":
                continue  # exclude refunded
            correct_total += qty * price * exc_map_correct[curr]
        correct_total = round(correct_total, 2)

        # Buggy total (wrong exchange rate column + off-by-one + double-count refund)
        buggy_total = 0.0
        for o in orders:
            oid = int(o["order_id"])
            qty = int(o["quantity"])
            price = float(o["unit_price"])
            curr = o["currency"]
            status = o["status"]
            odate = o["order_date"]
            # Off-by-one: exclude proc_date rows
            if odate == proc_date:
                continue
            # No negative filter
            # Double-count refunded: refunded orders ARE included
            buggy_total += qty * price * exc_map_wrong[curr]
        buggy_total = round(buggy_total, 2)

        expected = {
            "correct_total_usd": correct_total,
            "buggy_total_usd": buggy_total,
            "boundary_order_id": str(boundary_id),
            "boundary_amount_usd": boundary_amount_correct,
            "refunded_order_id": str(refunded_id),
            "negative_qty_order_id": str(neg_id),
            "future_date_order_id": str(future_id),
            "future_date_flagged": True,
            "proc_date": proc_date,
            "correct_exchange_col": "rate_usd",
            "wrong_exchange_col": "rate_v1",
            "bugs": [
                "wrong_exchange_rate_column",
                "off_by_one_date_filter",
                "double_count_refunded",
                "no_negative_qty_filter",
                "future_date_not_flagged",
            ],
        }

        workspace_files = self._build_workspace(
            orders, exc_rows, proc_date, date_start, date_end,
            refunded_id, neg_id, future_id, boundary_id,
            exc_map_correct, correct_total,
        )

        spec_md = self._spec()
        brief_md = self._brief()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── file builders ──────────────────────────────────────────────────────

    def _build_workspace(
        self, orders, exc_rows, proc_date, date_start, date_end,
        refunded_id, neg_id, future_id, boundary_id,
        exc_map_correct, correct_total,
    ) -> dict[str, str]:
        files = {}

        def to_csv(rows: list[dict]) -> str:
            if not rows:
                return ""
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
            return out.getvalue()

        files["data/source.csv"] = to_csv(orders)
        files["data/exchange_rates.csv"] = to_csv(exc_rows)

        # expected_output.csv: correctly transformed rows
        expected_rows = []
        for o in orders:
            qty = int(o["quantity"])
            price = float(o["unit_price"])
            curr = o["currency"]
            status = o["status"]
            odate = o["order_date"]
            if qty < 0:
                continue
            if status == "refunded":
                continue
            amt = round(qty * price * exc_map_correct[curr], 2)
            flagged = "future_date" if odate > proc_date else ""
            expected_rows.append({
                "order_id": o["order_id"],
                "customer": o["customer"],
                "product": o["product"],
                "quantity": qty,
                "amount_usd": amt,
                "order_date": odate,
                "status": status,
                "flagged": flagged,
            })
        files["data/expected_output.csv"] = to_csv(expected_rows)

        # actual_output.csv: buggy output for comparison (wrong exchange, off-by-one, no neg filter)
        actual_rows = []
        for o in orders:
            qty = int(o["quantity"])
            price = float(o["unit_price"])
            curr = o["currency"]
            odate = o["order_date"]
            if odate == proc_date:
                continue  # off-by-one excludes boundary
            exc_map_wrong = {r["currency"]: r["rate_v1"] for r in exc_rows}
            amt = round(qty * price * exc_map_wrong[curr], 2)
            actual_rows.append({
                "order_id": o["order_id"],
                "customer": o["customer"],
                "product": o["product"],
                "quantity": qty,
                "amount_usd": amt,
                "order_date": odate,
                "status": o["status"],
                "flagged": "",
            })
        files["data/actual_output.csv"] = to_csv(actual_rows)

        files["etl/extract.py"] = '''\
"""Extract: load source CSV into records list."""
import csv


def extract(source_path: str) -> list[dict]:
    """Load all rows from source CSV."""
    records = []
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records
'''

        files["etl/transform.py"] = f'''\
"""Transform: apply business rules and currency conversion.

Known issues (do not fix the comments — fix the code):
  BUG1: Uses wrong exchange rate column
  BUG2: Off-by-one date filter (excludes last day)
  BUG3: Refunded orders double-counted in aggregation
  BUG4: Negative quantity rows not filtered
  BUG5: Future-dated rows not flagged
"""
import csv
from datetime import datetime


def load_exchange_rates(rates_path: str) -> dict:
    """Load exchange rates. Returns dict of currency -> rate."""
    rates = {{}}
    with open(rates_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # BUG1: Should use "rate_usd" not "rate_v1"
            rates[row["currency"]] = float(row["rate_v1"])
    return rates


def transform(
    records: list[dict],
    rates: dict,
    date_start: str,
    date_end: str,
    proc_date: str,
) -> list[dict]:
    """Apply transformations to records."""
    output = []
    for rec in records:
        order_date = rec.get("order_date", "")

        # BUG2: Should be <= date_end, not < date_end
        if order_date < date_start or order_date < date_end:
            if order_date >= date_start:
                pass
            else:
                continue

        # Apply date filter correctly (still has bug — see above)
        if not (date_start <= order_date < date_end):  # BUG2: < should be <=
            continue

        qty = int(rec.get("quantity", "0"))
        # BUG4: Should filter qty < 0, but this code does nothing

        unit_price = float(rec.get("unit_price", "0"))
        currency = rec.get("currency", "USD")
        rate = rates.get(currency, 1.0)
        amount_usd = round(qty * unit_price * rate, 2)

        status = rec.get("status", "")
        # BUG3: Refunded orders should be excluded — currently included

        # BUG5: Future-dated rows must have flagged="future_date"
        flagged = ""

        output.append({{
            "order_id": rec["order_id"],
            "customer": rec.get("customer", ""),
            "product": rec.get("product", ""),
            "quantity": qty,
            "amount_usd": amount_usd,
            "order_date": order_date,
            "status": status,
            "flagged": flagged,
        }})

    return output


def aggregate(records: list[dict]) -> float:
    """Sum total USD amount."""
    # BUG3: refunded orders already in records — should be excluded before summing
    return round(sum(r["amount_usd"] for r in records), 2)
'''

        files["etl/load.py"] = '''\
"""Load: write transformed records to output CSV."""
import csv
import os


def load(records: list[dict], output_path: str) -> None:
    """Write records to output CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not records:
        return
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
'''

        files["run_etl.py"] = f'''\
"""ETL runner — orchestrates extract, transform, load."""
import sys
from etl.extract import extract
from etl.transform import load_exchange_rates, transform, aggregate
from etl.load import load

SOURCE = "data/source.csv"
RATES = "data/exchange_rates.csv"
OUTPUT = "data/actual_output.csv"
PROC_DATE = "{proc_date}"
DATE_START = "{date_start}"
DATE_END = "{date_end}"


def main():
    records = extract(SOURCE)
    print(f"Extracted {{len(records)}} records")

    rates = load_exchange_rates(RATES)
    transformed = transform(records, rates, DATE_START, DATE_END, PROC_DATE)
    print(f"Transformed {{len(transformed)}} records")

    total = aggregate(transformed)
    print(f"Total USD: {{total}}")

    load(transformed, OUTPUT)
    print(f"Output written to {{OUTPUT}}")
    return total


if __name__ == "__main__":
    main()
'''

        files["RECONCILIATION_SPEC.md"] = f'''\
# Reconciliation Specification

## Processing Date
`{proc_date}` — all orders on or before this date must be included.

## Date Filter Rule
Include orders where `date_start <= order_date <= date_end`.
The boundary (proc_date = {proc_date}) is INCLUSIVE.

## Exchange Rate
Use column `rate_usd` from `data/exchange_rates.csv`.
Do NOT use `rate_v1` or `rate_prev`.

## Data Quality Rules
- Orders with `quantity < 0` must be EXCLUDED before transformation.
- Orders with `status = "refunded"` must be EXCLUDED from totals.
- Orders with `order_date > proc_date` must remain in output with `flagged = "future_date"`.
  They must NOT be excluded.

## Expected Output
- File: `data/expected_output.csv`
- Columns: `order_id, customer, product, quantity, amount_usd, order_date, status, flagged`
- Total amount_usd: `{correct_total}` USD

## Deliverables
- Fixed `etl/transform.py`
- `RECONCILIATION_REPORT.md` documenting each of the 5 issues found and fixed
'''

        return files

    def _spec(self) -> str:
        return """\
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
"""

    def _brief(self) -> str:
        return """\
# D7: ETL Reconciliation (Brief)

Fix the ETL pipeline in `etl/transform.py`. There are 5 issues (3 transform bugs +
2 data quality problems). After fixing, output must match `data/expected_output.csv`.
Write `RECONCILIATION_REPORT.md` documenting what you found.
Run: `python run_etl.py`
"""
