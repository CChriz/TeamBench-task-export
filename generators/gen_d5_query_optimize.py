"""
Parameterized generator for D5: Query Optimization.

TNI Pattern A,C (Hidden Constraints + Multi-Criteria):
  - Spec has: complete query execution plan analysis (which queries do full table
    scans, which joins are inefficient, which indexes are missing), target latency
    per query (e.g. query_1 < 10ms, query_2 < 50ms), and scoring rubric
    (correctness 50%, performance 30%, readability 20%).
  - Brief says: "Several database queries are too slow. Optimize them."
  - Without the Planner's full analysis the Executor optimizes the obvious ones
    but misses N+1 patterns, missing composite indexes, and inefficient subqueries.

Each seed produces:
  - Different data domain: users/orders, products/reviews, employees/departments
  - Different query count: 4-6 queries
  - Different optimization types seeded deterministically:
      add_index, rewrite_join, eliminate_n_plus_1, use_aggregation, covering_index
  - workspace/database.py  — creates SQLite DB with sample data (no indexes!)
  - workspace/queries.py   — slow queries (full scans, N+1, bad subqueries)
  - workspace/tests/test_queries.py — correctness tests
  - reports/expected.json  — ground-truth for grading (never seen by agents)
"""
from __future__ import annotations

import json
from typing import Any

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool, ValuePool

# ── Domain definitions ────────────────────────────────────────────────────────

DOMAINS: dict[str, dict] = {
    "users_orders": {
        "label": "e-commerce (users / orders)",
        "tables": ["users", "orders", "order_items", "products"],
        "row_counts": {"users": 500, "products": 200, "orders": 2000, "order_items": 5000},
        "description": "An e-commerce platform with users, products, orders and line-items.",
    },
    "products_reviews": {
        "label": "review platform (products / reviews)",
        "tables": ["products", "reviews", "categories", "users"],
        "row_counts": {"users": 300, "products": 400, "categories": 20, "reviews": 3000},
        "description": "A product-review platform with products, categories, users and reviews.",
    },
    "employees_departments": {
        "label": "HR system (employees / departments)",
        "tables": ["employees", "departments", "projects", "assignments"],
        "row_counts": {"departments": 30, "employees": 500, "projects": 100, "assignments": 800},
        "description": "An HR system with employees, departments, projects and assignments.",
    },
}

# Optimization type catalog — each entry describes one optimization challenge
OPT_TYPES = [
    "add_index",           # Missing index causes full table scan
    "rewrite_join",        # Inefficient nested-loop join → hash/indexed join
    "eliminate_n_plus_1",  # N+1 pattern → single aggregated query
    "use_aggregation",     # Subquery per row → GROUP BY aggregation
    "covering_index",      # Non-covering index → composite covering index
]

# Latency targets in milliseconds per optimization type
LATENCY_TARGETS_MS: dict[str, int] = {
    "add_index":           10,
    "rewrite_join":        50,
    "eliminate_n_plus_1":  20,
    "use_aggregation":     30,
    "covering_index":      15,
}


