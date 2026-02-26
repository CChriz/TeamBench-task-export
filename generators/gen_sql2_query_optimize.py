"""
Parameterized generator for SQL2: Query Optimize.

TNI Pattern A, C (Hidden Constraints + Multi-Criteria):
  - Spec has: complete EXPLAIN query plan analysis identifying full table scans,
    missing indexes, and N+1 patterns; specific index types required (B-tree vs
    partial vs composite); dual targets: query latency budgets AND storage budget
    (total index size must stay under a cap); exact index naming convention.
  - Brief just says: "Queries are slow. Fix them."
  - Without the Planner's spec the Executor adds obvious single-column indexes
    but misses: (a) which index TYPE is required, (b) the storage budget cap,
    (c) the composite/covering index requirements, and (d) the naming convention.

Three seeds produce genuinely different instances:
  seed 0 -> e-commerce domain (orders/products/users/reviews)
  seed 1 -> logistics domain (shipments/warehouses/carriers/routes)
  seed 2 -> HR/payroll domain (employees/payroll/departments/timesheets)

Each instance generates:
  workspace/schema.sql    -- CREATE TABLE statements, NO indexes
  workspace/queries.sql   -- 5-8 slow queries with full-scan comments
  workspace/optimizer.py  -- skeleton that reads schema + applies optimizations
  reports/expected.json   -- ground truth for grading (never shown to agents)
"""
from __future__ import annotations

import json
from typing import Any

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool, ValuePool

# ---------------------------------------------------------------------------
# Domain catalog
# ---------------------------------------------------------------------------