class Generator(TaskGenerator):
    task_id = "D5_query_optimize"
    domain = "data"
    difficulty = "hard"
    languages = ["python", "sql"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=40)

        # ── Pick domain ────────────────────────────────────────────────────
        domain_key = rng.choice(list(DOMAINS.keys()))
        domain = DOMAINS[domain_key]

        # ── Pick query count (4 to min(6, num opt types)) ─────────────────
        query_count = rng.randint(4, min(6, len(OPT_TYPES)))

        # ── Pick optimization types (no duplicates, order matters) ─────────
        opt_pool = list(OPT_TYPES)
        rng.shuffle(opt_pool)
        selected_opts = opt_pool[:query_count]

        # ── Generate seed-specific data values ─────────────────────────────
        val_rng = SeededRandom(seed + 10)
        price_rng = SeededRandom(seed + 20)

        # Build per-query metadata
        queries_meta = []
        for i, opt_type in enumerate(selected_opts):
            q_num = i + 1
            target_ms = LATENCY_TARGETS_MS[opt_type]
            # Vary target slightly per seed to make cross-seed detection easier
            jitter = val_rng.randint(-2, 5)
            target_ms = max(5, target_ms + jitter)
            queries_meta.append({
                "num": q_num,
                "opt_type": opt_type,
                "target_ms": target_ms,
                "name": f"query_{q_num}",
            })

        # ── Generate expected ground truth ─────────────────────────────────
        expected = self._build_expected(
            seed, domain_key, domain, query_count, queries_meta, rng, val_rng, price_rng, names
        )

        # ── Generate workspace files ───────────────────────────────────────
        workspace_files = self._generate_workspace(
            seed, domain_key, domain, queries_meta, expected, rng
        )

        spec_md = self._generate_spec(domain_key, domain, queries_meta, expected)
        brief_md = self._generate_brief(domain_key)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Expected ground-truth builder
    # ──────────────────────────────────────────────────────────────────────────

    def _build_expected(
        self,
        seed: int,
        domain_key: str,
        domain: dict,
        query_count: int,
        queries_meta: list[dict],
        rng: SeededRandom,
        val_rng: SeededRandom,
        price_rng: SeededRandom,
        names: NamePool,
    ) -> dict:
        """Build the expected.json ground truth (never shown to agents)."""
        expected: dict[str, Any] = {
            "domain": domain_key,
            "query_count": query_count,
            "queries": {},
            "required_indexes": [],
            "forbidden_patterns": [],
        }

        for qm in queries_meta:
            opt = qm["opt_type"]
            q_name = qm["name"]
            expected["queries"][q_name] = {
                "opt_type": opt,
                "target_ms": qm["target_ms"],
            }

            if opt == "add_index":
                # Expect an index on a foreign-key or filter column
                if domain_key == "users_orders":
                    expected["required_indexes"].append("orders.user_id")
                elif domain_key == "products_reviews":
                    expected["required_indexes"].append("reviews.product_id")
                else:
                    expected["required_indexes"].append("assignments.employee_id")

            elif opt == "rewrite_join":
                # Expect index on join column
                if domain_key == "users_orders":
                    expected["required_indexes"].append("order_items.order_id")
                elif domain_key == "products_reviews":
                    expected["required_indexes"].append("reviews.user_id")
                else:
                    expected["required_indexes"].append("assignments.project_id")

            elif opt == "eliminate_n_plus_1":
                expected["forbidden_patterns"].append("n_plus_1")

            elif opt == "use_aggregation":
                expected["forbidden_patterns"].append("per_row_subquery")

            elif opt == "covering_index":
                if domain_key == "users_orders":
                    expected["required_indexes"].append("orders(user_id,status,total)")
                elif domain_key == "products_reviews":
                    expected["required_indexes"].append("reviews(product_id,rating)")
                else:
                    expected["required_indexes"].append("employees(department_id,salary)")

        # Deduplicate
        expected["required_indexes"] = list(dict.fromkeys(expected["required_indexes"]))
        expected["forbidden_patterns"] = list(dict.fromkeys(expected["forbidden_patterns"]))

        return expected

    # ──────────────────────────────────────────────────────────────────────────
    # Workspace file generators
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_workspace(
        self,
        seed: int,
        domain_key: str,
        domain: dict,
        queries_meta: list[dict],
        expected: dict,
        rng: SeededRandom,
    ) -> dict[str, str]:
        database_py = self._gen_database_py(seed, domain_key, domain, rng)
        queries_py = self._gen_queries_py(domain_key, queries_meta)
        test_py = self._gen_test_py(domain_key, queries_meta)

        return {
            "database.py": database_py,
            "queries.py": queries_py,
            "tests/__init__.py": "",
            "tests/test_queries.py": test_py,
        }

    def _gen_database_py(
        self,
        seed: int,
        domain_key: str,
        domain: dict,
        rng: SeededRandom,
    ) -> str:
        row_counts = domain["row_counts"]

        if domain_key == "users_orders":
            return self._gen_db_users_orders(seed, row_counts)
        elif domain_key == "products_reviews":
            return self._gen_db_products_reviews(seed, row_counts)
        else:
            return self._gen_db_employees_departments(seed, row_counts)

    # ── users_orders DB ───────────────────────────────────────────────────────

    def _gen_db_users_orders(self, seed: int, row_counts: dict) -> str:
        n_users = row_counts["users"]
        n_products = row_counts["products"]
        n_orders = row_counts["orders"]
        n_items = row_counts["order_items"]
        template = (
            '"""\n'
            'Create and populate store.db for D5_query_optimize (users/orders domain).\n'
            '\n'
            'Intentionally omits indexes so the slow queries are genuinely slow on large data.\n'
            'Run this file directly to (re)create the database.\n'
            '"""\n'
            'import sqlite3\n'
            'import random\n'
            'import os\n'
            '\n'
            'DB_PATH = "store.db"\n'
            'SEED = __SEED__\n'
            'N_USERS = __N_USERS__\n'
            'N_PRODUCTS = __N_PRODUCTS__\n'
            'N_ORDERS = __N_ORDERS__\n'
            'N_ITEMS = __N_ITEMS__\n'
            '\n'
            '\n'
            'def create_tables(cur: sqlite3.Cursor) -> None:\n'
            '    cur.executescript("""\n'
            '        CREATE TABLE IF NOT EXISTS users (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            name        TEXT NOT NULL,\n'
            '            email       TEXT NOT NULL,\n'
            '            country     TEXT NOT NULL,\n'
            '            created_at  TEXT NOT NULL\n'
            '        );\n'
            '\n'
            '        CREATE TABLE IF NOT EXISTS products (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            name        TEXT NOT NULL,\n'
            '            category    TEXT NOT NULL,\n'
            '            price       REAL NOT NULL\n'
            '        );\n'
            '\n'
            '        -- NOTE: No index on orders.user_id (intentional - causes full scan)\n'
            '        CREATE TABLE IF NOT EXISTS orders (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            user_id     INTEGER NOT NULL,\n'
            '            status      TEXT NOT NULL,\n'
            '            total       REAL NOT NULL,\n'
            '            created_at  TEXT NOT NULL\n'
            '        );\n'
            '\n'
            '        -- NOTE: No index on order_items.order_id (intentional - causes slow join)\n'
            '        CREATE TABLE IF NOT EXISTS order_items (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            order_id    INTEGER NOT NULL,\n'
            '            product_id  INTEGER NOT NULL,\n'
            '            quantity    INTEGER NOT NULL,\n'
            '            unit_price  REAL NOT NULL\n'
            '        );\n'
            '    """)\n'
            '\n'
            '\n'
            'def populate(cur: sqlite3.Cursor) -> None:\n'
            '    rng = random.Random(SEED)\n'
            '\n'
            '    countries = ["US", "UK", "DE", "FR", "CA", "AU", "JP", "BR", "IN", "MX"]\n'
            '    statuses = ["pending", "shipped", "delivered", "cancelled"]\n'
            '    categories = ["electronics", "clothing", "books", "home", "sports", "toys"]\n'
            '\n'
            '    # Users\n'
            '    users = []\n'
            '    for i in range(1, N_USERS + 1):\n'
            '        year = rng.randint(2018, 2023)\n'
            '        month = rng.randint(1, 12)\n'
            '        day = rng.randint(1, 28)\n'
            '        users.append((\n'
            '            i,\n'
            '            f"User_{i:04d}",\n'
            '            f"user{i}@example.com",\n'
            '            rng.choice(countries),\n'
            '            f"{year}-{month:02d}-{day:02d}",\n'
            '        ))\n'
            '    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?)", users)\n'
            '\n'
            '    # Products\n'
            '    products = []\n'
            '    for i in range(1, N_PRODUCTS + 1):\n'
            '        price = round(rng.uniform(5.0, 500.0), 2)\n'
            '        products.append((i, f"Product_{i:03d}", rng.choice(categories), price))\n'
            '    cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)\n'
            '\n'
            '    # Orders\n'
            '    orders = []\n'
            '    for i in range(1, N_ORDERS + 1):\n'
            '        uid = rng.randint(1, N_USERS)\n'
            '        total = round(rng.uniform(10.0, 1000.0), 2)\n'
            '        year = rng.randint(2020, 2024)\n'
            '        month = rng.randint(1, 12)\n'
            '        day = rng.randint(1, 28)\n'
            '        orders.append((\n'
            '            i, uid, rng.choice(statuses), total,\n'
            '            f"{year}-{month:02d}-{day:02d}"\n'
            '        ))\n'
            '    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", orders)\n'
            '\n'
            '    # Order items\n'
            '    items = []\n'
            '    for i in range(1, N_ITEMS + 1):\n'
            '        oid = rng.randint(1, N_ORDERS)\n'
            '        pid = rng.randint(1, N_PRODUCTS)\n'
            '        qty = rng.randint(1, 5)\n'
            '        price = round(rng.uniform(5.0, 500.0), 2)\n'
            '        items.append((i, oid, pid, qty, price))\n'
            '    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)\n'
            '\n'
            '\n'
            'def setup(db_path: str = DB_PATH) -> None:\n'
            '    if os.path.exists(db_path):\n'
            '        os.remove(db_path)\n'
            '    conn = sqlite3.connect(db_path)\n'
            '    cur = conn.cursor()\n'
            '    create_tables(cur)\n'
            '    populate(cur)\n'
            '    conn.commit()\n'
            '    conn.close()\n'
            '    print(f"Database created: {db_path}")\n'
            '    print(f"  users: {N_USERS}, products: {N_PRODUCTS}, orders: {N_ORDERS}, items: {N_ITEMS}")\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    setup()\n'
        )
        return (template
                .replace("__SEED__", str(seed))
                .replace("__N_USERS__", str(n_users))
                .replace("__N_PRODUCTS__", str(n_products))
                .replace("__N_ORDERS__", str(n_orders))
                .replace("__N_ITEMS__", str(n_items)))

    # ── products_reviews DB ───────────────────────────────────────────────────

    def _gen_db_products_reviews(self, seed: int, row_counts: dict) -> str:
        n_users = row_counts["users"]
        n_products = row_counts["products"]
        n_categories = row_counts["categories"]
        n_reviews = row_counts["reviews"]
        template = (
            '"""\n'
            'Create and populate catalog.db for D5_query_optimize (products/reviews domain).\n'
            '\n'
            'Intentionally omits indexes so queries scan full tables.\n'
            '"""\n'
            'import sqlite3\n'
            'import random\n'
            'import os\n'
            '\n'
            'DB_PATH = "catalog.db"\n'
            'SEED = __SEED__\n'
            'N_USERS = __N_USERS__\n'
            'N_PRODUCTS = __N_PRODUCTS__\n'
            'N_CATEGORIES = __N_CATEGORIES__\n'
            'N_REVIEWS = __N_REVIEWS__\n'
            '\n'
            '\n'
            'def create_tables(cur: sqlite3.Cursor) -> None:\n'
            '    cur.executescript("""\n'
            '        CREATE TABLE IF NOT EXISTS categories (\n'
            '            id    INTEGER PRIMARY KEY,\n'
            '            name  TEXT NOT NULL\n'
            '        );\n'
            '\n'
            '        CREATE TABLE IF NOT EXISTS users (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            name        TEXT NOT NULL,\n'
            '            email       TEXT NOT NULL\n'
            '        );\n'
            '\n'
            '        -- NOTE: No index on products.category_id (intentional)\n'
            '        CREATE TABLE IF NOT EXISTS products (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            name        TEXT NOT NULL,\n'
            '            category_id INTEGER NOT NULL,\n'
            '            price       REAL NOT NULL,\n'
            '            stock       INTEGER NOT NULL\n'
            '        );\n'
            '\n'
            '        -- NOTE: No index on reviews.product_id or reviews.user_id (intentional)\n'
            '        CREATE TABLE IF NOT EXISTS reviews (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            product_id  INTEGER NOT NULL,\n'
            '            user_id     INTEGER NOT NULL,\n'
            '            rating      INTEGER NOT NULL,\n'
            '            body        TEXT NOT NULL,\n'
            '            created_at  TEXT NOT NULL\n'
            '        );\n'
            '    """)\n'
            '\n'
            '\n'
            'def populate(cur: sqlite3.Cursor) -> None:\n'
            '    rng = random.Random(SEED)\n'
            '\n'
            '    cat_names = [\n'
            '        "Electronics", "Books", "Clothing", "Home", "Sports",\n'
            '        "Toys", "Garden", "Automotive", "Food", "Beauty",\n'
            '        "Tools", "Music", "Movies", "Office", "Baby",\n'
            '        "Pets", "Health", "Travel", "Art", "Jewelry",\n'
            '    ][:N_CATEGORIES]\n'
            '\n'
            '    cats = [(i + 1, cat_names[i]) for i in range(N_CATEGORIES)]\n'
            '    cur.executemany("INSERT INTO categories VALUES (?,?)", cats)\n'
            '\n'
            '    users = [(i, f"User_{i:04d}", f"u{i}@mail.com") for i in range(1, N_USERS + 1)]\n'
            '    cur.executemany("INSERT INTO users VALUES (?,?,?)", users)\n'
            '\n'
            '    products = []\n'
            '    for i in range(1, N_PRODUCTS + 1):\n'
            '        cid = rng.randint(1, N_CATEGORIES)\n'
            '        price = round(rng.uniform(1.0, 999.0), 2)\n'
            '        stock = rng.randint(0, 500)\n'
            '        products.append((i, f"Product_{i:04d}", cid, price, stock))\n'
            '    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)\n'
            '\n'
            '    reviews = []\n'
            '    for i in range(1, N_REVIEWS + 1):\n'
            '        pid = rng.randint(1, N_PRODUCTS)\n'
            '        uid = rng.randint(1, N_USERS)\n'
            '        rating = rng.randint(1, 5)\n'
            '        year = rng.randint(2020, 2024)\n'
            '        month = rng.randint(1, 12)\n'
            '        day = rng.randint(1, 28)\n'
            '        sentiment = "great" if rating >= 4 else "okay" if rating == 3 else "poor"\n'
            '        body = f"Review {i} - {sentiment} product."\n'
            '        reviews.append((i, pid, uid, rating, body, f"{year}-{month:02d}-{day:02d}"))\n'
            '    cur.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?)", reviews)\n'
            '\n'
            '\n'
            'def setup(db_path: str = DB_PATH) -> None:\n'
            '    if os.path.exists(db_path):\n'
            '        os.remove(db_path)\n'
            '    conn = sqlite3.connect(db_path)\n'
            '    cur = conn.cursor()\n'
            '    create_tables(cur)\n'
            '    populate(cur)\n'
            '    conn.commit()\n'
            '    conn.close()\n'
            '    print(f"Database created: {db_path}")\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    setup()\n'
        )
        return (template
                .replace("__SEED__", str(seed))
                .replace("__N_USERS__", str(n_users))
                .replace("__N_PRODUCTS__", str(n_products))
                .replace("__N_CATEGORIES__", str(n_categories))
                .replace("__N_REVIEWS__", str(n_reviews)))

    # ── employees_departments DB ──────────────────────────────────────────────

    def _gen_db_employees_departments(self, seed: int, row_counts: dict) -> str:
        n_depts = row_counts["departments"]
        n_emps = row_counts["employees"]
        n_projects = row_counts["projects"]
        n_assignments = row_counts["assignments"]
        template = (
            '"""\n'
            'Create and populate hr.db for D5_query_optimize (employees/departments domain).\n'
            '\n'
            'Intentionally omits indexes so queries are slow.\n'
            '"""\n'
            'import sqlite3\n'
            'import random\n'
            'import os\n'
            '\n'
            'DB_PATH = "hr.db"\n'
            'SEED = __SEED__\n'
            'N_DEPARTMENTS = __N_DEPARTMENTS__\n'
            'N_EMPLOYEES = __N_EMPLOYEES__\n'
            'N_PROJECTS = __N_PROJECTS__\n'
            'N_ASSIGNMENTS = __N_ASSIGNMENTS__\n'
            '\n'
            '\n'
            'def create_tables(cur: sqlite3.Cursor) -> None:\n'
            '    cur.executescript("""\n'
            '        CREATE TABLE IF NOT EXISTS departments (\n'
            '            id      INTEGER PRIMARY KEY,\n'
            '            name    TEXT NOT NULL,\n'
            '            budget  REAL NOT NULL\n'
            '        );\n'
            '\n'
            '        -- NOTE: No index on employees.department_id (intentional)\n'
            '        CREATE TABLE IF NOT EXISTS employees (\n'
            '            id            INTEGER PRIMARY KEY,\n'
            '            name          TEXT NOT NULL,\n'
            '            department_id INTEGER NOT NULL,\n'
            '            salary        REAL NOT NULL,\n'
            '            hire_date     TEXT NOT NULL,\n'
            '            status        TEXT NOT NULL\n'
            '        );\n'
            '\n'
            '        CREATE TABLE IF NOT EXISTS projects (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            name        TEXT NOT NULL,\n'
            '            start_date  TEXT NOT NULL,\n'
            '            end_date    TEXT NOT NULL,\n'
            '            status      TEXT NOT NULL\n'
            '        );\n'
            '\n'
            '        -- NOTE: No index on assignments.employee_id or assignments.project_id (intentional)\n'
            '        CREATE TABLE IF NOT EXISTS assignments (\n'
            '            id          INTEGER PRIMARY KEY,\n'
            '            employee_id INTEGER NOT NULL,\n'
            '            project_id  INTEGER NOT NULL,\n'
            '            role        TEXT NOT NULL,\n'
            '            hours       REAL NOT NULL\n'
            '        );\n'
            '    """)\n'
            '\n'
            '\n'
            'def populate(cur: sqlite3.Cursor) -> None:\n'
            '    rng = random.Random(SEED)\n'
            '\n'
            '    dept_names = [\n'
            '        "Engineering", "Marketing", "Sales", "HR", "Finance",\n'
            '        "Operations", "Legal", "Support", "Research", "Design",\n'
            '        "Analytics", "Security", "DevOps", "QA", "Product",\n'
            '        "Procurement", "Compliance", "Training", "Strategy", "Facilities",\n'
            '        "IT", "Accounting", "Logistics", "Customer Success", "Business Dev",\n'
            '        "Communications", "Risk", "Data Science", "Cloud", "Infra",\n'
            '    ][:N_DEPARTMENTS]\n'
            '\n'
            '    depts = []\n'
            '    for i, name in enumerate(dept_names, 1):\n'
            '        budget = round(rng.uniform(100000, 5000000), 2)\n'
            '        depts.append((i, name, budget))\n'
            '    cur.executemany("INSERT INTO departments VALUES (?,?,?)", depts)\n'
            '\n'
            '    statuses = ["active", "inactive", "on_leave"]\n'
            '    roles = ["lead", "contributor", "reviewer", "observer"]\n'
            '    proj_statuses = ["active", "completed", "planned"]\n'
            '\n'
            '    employees = []\n'
            '    for i in range(1, N_EMPLOYEES + 1):\n'
            '        did = rng.randint(1, N_DEPARTMENTS)\n'
            '        salary = round(rng.uniform(40000, 200000), 2)\n'
            '        year = rng.randint(2010, 2023)\n'
            '        month = rng.randint(1, 12)\n'
            '        day = rng.randint(1, 28)\n'
            '        employees.append((\n'
            '            i, f"Employee_{i:04d}", did, salary,\n'
            '            f"{year}-{month:02d}-{day:02d}",\n'
            '            rng.choice(statuses)\n'
            '        ))\n'
            '    cur.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?)", employees)\n'
            '\n'
            '    projects = []\n'
            '    for i in range(1, N_PROJECTS + 1):\n'
            '        sy = rng.randint(2020, 2022)\n'
            '        sm = rng.randint(1, 12)\n'
            '        ey = rng.randint(2023, 2025)\n'
            '        em = rng.randint(1, 12)\n'
            '        projects.append((\n'
            '            i, f"Project_{i:03d}",\n'
            '            f"{sy}-{sm:02d}-01",\n'
            '            f"{ey}-{em:02d}-28",\n'
            '            rng.choice(proj_statuses)\n'
            '        ))\n'
            '    cur.executemany("INSERT INTO projects VALUES (?,?,?,?,?)", projects)\n'
            '\n'
            '    assignments = []\n'
            '    for i in range(1, N_ASSIGNMENTS + 1):\n'
            '        eid = rng.randint(1, N_EMPLOYEES)\n'
            '        pid = rng.randint(1, N_PROJECTS)\n'
            '        hours = round(rng.uniform(1.0, 200.0), 1)\n'
            '        assignments.append((i, eid, pid, rng.choice(roles), hours))\n'
            '    cur.executemany("INSERT INTO assignments VALUES (?,?,?,?,?)", assignments)\n'
            '\n'
            '\n'
            'def setup(db_path: str = DB_PATH) -> None:\n'
            '    if os.path.exists(db_path):\n'
            '        os.remove(db_path)\n'
            '    conn = sqlite3.connect(db_path)\n'
            '    cur = conn.cursor()\n'
            '    create_tables(cur)\n'
            '    populate(cur)\n'
            '    conn.commit()\n'
            '    conn.close()\n'
            '    print(f"Database created: {db_path}")\n'
            '\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    setup()\n'
        )
        return (template
                .replace("__SEED__", str(seed))
                .replace("__N_DEPARTMENTS__", str(n_depts))
                .replace("__N_EMPLOYEES__", str(n_emps))
                .replace("__N_PROJECTS__", str(n_projects))
                .replace("__N_ASSIGNMENTS__", str(n_assignments)))

    # ──────────────────────────────────────────────────────────────────────────
    # queries.py (slow, unoptimized)
    # ──────────────────────────────────────────────────────────────────────────

    def _gen_queries_py(self, domain_key: str, queries_meta: list[dict]) -> str:
        """Generate queries.py with one slow function per optimization challenge."""
        header = f'''"""Slow database queries for D5_query_optimize ({domain_key} domain).

Each function below contains one or more performance problems:
  - Missing indexes causing full table scans
  - N+1 query patterns (one query per row)
  - Inefficient correlated subqueries instead of aggregations
  - Non-covering indexes

Your task: optimize each function so it returns IDENTICAL results
but runs within the target latency specified in the spec.
"""
import sqlite3
from typing import Any

'''
        db_file = {
            "users_orders": "store.db",
            "products_reviews": "catalog.db",
            "employees_departments": "hr.db",
        }[domain_key]

        header += f'DB_PATH = "{db_file}"\n\n\n'

        funcs = []
        for qm in queries_meta:
            opt = qm["opt_type"]
            q_num = qm["num"]
            func = self._slow_query_func(domain_key, opt, q_num)
            funcs.append(func)

        return header + "\n\n".join(funcs) + "\n"

    def _slow_query_func(self, domain_key: str, opt_type: str, q_num: int) -> str:
        """Return a slow query function body for a given optimization type and domain."""

        if domain_key == "users_orders":
            return self._slow_func_users_orders(opt_type, q_num)
        elif domain_key == "products_reviews":
            return self._slow_func_products_reviews(opt_type, q_num)
        else:
            return self._slow_func_employees_departments(opt_type, q_num)

    def _slow_func_users_orders(self, opt_type: str, q_num: int) -> str:
        templates: dict[str, str] = {
            "add_index": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all orders for users in the \'US\', sorted by total descending.

    Performance problem: orders.user_id has no index, so the join requires
    a full table scan of orders for every user row.
    Target: < 10ms after optimization (add index on orders.user_id).
    """
    cur = conn.cursor()
    # Slow: full scan of orders table for every US user
    cur.execute("""
        SELECT u.id AS user_id, u.name, o.id AS order_id, o.total, o.status
        FROM users u
        JOIN orders o ON o.user_id = u.id
        WHERE u.country = \'US\'
        ORDER BY o.total DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "rewrite_join": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return order line-items with product names for all \'delivered\' orders.

    Performance problem: order_items.order_id has no index, causing a nested
    loop join that becomes O(n*m) on large tables.
    Target: < 50ms after optimization (add index on order_items.order_id).
    """
    cur = conn.cursor()
    # Slow: full scan of order_items for each delivered order
    cur.execute("""
        SELECT o.id AS order_id, p.name AS product_name,
               oi.quantity, oi.unit_price,
               (oi.quantity * oi.unit_price) AS line_total
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p     ON p.id = oi.product_id
        WHERE o.status = \'delivered\'
        ORDER BY o.id, line_total DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "eliminate_n_plus_1": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each user with their total number of orders.

    Performance problem: N+1 pattern — fetches all users then issues one
    COUNT query per user.  On 500 users this is 501 round-trips.
    Target: < 20ms after optimization (single aggregated query).
    """
    cur = conn.cursor()
    # Slow: N+1 — one extra query per user
    cur.execute("SELECT id, name FROM users")
    users = cur.fetchall()

    results = []
    for uid, name in users:
        cur2 = conn.cursor()
        cur2.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (uid,))
        count = cur2.fetchone()[0]
        results.append({{"user_id": uid, "name": name, "order_count": count}})

    return sorted(results, key=lambda r: -r["order_count"])''',

            "use_aggregation": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each product with its total revenue across all order_items.

    Performance problem: correlated subquery computes SUM per product row,
    executing once per product instead of once total.
    Target: < 30ms after optimization (use GROUP BY aggregation).
    """
    cur = conn.cursor()
    # Slow: correlated subquery — runs once per product row
    cur.execute("""
        SELECT p.id, p.name, p.category,
               (SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0)
                FROM order_items oi
                WHERE oi.product_id = p.id) AS total_revenue
        FROM products p
        ORDER BY total_revenue DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "covering_index": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return pending orders with user_id and total for reporting.

    Performance problem: even if an index on orders.user_id exists,
    SQLite must fetch the full row to read \'status\' and \'total\'.
    A composite covering index (user_id, status, total) eliminates the row fetch.
    Target: < 15ms after optimization (add covering index).
    """
    cur = conn.cursor()
    # Slow: index on user_id alone doesn\'t cover status/total columns
    cur.execute("""
        SELECT user_id, status, SUM(total) AS total_spend
        FROM orders
        WHERE status = \'pending\'
        GROUP BY user_id
        ORDER BY total_spend DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',
        }
        return templates.get(opt_type, f'def query_{q_num}(conn): pass')

    def _slow_func_products_reviews(self, opt_type: str, q_num: int) -> str:
        templates: dict[str, str] = {
            "add_index": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all reviews for products in the \'Electronics\' category.

    Performance problem: reviews.product_id has no index, causing a full
    scan of the reviews table for each matching product.
    Target: < 10ms after optimization (add index on reviews.product_id).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT p.name AS product_name, r.rating, r.body, r.created_at
        FROM products p
        JOIN reviews r ON r.product_id = p.id
        JOIN categories c ON c.id = p.category_id
        WHERE c.name = \'Electronics\'
        ORDER BY r.created_at DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "rewrite_join": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return reviews written by each user along with the product name.

    Performance problem: reviews.user_id has no index; join scans reviews
    for each user row.
    Target: < 50ms after optimization (add index on reviews.user_id).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id AS user_id, u.name AS user_name,
               p.name AS product_name, r.rating
        FROM users u
        JOIN reviews r ON r.user_id = u.id
        JOIN products p ON p.id = r.product_id
        ORDER BY u.id, r.rating DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "eliminate_n_plus_1": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each product with its average rating.

    Performance problem: N+1 — fetches all products then runs one AVG query
    per product (400 products = 401 queries).
    Target: < 20ms after optimization (single aggregated query).
    """
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM products")
    products = cur.fetchall()

    results = []
    for pid, name in products:
        cur2 = conn.cursor()
        cur2.execute("SELECT AVG(rating) FROM reviews WHERE product_id = ?", (pid,))
        avg = cur2.fetchone()[0] or 0.0
        results.append({{"product_id": pid, "name": name, "avg_rating": round(avg, 2)}})

    return sorted(results, key=lambda r: -r["avg_rating"])''',

            "use_aggregation": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each category with its total number of reviews.

    Performance problem: correlated subquery counts reviews per category row.
    Target: < 30ms after optimization (use GROUP BY with JOIN).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.name,
               (SELECT COUNT(*)
                FROM reviews r
                JOIN products p ON p.id = r.product_id
                WHERE p.category_id = c.id) AS review_count
        FROM categories c
        ORDER BY review_count DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "covering_index": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return high-rated reviews (rating >= 4) per product for display.

    Performance problem: no covering index on (product_id, rating) forces
    row fetches for every review to evaluate the WHERE clause.
    Target: < 15ms after optimization (composite covering index).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT product_id, COUNT(*) AS high_rating_count,
               AVG(rating) AS avg_rating
        FROM reviews
        WHERE rating >= 4
        GROUP BY product_id
        ORDER BY high_rating_count DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',
        }
        return templates.get(opt_type, f'def query_{q_num}(conn): pass')

    def _slow_func_employees_departments(self, opt_type: str, q_num: int) -> str:
        templates: dict[str, str] = {
            "add_index": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all active employees in a given department, sorted by salary desc.

    Performance problem: employees.department_id has no index, causing a
    full table scan on every department lookup.
    Target: < 10ms after optimization (add index on employees.department_id).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.name, d.name AS department, e.salary, e.hire_date
        FROM employees e
        JOIN departments d ON d.id = e.department_id
        WHERE e.status = \'active\'
        ORDER BY e.salary DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "rewrite_join": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each assignment with employee name and project name.

    Performance problem: assignments.employee_id and assignments.project_id
    have no indexes; both joins require full scans.
    Target: < 50ms after optimization.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id AS assignment_id,
               e.name AS employee_name,
               p.name AS project_name,
               a.role, a.hours
        FROM assignments a
        JOIN employees e ON e.id = a.employee_id
        JOIN projects p  ON p.id = a.project_id
        ORDER BY a.hours DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "eliminate_n_plus_1": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each project with the total hours assigned.

    Performance problem: N+1 — fetches all projects then runs one SUM query
    per project.
    Target: < 20ms after optimization (single aggregated query).
    """
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    projects = cur.fetchall()

    results = []
    for pid, name in projects:
        cur2 = conn.cursor()
        cur2.execute("SELECT COALESCE(SUM(hours), 0) FROM assignments WHERE project_id = ?", (pid,))
        total_hours = cur2.fetchone()[0]
        results.append({{"project_id": pid, "name": name, "total_hours": total_hours}})

    return sorted(results, key=lambda r: -r["total_hours"])''',

            "use_aggregation": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each department with its total headcount and average salary.

    Performance problem: correlated subqueries compute both COUNT and AVG
    per department row — two sub-scans of employees per department.
    Target: < 30ms after optimization (single GROUP BY query).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.name,
               (SELECT COUNT(*) FROM employees e WHERE e.department_id = d.id) AS headcount,
               (SELECT AVG(salary) FROM employees e WHERE e.department_id = d.id) AS avg_salary
        FROM departments d
        ORDER BY headcount DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',

            "covering_index": f'''def query_{q_num}(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return salary bands per department for active employees.

    Performance problem: even with an index on department_id, reading salary
    requires fetching full rows.  A covering index (department_id, salary)
    would make this index-only.
    Target: < 15ms after optimization.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT department_id,
               COUNT(*) AS headcount,
               MIN(salary) AS min_salary,
               MAX(salary) AS max_salary,
               AVG(salary) AS avg_salary
        FROM employees
        WHERE status = \'active\'
        GROUP BY department_id
        ORDER BY avg_salary DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]''',
        }
        return templates.get(opt_type, f'def query_{q_num}(conn): pass')

    # ──────────────────────────────────────────────────────────────────────────
    # tests/test_queries.py
    # ──────────────────────────────────────────────────────────────────────────

    def _gen_test_py(self, domain_key: str, queries_meta: list[dict]) -> str:
        db_file = {
            "users_orders": "store.db",
            "products_reviews": "catalog.db",
            "employees_departments": "hr.db",
        }[domain_key]

        db_module = {
            "users_orders": "store",
            "products_reviews": "catalog",
            "employees_departments": "hr",
        }[domain_key]

        query_imports = ", ".join(f"query_{qm['num']}" for qm in queries_meta)

        # Build individual test functions
        test_funcs = []
        for qm in queries_meta:
            q_num = qm["num"]
            opt_type = qm["opt_type"]
            target_ms = qm["target_ms"]
            test_funcs.append(
                self._gen_test_func(domain_key, q_num, opt_type, target_ms, db_file)
            )

        all_tests = "\n\n".join(test_funcs)

        return f'''"""Correctness and performance tests for D5_query_optimize.

Run with:
    python3 database.py       # create the DB first
    python3 -m pytest tests/ -v
"""
import os
import sys
import sqlite3
import time
import pytest

# Allow importing from workspace root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import setup, DB_PATH
from queries import {query_imports}

DB_FILE = DB_PATH


@pytest.fixture(scope="session", autouse=True)
def database():
    """Create fresh database once per test session."""
    setup(DB_FILE)
    yield
    # Leave DB in place for inspection


def _conn():
    return sqlite3.connect(DB_FILE)


{all_tests}
'''

    def _gen_test_func(
        self,
        domain_key: str,
        q_num: int,
        opt_type: str,
        target_ms: int,
        db_file: str,
    ) -> str:
        """Generate one pytest test function for a query."""

        # Correctness assertion description per opt_type and domain
        correctness_checks = {
            ("users_orders", "add_index"): "all rows must have user_id set; status-field present",
            ("users_orders", "rewrite_join"): "line_total = quantity * unit_price",
            ("users_orders", "eliminate_n_plus_1"): "order_count >= 0 for every user",
            ("users_orders", "use_aggregation"): "total_revenue >= 0 for every product",
            ("users_orders", "covering_index"): "every row status == 'pending'",
            ("products_reviews", "add_index"): "all rows must have a rating in 1-5",
            ("products_reviews", "rewrite_join"): "product_name must be non-empty string",
            ("products_reviews", "eliminate_n_plus_1"): "avg_rating in [0.0, 5.0]",
            ("products_reviews", "use_aggregation"): "review_count >= 0",
            ("products_reviews", "covering_index"): "high_rating_count >= 1",
            ("employees_departments", "add_index"): "status == 'active' for all rows",
            ("employees_departments", "rewrite_join"): "hours > 0 for all rows",
            ("employees_departments", "eliminate_n_plus_1"): "total_hours >= 0",
            ("employees_departments", "use_aggregation"): "headcount >= 0",
            ("employees_departments", "covering_index"): "min_salary <= max_salary",
        }

        desc = correctness_checks.get((domain_key, opt_type), "results must be a non-empty list")

        # Build the inline assertion code per type
        assert_block = self._correctness_assert(domain_key, opt_type, q_num)

        return f'''def test_query_{q_num}_correctness():
    """query_{q_num} ({opt_type}): {desc}"""
    conn = _conn()
    rows = query_{q_num}(conn)
    conn.close()

    assert isinstance(rows, list), "query_{q_num} must return a list"
    assert len(rows) > 0, "query_{q_num} returned 0 rows — likely broken"
{assert_block}


def test_query_{q_num}_performance():
    """query_{q_num} ({opt_type}): must complete in < {target_ms}ms after optimization."""
    conn = _conn()
    start = time.perf_counter()
    rows = query_{q_num}(conn)
    elapsed_ms = (time.perf_counter() - start) * 1000
    conn.close()

    assert len(rows) > 0, "query_{q_num} returned no rows"
    assert elapsed_ms < {target_ms}, (
        f"query_{q_num} took {{elapsed_ms:.1f}}ms, target is {target_ms}ms. "
        f"Add required indexes and/or rewrite the query."
    )


def test_query_{q_num}_result_stability():
    """query_{q_num}: two consecutive calls must return identical results."""
    conn = _conn()
    rows_a = query_{q_num}(conn)
    rows_b = query_{q_num}(conn)
    conn.close()

    assert rows_a == rows_b, "query_{q_num} returned different results on repeated calls"'''

    def _correctness_assert(self, domain_key: str, opt_type: str, q_num: int) -> str:
        """Return correctness assertion lines for a given query."""
        q = f"query_{q_num}"

        checks: dict[tuple[str, str], str] = {
            ("users_orders", "add_index"): f'''\
    for r in rows:
        assert "user_id" in r, f"{q}: missing user_id in row {{r}}"
        assert "total" in r, f"{q}: missing total in row {{r}}"''',

            ("users_orders", "rewrite_join"): f'''\
    for r in rows:
        expected_total = round(r["quantity"] * r["unit_price"], 2)
        assert abs(r["line_total"] - expected_total) < 0.01, (
            f"{q}: line_total mismatch: {{r['line_total']}} vs {{expected_total}}"
        )''',

            ("users_orders", "eliminate_n_plus_1"): f'''\
    for r in rows:
        assert r["order_count"] >= 0, f"{q}: negative order_count in {{r}}"
    # Verify descending order
    counts = [r["order_count"] for r in rows]
    assert counts == sorted(counts, reverse=True), "{q}: not sorted by order_count desc"''',

            ("users_orders", "use_aggregation"): f'''\
    for r in rows:
        assert r["total_revenue"] >= 0, f"{q}: negative total_revenue in {{r}}"
    # Verify descending order
    revenues = [r["total_revenue"] for r in rows]
    assert revenues == sorted(revenues, reverse=True), "{q}: not sorted by total_revenue desc"''',

            ("users_orders", "covering_index"): f'''\
    for r in rows:
        assert r["status"] == "pending", f"{q}: non-pending row in result: {{r}}"
        assert r["total_spend"] > 0, f"{q}: zero total_spend in {{r}}"''',

            ("products_reviews", "add_index"): f'''\
    for r in rows:
        assert 1 <= r["rating"] <= 5, f"{q}: invalid rating {{r['rating']}} in {{r}}"''',

            ("products_reviews", "rewrite_join"): f'''\
    for r in rows:
        assert isinstance(r["product_name"], str) and r["product_name"], (
            f"{q}: empty product_name in {{r}}"
        )
        assert 1 <= r["rating"] <= 5, f"{q}: invalid rating in {{r}}"''',

            ("products_reviews", "eliminate_n_plus_1"): f'''\
    for r in rows:
        assert 0.0 <= r["avg_rating"] <= 5.0, f"{q}: avg_rating out of range in {{r}}"
    # Verify descending order
    avgs = [r["avg_rating"] for r in rows]
    assert avgs == sorted(avgs, reverse=True), "{q}: not sorted by avg_rating desc"''',

            ("products_reviews", "use_aggregation"): f'''\
    for r in rows:
        assert r["review_count"] >= 0, f"{q}: negative review_count in {{r}}"
    counts = [r["review_count"] for r in rows]
    assert counts == sorted(counts, reverse=True), "{q}: not sorted by review_count desc"''',

            ("products_reviews", "covering_index"): f'''\
    for r in rows:
        assert r["high_rating_count"] >= 1, f"{q}: high_rating_count < 1 in {{r}}"
    counts = [r["high_rating_count"] for r in rows]
    assert counts == sorted(counts, reverse=True), "{q}: not sorted by high_rating_count desc"''',

            ("employees_departments", "add_index"): f'''\
    for r in rows:
        assert r.get("status") == "active" or "department" in r, (
            f"{q}: unexpected row {{r}}"
        )
        assert r["salary"] > 0, f"{q}: non-positive salary in {{r}}"''',

            ("employees_departments", "rewrite_join"): f'''\
    for r in rows:
        assert r["hours"] > 0, f"{q}: non-positive hours in {{r}}"
        assert isinstance(r["employee_name"], str), f"{q}: bad employee_name in {{r}}"''',

            ("employees_departments", "eliminate_n_plus_1"): f'''\
    for r in rows:
        assert r["total_hours"] >= 0, f"{q}: negative total_hours in {{r}}"
    hours = [r["total_hours"] for r in rows]
    assert hours == sorted(hours, reverse=True), "{q}: not sorted by total_hours desc"''',

            ("employees_departments", "use_aggregation"): f'''\
    for r in rows:
        assert r["headcount"] >= 0, f"{q}: negative headcount in {{r}}"
    counts = [r["headcount"] for r in rows]
    assert counts == sorted(counts, reverse=True), "{q}: not sorted by headcount desc"''',

            ("employees_departments", "covering_index"): f'''\
    for r in rows:
        assert r["min_salary"] <= r["max_salary"], (
            f"{q}: min_salary > max_salary in {{r}}"
        )
        assert r["headcount"] >= 1, f"{q}: headcount < 1 in {{r}}"''',
        }

        return checks.get((domain_key, opt_type), f'    assert rows, "{q}: empty result"')

    # ──────────────────────────────────────────────────────────────────────────
    # spec.md and brief.md
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_spec(
        self,
        domain_key: str,
        domain: dict,
        queries_meta: list[dict],
        expected: dict,
    ) -> str:
        query_sections = []
        for qm in queries_meta:
            q_name = qm["name"]
            opt = qm["opt_type"]
            target_ms = qm["target_ms"]
            opt_label = opt.replace("_", " ").title()
            query_sections.append(f"""
### {q_name} — {opt_label}

- **Optimization required**: {opt_label}
- **Target latency**: < {target_ms}ms
- **Current problem**: {self._opt_problem_desc(opt, domain_key)}
- **Fix**: {self._opt_fix_desc(opt, domain_key)}
""")

        query_details = "\n".join(query_sections)

        required_idx_list = "\n".join(
            f"- `{idx}`" for idx in expected["required_indexes"]
        ) or "- (none beyond per-query indexes)"

        forbidden_list = "\n".join(
            f"- `{p}`" for p in expected["forbidden_patterns"]
        ) or "- (none)"

        row_counts = domain["row_counts"]
        table_sizes = "\n".join(
            f"| `{tbl}` | {cnt:,} |"
            for tbl, cnt in row_counts.items()
        )

        return f"""# D5: Query Optimization (Planner Specification)

## Context

{domain['description']}

The application's database layer was built without indexes. As data grew, several
queries became unacceptably slow. This spec gives you the complete execution-plan
analysis and per-query latency targets needed to plan the optimization work.

## Database Schema

Domain: **{domain['label']}**

Table sizes at grading time:

| Table | Rows |
|-------|------|
{table_sizes}

## Execution Plan Analysis

The following {len(queries_meta)} queries in `queries.py` must be optimized.
{query_details}

## Required Indexes (must be present after optimization)

{required_idx_list}

## Forbidden Patterns (must NOT appear in optimized code)

{forbidden_list}

## Scoring Rubric

| Criterion | Weight |
|-----------|--------|
| Correctness — all queries return identical results to original | 50% |
| Performance — each query within target latency | 30% |
| Readability — clean SQL, no unnecessary complexity | 20% |

## Deliverables

1. **`database.py`** — add `CREATE INDEX` statements (in `create_tables()`).
2. **`queries.py`** — rewrite each slow function to use proper joins / aggregations.
3. All tests in `tests/test_queries.py` must pass:
   ```
   python3 database.py
   python3 -m pytest tests/ -v
   ```

## Constraints

- The database schema (table structure) must not change.
- Query results must be **bit-for-bit identical** before and after optimization.
- Indexes must be created in `database.py`, not as inline SQL in queries.
- Do not reduce data volume or add caches — the fix must be structural.
"""

    def _opt_problem_desc(self, opt_type: str, domain_key: str) -> str:
        descs = {
            "add_index": "Missing index on foreign key causes full table scan on every query.",
            "rewrite_join": "Join without index causes O(n×m) nested-loop scan.",
            "eliminate_n_plus_1": "N+1 pattern: one extra query issued per row of the outer result.",
            "use_aggregation": "Correlated subquery runs once per outer row instead of once total.",
            "covering_index": "Index exists but does not cover all projected columns, forcing row fetches.",
        }
        return descs.get(opt_type, "Unknown pattern.")

    def _opt_fix_desc(self, opt_type: str, domain_key: str) -> str:
        fixes = {
            "add_index": "Add a B-tree index on the foreign key column used in the WHERE/JOIN.",
            "rewrite_join": "Add an index on the join column; SQLite will switch to an index-based join.",
            "eliminate_n_plus_1": "Replace the loop+query with a single query using LEFT JOIN + GROUP BY.",
            "use_aggregation": "Replace the correlated subquery with a JOIN + GROUP BY aggregation.",
            "covering_index": "Add a composite index that includes all columns read by the query.",
        }
        return fixes.get(opt_type, "Rewrite the query.")

    def _generate_brief(self, domain_key: str) -> str:
        domain_label = DOMAINS[domain_key]["label"]
        return f"""# D5: Query Optimization (Brief)

Several database queries in the **{domain_label}** system are too slow.
The application is timing out under normal load.

## Your Task

Optimize the queries in `queries.py` so they run within acceptable latency.
You may also modify `database.py` to add indexes.

## How to Run

```bash
python3 database.py          # (re)create the database
python3 -m pytest tests/ -v  # run correctness + performance tests
```

All tests must pass. Query results must remain correct after optimization.
"""