DOMAINS: dict[str, dict] = {
    "ecommerce": {
        "label": "E-commerce (orders / products / users / reviews)",
        "tables": {
            "users": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "email TEXT NOT NULL UNIQUE",
                    "name TEXT NOT NULL",
                    "country TEXT NOT NULL",
                    "created_at TEXT NOT NULL",
                ],
                "row_count": 120000,
            },
            "products": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "sku TEXT NOT NULL UNIQUE",
                    "name TEXT NOT NULL",
                    "category TEXT NOT NULL",
                    "price REAL NOT NULL",
                    "stock INTEGER NOT NULL DEFAULT 0",
                ],
                "row_count": 45000,
            },
            "orders": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "user_id INTEGER NOT NULL",
                    "status TEXT NOT NULL",
                    "total REAL NOT NULL",
                    "created_at TEXT NOT NULL",
                    "shipped_at TEXT",
                ],
                "row_count": 800000,
            },
            "order_items": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "order_id INTEGER NOT NULL",
                    "product_id INTEGER NOT NULL",
                    "quantity INTEGER NOT NULL",
                    "unit_price REAL NOT NULL",
                ],
                "row_count": 2400000,
            },
            "reviews": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "product_id INTEGER NOT NULL",
                    "user_id INTEGER NOT NULL",
                    "rating INTEGER NOT NULL",
                    "body TEXT",
                    "created_at TEXT NOT NULL",
                ],
                "row_count": 340000,
            },
        },
        "slow_query_templates": [
            {
                "name": "orders_by_user",
                "description": "Find all orders for a given user, ordered by date",
                "plan_problem": "FULL SCAN on orders (800 000 rows) — missing index on user_id",
                "sql": (
                    "SELECT o.id, o.status, o.total, o.created_at\n"
                    "FROM orders o\n"
                    "WHERE o.user_id = :uid\n"
                    "ORDER BY o.created_at DESC;"
                ),
                "fix_index": "orders(user_id, created_at)",
                "index_type": "btree",
                "index_name": "idx_orders_user_id_created_at",
                "latency_ms": 8,
            },
            {
                "name": "product_revenue",
                "description": "Total revenue per product for reporting dashboard",
                "plan_problem": "FULL SCAN on order_items (2.4 M rows) + FULL SCAN on products — no index on product_id",
                "sql": (
                    "SELECT p.name, p.category, SUM(oi.quantity * oi.unit_price) AS revenue\n"
                    "FROM order_items oi\n"
                    "JOIN products p ON p.id = oi.product_id\n"
                    "GROUP BY p.id, p.name, p.category\n"
                    "ORDER BY revenue DESC\n"
                    "LIMIT 20;"
                ),
                "fix_index": "order_items(product_id)",
                "index_type": "btree",
                "index_name": "idx_order_items_product_id",
                "latency_ms": 15,
            },
            {
                "name": "pending_orders",
                "description": "Count pending orders per country for ops dashboard",
                "plan_problem": "FULL SCAN on orders (800 000 rows) filtered on status='pending'; partial index would cover only pending rows",
                "sql": (
                    "SELECT u.country, COUNT(o.id) AS pending_count\n"
                    "FROM orders o\n"
                    "JOIN users u ON u.id = o.user_id\n"
                    "WHERE o.status = 'pending'\n"
                    "GROUP BY u.country\n"
                    "ORDER BY pending_count DESC;"
                ),
                "fix_index": "orders(status, user_id)",
                "index_type": "partial",
                "index_name": "idx_orders_pending_user_id",
                "latency_ms": 12,
            },
            {
                "name": "top_reviewers",
                "description": "Users who wrote the most reviews in the last 90 days",
                "plan_problem": "FULL SCAN on reviews (340 000 rows) — missing composite index on (user_id, created_at)",
                "sql": (
                    "SELECT u.name, COUNT(r.id) AS review_count\n"
                    "FROM reviews r\n"
                    "JOIN users u ON u.id = r.user_id\n"
                    "WHERE r.created_at >= date('now', '-90 days')\n"
                    "GROUP BY r.user_id, u.name\n"
                    "ORDER BY review_count DESC\n"
                    "LIMIT 10;"
                ),
                "fix_index": "reviews(user_id, created_at)",
                "index_type": "composite",
                "index_name": "idx_reviews_user_id_created_at",
                "latency_ms": 10,
            },
            {
                "name": "low_stock_products",
                "description": "Products with stock below reorder threshold per category",
                "plan_problem": "FULL SCAN on products (45 000 rows) — covering index on (category, stock, id, name) eliminates heap fetch",
                "sql": (
                    "SELECT category, id, name, stock\n"
                    "FROM products\n"
                    "WHERE stock < :threshold\n"
                    "ORDER BY category, stock;"
                ),
                "fix_index": "products(category, stock, id, name)",
                "index_type": "covering",
                "index_name": "idx_products_category_stock_covering",
                "latency_ms": 5,
            },
            {
                "name": "user_order_summary",
                "description": "Per-user order summary: count, total spend, last order date",
                "plan_problem": "FULL SCAN on orders — missing composite covering index on (user_id, status, total, created_at)",
                "sql": (
                    "SELECT user_id,\n"
                    "       COUNT(*) AS order_count,\n"
                    "       SUM(total) AS total_spend,\n"
                    "       MAX(created_at) AS last_order\n"
                    "FROM orders\n"
                    "GROUP BY user_id;"
                ),
                "fix_index": "orders(user_id, status, total, created_at)",
                "index_type": "covering",
                "index_name": "idx_orders_user_covering",
                "latency_ms": 20,
            },
        ],
        "storage_budget_mb": 512,
    },
    "logistics": {
        "label": "Logistics (shipments / warehouses / carriers / routes)",
        "tables": {
            "warehouses": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "code TEXT NOT NULL UNIQUE",
                    "city TEXT NOT NULL",
                    "country TEXT NOT NULL",
                    "capacity INTEGER NOT NULL",
                ],
                "row_count": 800,
            },
            "carriers": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "name TEXT NOT NULL",
                    "mode TEXT NOT NULL",
                    "active INTEGER NOT NULL DEFAULT 1",
                ],
                "row_count": 150,
            },
            "routes": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "origin_id INTEGER NOT NULL",
                    "destination_id INTEGER NOT NULL",
                    "carrier_id INTEGER NOT NULL",
                    "transit_days INTEGER NOT NULL",
                    "cost_per_kg REAL NOT NULL",
                ],
                "row_count": 18000,
            },
            "shipments": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "route_id INTEGER NOT NULL",
                    "status TEXT NOT NULL",
                    "weight_kg REAL NOT NULL",
                    "dispatched_at TEXT NOT NULL",
                    "arrived_at TEXT",
                    "origin_warehouse_id INTEGER NOT NULL",
                    "destination_warehouse_id INTEGER NOT NULL",
                ],
                "row_count": 950000,
            },
            "shipment_events": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "shipment_id INTEGER NOT NULL",
                    "event_type TEXT NOT NULL",
                    "occurred_at TEXT NOT NULL",
                    "location TEXT",
                ],
                "row_count": 4200000,
            },
        },
        "slow_query_templates": [
            {
                "name": "shipments_by_route",
                "description": "All shipments on a given route ordered by dispatch date",
                "plan_problem": "FULL SCAN on shipments (950 000 rows) — missing index on route_id",
                "sql": (
                    "SELECT id, status, weight_kg, dispatched_at, arrived_at\n"
                    "FROM shipments\n"
                    "WHERE route_id = :rid\n"
                    "ORDER BY dispatched_at DESC;"
                ),
                "fix_index": "shipments(route_id, dispatched_at)",
                "index_type": "btree",
                "index_name": "idx_shipments_route_id_dispatched_at",
                "latency_ms": 8,
            },
            {
                "name": "in_transit_shipments",
                "description": "Count in-transit shipments per carrier",
                "plan_problem": "FULL SCAN on shipments filtered on status='in_transit' — partial index on in-transit rows would shrink scan to ~15%",
                "sql": (
                    "SELECT c.name, COUNT(s.id) AS in_transit\n"
                    "FROM shipments s\n"
                    "JOIN routes r ON r.id = s.route_id\n"
                    "JOIN carriers c ON c.id = r.carrier_id\n"
                    "WHERE s.status = 'in_transit'\n"
                    "GROUP BY c.name\n"
                    "ORDER BY in_transit DESC;"
                ),
                "fix_index": "shipments(status, route_id)",
                "index_type": "partial",
                "index_name": "idx_shipments_in_transit_route_id",
                "latency_ms": 12,
            },
            {
                "name": "recent_events",
                "description": "Latest event per shipment for tracking dashboard",
                "plan_problem": "FULL SCAN on shipment_events (4.2 M rows) — missing composite index on (shipment_id, occurred_at DESC)",
                "sql": (
                    "SELECT shipment_id, event_type, occurred_at, location\n"
                    "FROM shipment_events\n"
                    "WHERE shipment_id = :sid\n"
                    "ORDER BY occurred_at DESC\n"
                    "LIMIT 1;"
                ),
                "fix_index": "shipment_events(shipment_id, occurred_at)",
                "index_type": "composite",
                "index_name": "idx_shipment_events_sid_occurred_at",
                "latency_ms": 3,
            },
            {
                "name": "cheapest_routes",
                "description": "Top-10 cheapest routes between two warehouses",
                "plan_problem": "FULL SCAN on routes (18 000 rows) — missing composite index on (origin_id, destination_id, cost_per_kg)",
                "sql": (
                    "SELECT r.id, c.name, r.transit_days, r.cost_per_kg\n"
                    "FROM routes r\n"
                    "JOIN carriers c ON c.id = r.carrier_id\n"
                    "WHERE r.origin_id = :orig AND r.destination_id = :dest\n"
                    "ORDER BY r.cost_per_kg\n"
                    "LIMIT 10;"
                ),
                "fix_index": "routes(origin_id, destination_id, cost_per_kg)",
                "index_type": "covering",
                "index_name": "idx_routes_origin_dest_cost",
                "latency_ms": 5,
            },
            {
                "name": "warehouse_throughput",
                "description": "Total weight dispatched per warehouse per month",
                "plan_problem": "FULL SCAN on shipments — missing composite index on (origin_warehouse_id, dispatched_at) for GROUP BY range scan",
                "sql": (
                    "SELECT origin_warehouse_id,\n"
                    "       strftime('%Y-%m', dispatched_at) AS month,\n"
                    "       SUM(weight_kg) AS total_weight\n"
                    "FROM shipments\n"
                    "GROUP BY origin_warehouse_id, month\n"
                    "ORDER BY origin_warehouse_id, month;"
                ),
                "fix_index": "shipments(origin_warehouse_id, dispatched_at)",
                "index_type": "composite",
                "index_name": "idx_shipments_origin_wh_dispatched",
                "latency_ms": 18,
            },
            {
                "name": "delayed_shipments",
                "description": "Shipments that arrived later than expected transit time",
                "plan_problem": "FULL SCAN on shipments joined to routes — missing index on destination_warehouse_id",
                "sql": (
                    "SELECT s.id, s.dispatched_at, s.arrived_at, r.transit_days\n"
                    "FROM shipments s\n"
                    "JOIN routes r ON r.id = s.route_id\n"
                    "WHERE s.arrived_at IS NOT NULL\n"
                    "  AND julianday(s.arrived_at) - julianday(s.dispatched_at) > r.transit_days\n"
                    "ORDER BY s.arrived_at DESC;"
                ),
                "fix_index": "shipments(destination_warehouse_id, arrived_at)",
                "index_type": "btree",
                "index_name": "idx_shipments_dest_wh_arrived_at",
                "latency_ms": 15,
            },
            {
                "name": "carrier_reliability",
                "description": "On-time delivery rate per active carrier",
                "plan_problem": "FULL SCAN on carriers + nested sub-scans on shipments — missing covering index on routes(carrier_id)",
                "sql": (
                    "SELECT c.name,\n"
                    "       COUNT(s.id) AS total,\n"
                    "       SUM(CASE WHEN julianday(s.arrived_at) - julianday(s.dispatched_at) <= r.transit_days THEN 1 ELSE 0 END) AS on_time\n"
                    "FROM carriers c\n"
                    "JOIN routes r ON r.carrier_id = c.id\n"
                    "JOIN shipments s ON s.route_id = r.id\n"
                    "WHERE c.active = 1 AND s.arrived_at IS NOT NULL\n"
                    "GROUP BY c.id, c.name;"
                ),
                "fix_index": "routes(carrier_id, id)",
                "index_type": "covering",
                "index_name": "idx_routes_carrier_id_covering",
                "latency_ms": 25,
            },
        ],
        "storage_budget_mb": 768,
    },
    "hr_payroll": {
        "label": "HR / Payroll (employees / payroll / departments / timesheets)",
        "tables": {
            "departments": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "name TEXT NOT NULL",
                    "cost_center TEXT NOT NULL",
                    "manager_id INTEGER",
                ],
                "row_count": 120,
            },
            "employees": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "department_id INTEGER NOT NULL",
                    "name TEXT NOT NULL",
                    "email TEXT NOT NULL UNIQUE",
                    "job_title TEXT NOT NULL",
                    "hire_date TEXT NOT NULL",
                    "status TEXT NOT NULL DEFAULT 'active'",
                ],
                "row_count": 28000,
            },
            "payroll": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "employee_id INTEGER NOT NULL",
                    "period TEXT NOT NULL",
                    "gross REAL NOT NULL",
                    "tax REAL NOT NULL",
                    "net REAL NOT NULL",
                    "paid_at TEXT NOT NULL",
                ],
                "row_count": 672000,
            },
            "timesheets": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "employee_id INTEGER NOT NULL",
                    "work_date TEXT NOT NULL",
                    "hours REAL NOT NULL",
                    "project_code TEXT NOT NULL",
                    "approved INTEGER NOT NULL DEFAULT 0",
                ],
                "row_count": 1800000,
            },
            "leave_requests": {
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "employee_id INTEGER NOT NULL",
                    "leave_type TEXT NOT NULL",
                    "start_date TEXT NOT NULL",
                    "end_date TEXT NOT NULL",
                    "status TEXT NOT NULL DEFAULT 'pending'",
                ],
                "row_count": 95000,
            },
        },
        "slow_query_templates": [
            {
                "name": "payroll_by_employee",
                "description": "Full payroll history for a single employee",
                "plan_problem": "FULL SCAN on payroll (672 000 rows) — missing index on employee_id",
                "sql": (
                    "SELECT period, gross, tax, net, paid_at\n"
                    "FROM payroll\n"
                    "WHERE employee_id = :eid\n"
                    "ORDER BY paid_at DESC;"
                ),
                "fix_index": "payroll(employee_id, paid_at)",
                "index_type": "btree",
                "index_name": "idx_payroll_employee_id_paid_at",
                "latency_ms": 6,
            },
            {
                "name": "dept_headcount",
                "description": "Active headcount and average gross pay per department",
                "plan_problem": "FULL SCAN on employees + FULL SCAN on payroll — missing composite index on (department_id, status)",
                "sql": (
                    "SELECT d.name, COUNT(e.id) AS headcount,\n"
                    "       AVG(p.gross) AS avg_gross\n"
                    "FROM departments d\n"
                    "JOIN employees e ON e.department_id = d.id\n"
                    "JOIN payroll p ON p.employee_id = e.id\n"
                    "WHERE e.status = 'active'\n"
                    "GROUP BY d.id, d.name\n"
                    "ORDER BY headcount DESC;"
                ),
                "fix_index": "employees(department_id, status)",
                "index_type": "composite",
                "index_name": "idx_employees_dept_id_status",
                "latency_ms": 14,
            },
            {
                "name": "unapproved_timesheets",
                "description": "Employees with unapproved timesheets older than 7 days",
                "plan_problem": "FULL SCAN on timesheets (1.8 M rows) on approved=0 — partial index on unapproved rows only",
                "sql": (
                    "SELECT e.name, e.email, t.work_date, t.hours, t.project_code\n"
                    "FROM timesheets t\n"
                    "JOIN employees e ON e.id = t.employee_id\n"
                    "WHERE t.approved = 0\n"
                    "  AND t.work_date < date('now', '-7 days')\n"
                    "ORDER BY t.work_date;"
                ),
                "fix_index": "timesheets(approved, work_date, employee_id)",
                "index_type": "partial",
                "index_name": "idx_timesheets_unapproved_work_date",
                "latency_ms": 10,
            },
            {
                "name": "monthly_payroll_cost",
                "description": "Total gross payroll cost per department per month",
                "plan_problem": "FULL SCAN on payroll — missing composite covering index on (period, employee_id, gross)",
                "sql": (
                    "SELECT d.name, p.period, SUM(p.gross) AS dept_gross\n"
                    "FROM payroll p\n"
                    "JOIN employees e ON e.id = p.employee_id\n"
                    "JOIN departments d ON d.id = e.department_id\n"
                    "GROUP BY d.id, d.name, p.period\n"
                    "ORDER BY p.period DESC, dept_gross DESC;"
                ),
                "fix_index": "payroll(period, employee_id, gross)",
                "index_type": "covering",
                "index_name": "idx_payroll_period_employee_gross",
                "latency_ms": 20,
            },
            {
                "name": "pending_leave",
                "description": "Pending leave requests ordered by start date per department",
                "plan_problem": "FULL SCAN on leave_requests (95 000 rows) on status='pending' — partial index would shrink to ~8%",
                "sql": (
                    "SELECT e.name, d.name AS dept, lr.leave_type, lr.start_date, lr.end_date\n"
                    "FROM leave_requests lr\n"
                    "JOIN employees e ON e.id = lr.employee_id\n"
                    "JOIN departments d ON d.id = e.department_id\n"
                    "WHERE lr.status = 'pending'\n"
                    "ORDER BY lr.start_date;"
                ),
                "fix_index": "leave_requests(status, start_date, employee_id)",
                "index_type": "partial",
                "index_name": "idx_leave_requests_pending_start",
                "latency_ms": 8,
            },
            {
                "name": "hours_by_project",
                "description": "Total approved hours per project code in a date range",
                "plan_problem": "FULL SCAN on timesheets — missing composite index on (project_code, approved, work_date)",
                "sql": (
                    "SELECT project_code, SUM(hours) AS total_hours\n"
                    "FROM timesheets\n"
                    "WHERE approved = 1\n"
                    "  AND work_date BETWEEN :start AND :end\n"
                    "GROUP BY project_code\n"
                    "ORDER BY total_hours DESC;"
                ),
                "fix_index": "timesheets(project_code, approved, work_date, hours)",
                "index_type": "covering",
                "index_name": "idx_timesheets_project_approved_date",
                "latency_ms": 12,
            },
        ],
        "storage_budget_mb": 384,
    },
}

# Domain key order so seed -> domain mapping is deterministic
_DOMAIN_KEYS = ["ecommerce", "logistics", "hr_payroll"]

# Approximate index size estimates in MB (used to check storage budget)
INDEX_SIZE_ESTIMATES: dict[str, float] = {
    "btree": 40.0,
    "partial": 12.0,
    "composite": 55.0,
    "covering": 80.0,
}


class Generator(TaskGenerator):
    task_id = "SQL2_query_optimize"
    domain = "data"
    difficulty = "hard"
    languages = ["sql", "python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # ── Pick domain deterministically by seed ──────────────────────────
        domain_key = _DOMAIN_KEYS[seed % len(_DOMAIN_KEYS)]
        domain = DOMAINS[domain_key]

        # ── Pick 5-8 queries from the template pool ────────────────────────
        all_templates = list(domain["slow_query_templates"])
        rng.shuffle(all_templates)
        query_count = rng.randint(5, min(8, len(all_templates)))
        selected = all_templates[:query_count]

        # ── Vary latency targets slightly per seed ─────────────────────────
        lat_rng = SeededRandom(seed + 7)
        queries_meta: list[dict] = []
        for i, tpl in enumerate(selected):
            jitter = lat_rng.randint(-2, 4)
            target_ms = max(3, tpl["latency_ms"] + jitter)
            queries_meta.append({
                **tpl,
                "query_num": i + 1,
                "target_ms": target_ms,
            })

        # ── Storage budget (vary slightly per seed) ────────────────────────
        base_budget: int = domain["storage_budget_mb"]
        budget_jitter = rng.randint(-32, 48)
        storage_budget_mb: int = base_budget + budget_jitter

        # ── Compute expected total index size ──────────────────────────────
        total_index_size = sum(
            INDEX_SIZE_ESTIMATES.get(qm["index_type"], 40.0)
            for qm in queries_meta
        )
        # Ensure budget is achievable but tight
        if total_index_size >= storage_budget_mb:
            storage_budget_mb = int(total_index_size * 1.15) + 10

        # ── Build expected ground truth ────────────────────────────────────
        expected = self._build_expected(
            seed, domain_key, domain, queries_meta, storage_budget_mb, total_index_size
        )

        # ── Generate workspace files ───────────────────────────────────────
        workspace_files = self._generate_workspace(domain_key, domain, queries_meta)

        spec_md = self._generate_spec(
            domain_key, domain, queries_meta, storage_budget_mb, total_index_size
        )
        brief_md = self._generate_brief(domain_key, domain)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Expected ground-truth ──────────────────────────────────────────────

    def _build_expected(
        self,
        seed: int,
        domain_key: str,
        domain: dict,
        queries_meta: list[dict],
        storage_budget_mb: int,
        total_index_size: float,
    ) -> dict:
        required_indexes: list[dict] = []
        latency_targets: dict[str, int] = {}

        for qm in queries_meta:
            required_indexes.append({
                "name": qm["index_name"],
                "columns": qm["fix_index"],
                "type": qm["index_type"],
                "query": qm["name"],
            })
            latency_targets[qm["name"]] = qm["target_ms"]

        # Naming convention: all index names must start with "idx_"
        index_naming_convention = "idx_"

        return {
            "seed": seed,
            "domain": domain_key,
            "query_count": len(queries_meta),
            "required_indexes": required_indexes,
            "index_naming_convention": index_naming_convention,
            "latency_targets_ms": latency_targets,
            "storage_budget_mb": storage_budget_mb,
            "estimated_total_index_size_mb": round(total_index_size, 1),
            "index_types_required": list({qm["index_type"] for qm in queries_meta}),
            "query_names": [qm["name"] for qm in queries_meta],
        }

    # ── Workspace file generators ──────────────────────────────────────────

    def _generate_workspace(
        self,
        domain_key: str,
        domain: dict,
        queries_meta: list[dict],
    ) -> dict[str, str]:
        schema_sql = self._generate_schema_sql(domain_key, domain)
        queries_sql = self._generate_queries_sql(domain_key, queries_meta)
        optimizer_py = self._generate_optimizer_py(domain_key, queries_meta)
        return {
            "schema.sql": schema_sql,
            "queries.sql": queries_sql,
            "optimizer.py": optimizer_py,
        }

    def _generate_schema_sql(self, domain_key: str, domain: dict) -> str:
        label = domain["label"]
        lines: list[str] = [
            f"-- Schema for SQL2_query_optimize ({label})",
            "-- NOTE: No indexes are defined. The optimizer must add them.",
            "",
        ]
        for table_name, tdef in domain["tables"].items():
            col_defs = ",\n    ".join(tdef["columns"])
            approx_rows = tdef["row_count"]
            lines.append(f"-- Approximate row count: {approx_rows:,}")
            lines.append(f"CREATE TABLE {table_name} (")
            lines.append(f"    {col_defs}")
            lines.append(");")
            lines.append("")
        return "\n".join(lines)

    def _generate_queries_sql(self, domain_key: str, queries_meta: list[dict]) -> str:
        lines: list[str] = [
            f"-- Slow queries for SQL2_query_optimize ({domain_key})",
            "-- Each query is annotated with its observed query plan problem.",
            "-- Your task: add indexes in schema.sql so all queries meet their latency targets.",
            "",
        ]
        for qm in queries_meta:
            lines.append(f"-- ─────────────────────────────────────────────────────────────────")
            lines.append(f"-- Query: {qm['name']}")
            lines.append(f"-- Purpose: {qm['description']}")
            lines.append(f"-- Observed plan: {qm['plan_problem']}")
            lines.append(f"-- Latency target: < {qm['target_ms']} ms")
            lines.append(f"-- ─────────────────────────────────────────────────────────────────")
            lines.append(qm["sql"])
            lines.append("")
        return "\n".join(lines)

    def _generate_optimizer_py(self, domain_key: str, queries_meta: list[dict]) -> str:
        query_names = [qm["name"] for qm in queries_meta]
        query_list_repr = "\n    ".join(f'"{n}",' for n in query_names)
        return f'''"""
SQL2 Query Optimizer skeleton.

Your job: populate `get_indexes()` so that `apply_optimizations()` adds
the correct CREATE INDEX statements to schema.sql.

Rules:
  - All index names MUST start with "idx_"
  - Index type comments are required: -- type: btree | partial | composite | covering
  - Total estimated index storage must stay under the storage budget
    (see STORAGE_BUDGET_MB).
  - Each query in SLOW_QUERIES must have a corresponding index entry.
"""
import re
import sys

# Storage budget in MB — do NOT exceed this with your indexes.
# Approximate index sizes: btree ~40MB, partial ~12MB, composite ~55MB, covering ~80MB
STORAGE_BUDGET_MB = None  # TODO: fill in from spec

SLOW_QUERIES = [
    {query_list_repr}
]


def get_indexes() -> list[dict]:
    """
    Return a list of index definitions to apply.

    Each entry must have:
      "name"    : str  -- index name, must start with "idx_"
      "table"   : str  -- table to index
      "columns" : list -- ordered list of column names
      "type"    : str  -- one of: btree, partial, composite, covering
      "query"   : str  -- which slow query this index targets
      "partial_where" : str | None  -- WHERE clause for partial indexes

    Example:
      {{
        "name": "idx_orders_user_id_created_at",
        "table": "orders",
        "columns": ["user_id", "created_at"],
        "type": "btree",
        "query": "orders_by_user",
        "partial_where": None,
      }}
    """
    # TODO: implement — add one entry per slow query
    return []


def validate_budget(indexes: list[dict]) -> bool:
    """Check that total estimated index size stays within budget."""
    size_estimates = {{
        "btree": 40.0,
        "partial": 12.0,
        "composite": 55.0,
        "covering": 80.0,
    }}
    total = sum(size_estimates.get(ix["type"], 40.0) for ix in indexes)
    print(f"Estimated index storage: {{total:.1f}} MB (budget: {{STORAGE_BUDGET_MB}} MB)")
    if STORAGE_BUDGET_MB is not None and total > STORAGE_BUDGET_MB:
        print(f"ERROR: Index storage {{total:.1f}} MB exceeds budget {{STORAGE_BUDGET_MB}} MB")
        return False
    return True


def apply_optimizations(schema_path: str = "schema.sql") -> None:
    """Read schema.sql, append CREATE INDEX statements, write back."""
    with open(schema_path) as f:
        content = f.read()

    indexes = get_indexes()
    if not indexes:
        print("No indexes defined in get_indexes(). Nothing to apply.")
        sys.exit(1)

    if not validate_budget(indexes):
        sys.exit(1)

    index_ddl_lines = ["", "-- === Optimized Indexes (generated by optimizer.py) ==="]
    for ix in indexes:
        name = ix["name"]
        table = ix["table"]
        cols = ", ".join(ix["columns"])
        ix_type = ix.get("type", "btree")
        query = ix.get("query", "unknown")
        where = ix.get("partial_where")

        index_ddl_lines.append(f"-- type: {{ix_type}}  target_query: {{query}}")
        if where:
            index_ddl_lines.append(
                f"CREATE INDEX IF NOT EXISTS {{name}} ON {{table}} ({{cols}}) WHERE {{where}};"
            )
        else:
            index_ddl_lines.append(
                f"CREATE INDEX IF NOT EXISTS {{name}} ON {{table}} ({{cols}});"
            )

    # Remove any previously generated block
    marker = "-- === Optimized Indexes"
    if marker in content:
        content = content[:content.index(marker)]

    updated = content.rstrip() + "\\n" + "\\n".join(index_ddl_lines) + "\\n"
    with open(schema_path, "w") as f:
        f.write(updated)

    print(f"Applied {{len(indexes)}} index(es) to {{schema_path}}")
    print("Queries targeted:", [ix["query"] for ix in indexes])


if __name__ == "__main__":
    schema = sys.argv[1] if len(sys.argv) > 1 else "schema.sql"
    apply_optimizations(schema)
'''

    # ── Spec and brief generators ──────────────────────────────────────────

    def _generate_spec(
        self,
        domain_key: str,
        domain: dict,
        queries_meta: list[dict],
        storage_budget_mb: int,
        total_index_size: float,
    ) -> str:
        label = domain["label"]

        # Build schema table summary
        schema_lines: list[str] = []
        for tname, tdef in domain["tables"].items():
            schema_lines.append(f"**{tname}** (~{tdef['row_count']:,} rows)")
            col_str = ", ".join(
                c.split()[0] for c in tdef["columns"]
            )
            schema_lines.append(f"  columns: {col_str}")
        schema_summary = "\n".join(schema_lines)

        # Build per-query plan table
        query_rows: list[str] = []
        for qm in queries_meta:
            query_rows.append(
                f"| `{qm['name']}` | {qm['description']} "
                f"| {qm['plan_problem']} "
                f"| < {qm['target_ms']} ms "
                f"| {qm['index_type']} |"
            )
        query_table = "\n".join(query_rows)

        # Build required index table
        index_rows: list[str] = []
        for qm in queries_meta:
            index_rows.append(
                f"| `{qm['index_name']}` | `{qm['fix_index']}` "
                f"| {qm['index_type']} | `{qm['name']}` |"
            )
        index_table = "\n".join(index_rows)

        # Storage budget breakdown
        budget_rows: list[str] = []
        running = 0.0
        for qm in queries_meta:
            sz = INDEX_SIZE_ESTIMATES.get(qm["index_type"], 40.0)
            running += sz
            budget_rows.append(
                f"| `{qm['index_name']}` | {qm['index_type']} | ~{sz:.0f} MB |"
            )
        budget_rows.append(f"| **TOTAL** | | **~{running:.0f} MB** |")
        budget_table = "\n".join(budget_rows)

        return f"""# SQL2: Query Optimize — Planner Specification

## Context

Domain: **{label}**

The production database is exhibiting severe query latency. A profiling session
identified {len(queries_meta)} slow queries — each is doing a full table scan where
a targeted index would reduce execution time by 10-100x.

Your team must add the correct indexes. This task has **two hard constraints**:

1. **Latency constraint**: every query listed below must meet its ms target after
   the index is applied.
2. **Storage constraint**: the total estimated size of all new indexes must stay
   under **{storage_budget_mb} MB**. (Current estimate: ~{running:.0f} MB — within budget.)

## Schema Summary

```
{schema_summary}
```

Full DDL is in `schema.sql`. **There are zero indexes defined today.**

## Slow Query Analysis

| Query | Purpose | Observed Plan Problem | Latency Target | Required Index Type |
|-------|---------|----------------------|----------------|---------------------|
{query_table}

## Required Indexes (Exact Specification)

The Executor MUST create these indexes with the exact names and column orders shown.
Index names MUST use the convention `idx_<table>_<columns>`.

| Index Name | Columns | Type | Fixes Query |
|------------|---------|------|-------------|
{index_table}

### Index Type Definitions

- **btree** — standard B-tree index; use for equality and range lookups on moderate-cardinality columns.
- **partial** — filtered index (`WHERE` clause); use when queries always filter on a low-cardinality status column, keeping index size small.
- **composite** — multi-column B-tree; column ORDER matters — put equality columns first, then range/sort columns.
- **covering** — composite index that includes ALL columns referenced in the query (SELECT + WHERE + ORDER BY), eliminating the heap fetch.

## Storage Budget Breakdown

| Index Name | Type | Estimated Size |
|------------|------|----------------|
{budget_table}

**Hard limit: {storage_budget_mb} MB total.** Indexes exceeding the budget must be
replaced with partial indexes where possible.

## Deliverables

1. `optimizer.py` — implement `get_indexes()` returning the full list above.
2. `schema.sql` — after running `python3 optimizer.py`, the file must contain
   all required `CREATE INDEX` statements.
3. Naming convention: every index name must start with `idx_`.
4. Storage validation: `validate_budget()` in `optimizer.py` must print
   `"BUDGET_OK"` (it currently prints an error if over budget).

## Verification

```bash
python3 optimizer.py schema.sql
# Expected output ends with: Applied {len(queries_meta)} index(es) to schema.sql
grep -c "CREATE INDEX" schema.sql
# Expected: {len(queries_meta)}
```
"""

    def _generate_brief(self, domain_key: str, domain: dict) -> str:
        label = domain["label"]
        table_names = list(domain["tables"].keys())
        tables_str = ", ".join(f"`{t}`" for t in table_names)
        return f"""# SQL2: Query Optimize (Executor Brief)

## Situation

The {label} database is slow. Several queries are timing out in production.

## Your Task

Add indexes to `schema.sql` so the slow queries in `queries.sql` run faster.

## Files

- `schema.sql` — database schema (no indexes yet)
- `queries.sql` — {len(domain['slow_query_templates'])} slow queries (read the comments for hints)
- `optimizer.py` — skeleton; implement `get_indexes()` and run it

## Tables

{tables_str}

## How to Apply

```bash
python3 optimizer.py schema.sql
```

This appends `CREATE INDEX` statements to `schema.sql`.

## Done When

- `optimizer.py` exits 0
- `schema.sql` contains the correct `CREATE INDEX` statements
- All index names start with `idx_`
"""
