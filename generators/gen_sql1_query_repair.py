"""
Parameterized generator for SQL1: Query Repair.

Each seed produces:
  - Different employee names (from NamePool)
  - Different salary values (which employees are high-salary changes)
  - Different department budgets (which departments are over-budget changes)
  - Different project names and deadlines (which projects are overdue changes)
  - Different manager assignments
  - Seed-specific expected.json, setup_db.py, spec.md

The 5 bug TYPES stay the same (wrong GROUP BY/correlated subquery, wrong JOIN column,
wrong date comparison, wrong self-join column, unsupported RIGHT JOIN + bad ORDER BY alias)
but the specific data and expected row counts change per seed.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import (
    SeededRandom, NamePool, ValuePool, DEPARTMENTS, PROJECT_NAMES,
)

# Fixed reference date for "overdue" determination (deterministic grading)
REFERENCE_DATE = "2025-01-01"

# Possible department names (pick 5 per seed from this list)
DEPT_POOL = [
    "Engineering", "Marketing", "Sales", "HR", "Finance",
    "Operations", "Legal", "Support", "Research", "Design",
]

# One department is always "Executive" (zero employees) to test LEFT JOIN
EXECUTIVE_DEPT = "Executive"


class Generator(TaskGenerator):
    task_id = "SQL1_query_repair"
    domain = "data"
    difficulty = "medium"
    languages = ["python", "sql"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=30)
        salary_rng = SeededRandom(seed + 1)
        budget_rng = SeededRandom(seed + 2)
        project_rng = SeededRandom(seed + 3)
        date_rng = SeededRandom(seed + 4)

        # ── Pick 4 regular departments + Executive (always present for Q5) ──
        regular_depts = rng.sample(DEPT_POOL, 4)
        # departments list: 4 regular + Executive
        dept_names = regular_depts + [EXECUTIVE_DEPT]

        # ── Generate 15 employees spread across the 4 regular departments ──
        # Ensure each regular dept has at least 1 employee for JOIN tests
        employees = []
        emp_id = 1

        # Assign 2-5 employees per regular department (totalling 15 - 1 boundary = ~15)
        dept_sizes = {}
        remaining = 15
        for i, dept in enumerate(regular_depts):
            if i == len(regular_depts) - 1:
                count = remaining
            else:
                count = rng.randint(2, max(2, remaining - (len(regular_depts) - i - 1) * 2))
                count = min(count, remaining - (len(regular_depts) - i - 1))
            dept_sizes[dept] = count
            remaining -= count

        # Generate salary ranges per dept (base salary 50k-120k)
        dept_salary_ranges = {}
        for dept in regular_depts:
            base = salary_rng.randint(50000, 90000)
            dept_salary_ranges[dept] = (base, base + salary_rng.randint(20000, 60000))

        for dept in regular_depts:
            lo, hi = dept_salary_ranges[dept]
            for _ in range(dept_sizes[dept]):
                salary = salary_rng.randint(lo, hi)
                # Hire date: random year 2015-2023
                year = date_rng.randint(2015, 2023)
                month = date_rng.randint(1, 12)
                day = date_rng.randint(1, 28)
                hire_date = f"{year:04d}-{month:02d}-{day:02d}"
                employees.append({
                    "id": emp_id,
                    "name": names.next(),
                    "department": dept,
                    "salary": salary,
                    "hire_date": hire_date,
                })
                emp_id += 1

        # ── Compute Q1 expected: employees above their dept average ──
        dept_salaries: dict[str, list[float]] = {}
        for e in employees:
            dept_salaries.setdefault(e["department"], []).append(e["salary"])
        dept_avg = {d: sum(v) / len(v) for d, v in dept_salaries.items()}

        q1_rows = [e for e in employees if e["salary"] > dept_avg[e["department"]]]
        q1_rows.sort(key=lambda e: (e["department"], -e["salary"]))
        q1_count = len(q1_rows)

        # ── Generate departments with budgets ──
        # Make 2-3 regular depts over-budget (total salary > budget)
        n_over_budget = rng.randint(2, min(3, len(regular_depts)))
        over_budget_depts = rng.sample(regular_depts, n_over_budget)

        dept_total_salary = {
            dept: sum(e["salary"] for e in employees if e["department"] == dept)
            for dept in regular_depts
        }

        # Assign manager from each dept's employees
        dept_emp_map: dict[str, list[dict]] = {}
        for e in employees:
            dept_emp_map.setdefault(e["department"], []).append(e)

        departments = []
        dept_id_map: dict[str, int] = {}
        manager_map: dict[str, str] = {}  # dept name -> manager employee name

        for i, dept in enumerate(dept_names):
            dept_id = i + 1
            dept_id_map[dept] = dept_id

            if dept == EXECUTIVE_DEPT:
                budget = budget_rng.randint(200000, 500000)
                manager_id = None
            else:
                total = dept_total_salary[dept]
                if dept in over_budget_depts:
                    # Budget is 80-95% of total (so dept is over budget)
                    budget = int(total * budget_rng.uniform(0.80, 0.95))
                else:
                    # Budget is 110-150% of total (under budget)
                    budget = int(total * budget_rng.uniform(1.10, 1.50))
                # Pick a random employee as manager
                mgr = rng.choice(dept_emp_map[dept])
                manager_id = mgr["id"]
                manager_map[dept] = mgr["name"]

            departments.append({
                "id": dept_id,
                "name": dept,
                "budget": budget,
                "manager_id": manager_id,
            })

        # ── Q2 expected: over-budget departments ──
        over_budget_names = sorted(over_budget_depts)
        q2_count = len(over_budget_names)

        # ── Generate projects (8 total) ──
        # 3-4 active overdue projects (deadline < REFERENCE_DATE)
        # 1-2 active NOT overdue (deadline >= REFERENCE_DATE)
        # rest completed (status doesn't matter for Q3)
        proj_names_pool = rng.sample(PROJECT_NAMES, 8)

        n_overdue = rng.randint(3, 4)
        n_active_not_overdue = rng.randint(1, 2)
        n_completed = 8 - n_overdue - n_active_not_overdue

        projects = []
        proj_id = 1

        # Overdue active projects (deadline in 2023-2024 before Jan 1 2025)
        overdue_proj_names = []
        for i in range(n_overdue):
            year = date_rng.randint(2023, 2024)
            month = date_rng.randint(1, 12)
            day = date_rng.randint(1, 28)
            deadline = f"{year:04d}-{month:02d}-{day:02d}"
            # Ensure strictly before reference date
            if deadline >= REFERENCE_DATE:
                deadline = "2024-06-15"
            dept = rng.choice(regular_depts)
            pname = proj_names_pool[i]
            overdue_proj_names.append(pname)
            projects.append({
                "id": proj_id,
                "name": pname,
                "department_id": dept_id_map[dept],
                "deadline": deadline,
                "status": "active",
            })
            proj_id += 1

        # Active but NOT overdue (deadline on or after reference date)
        for i in range(n_active_not_overdue):
            year = date_rng.randint(2025, 2026)
            month = date_rng.randint(1, 12)
            day = date_rng.randint(1, 28)
            deadline = f"{year:04d}-{month:02d}-{day:02d}"
            dept = rng.choice(regular_depts)
            projects.append({
                "id": proj_id,
                "name": proj_names_pool[n_overdue + i],
                "department_id": dept_id_map[dept],
                "deadline": deadline,
                "status": "active",
            })
            proj_id += 1

        # Completed projects
        for i in range(n_completed):
            year = date_rng.randint(2022, 2024)
            month = date_rng.randint(1, 12)
            day = date_rng.randint(1, 28)
            deadline = f"{year:04d}-{month:02d}-{day:02d}"
            dept = rng.choice(regular_depts)
            projects.append({
                "id": proj_id,
                "name": proj_names_pool[n_overdue + n_active_not_overdue + i],
                "department_id": dept_id_map[dept],
                "deadline": deadline,
                "status": "completed",
            })
            proj_id += 1

        q3_count = n_overdue

        # ── Q4 expected: department managers ──
        # Only depts with manager_id IS NOT NULL
        q4_count = len([d for d in departments if d["manager_id"] is not None])
        # manager_map already has dept->manager_name for regular depts

        # ── Q5 expected: employee count per department ──
        # Includes Executive with 0
        dept_emp_count = {dept: 0 for dept in dept_names}
        for e in employees:
            dept_emp_count[e["department"]] += 1
        # First row is dept with highest count
        sorted_depts_by_count = sorted(
            dept_names,
            key=lambda d: (-dept_emp_count[d], d)
        )
        q5_first_dept = sorted_depts_by_count[0]
        q5_count = len(dept_names)  # always 5 (4 regular + Executive)

        # ── Build expected ground truth ──
        expected = {
            "q1_row_count": q1_count,
            "q1_high_salary_names": [e["name"] for e in q1_rows],
            "q2_row_count": q2_count,
            "q2_over_budget_depts": over_budget_names,
            "q3_row_count": q3_count,
            "q3_overdue_project_names": overdue_proj_names,
            "q4_row_count": q4_count,
            "q4_manager_map": manager_map,
            "q5_row_count": q5_count,
            "q5_first_dept": q5_first_dept,
            "q5_dept_counts": dept_emp_count,
            "reference_date": REFERENCE_DATE,
            "departments": dept_names,
        }

        # ── Generate workspace files ──
        setup_db_py = self._generate_setup_db(employees, departments, projects)
        queries_py = self._generate_buggy_queries()
        main_py = self._generate_main(q1_count, q2_count, over_budget_names,
                                       q3_count, overdue_proj_names,
                                       q4_count, manager_map,
                                       q5_count, q5_first_dept, dept_emp_count)

        workspace_files = {
            "setup_db.py": setup_db_py,
            "queries.py": queries_py,
            "main.py": main_py,
        }

        spec_md = self._generate_spec(employees, departments, projects, dept_names,
                                       q1_count, q2_count, over_budget_names,
                                       q3_count, q4_count, manager_map,
                                       q5_count, q5_first_dept, dept_emp_count)
        brief_md = self._generate_brief()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_setup_db(
        self,
        employees: list[dict],
        departments: list[dict],
        projects: list[dict],
    ) -> str:
        emp_rows = ",\n        ".join(
            f"({e['id']}, {e['name']!r}, {e['department']!r}, {e['salary']}, {e['hire_date']!r})"
            for e in employees
        )
        dept_rows = ",\n        ".join(
            f"({d['id']}, {d['name']!r}, {d['budget']}, "
            f"{'None' if d['manager_id'] is None else d['manager_id']})"
            for d in departments
        )
        proj_rows = ",\n        ".join(
            f"({p['id']}, {p['name']!r}, {p['department_id']}, {p['deadline']!r}, {p['status']!r})"
            for p in projects
        )

        return f'''"""Create and populate company.db for SQL1_query_repair task."""
import sqlite3
import os

DB_PATH = "company.db"


def setup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE employees (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            department  TEXT NOT NULL,
            salary      REAL NOT NULL,
            hire_date   TEXT NOT NULL
        );

        CREATE TABLE departments (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            budget      REAL NOT NULL,
            manager_id  INTEGER
        );

        CREATE TABLE projects (
            id            INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            deadline      TEXT NOT NULL,
            status        TEXT NOT NULL
        );
    """)

    employees = [
        {emp_rows},
    ]
    cur.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?)", employees)

    departments = [
        {dept_rows},
    ]
    cur.executemany("INSERT INTO departments VALUES (?, ?, ?, ?)", departments)

    projects = [
        {proj_rows},
    ]
    cur.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?)", projects)

    conn.commit()
    conn.close()
    print(f"Database created: {{DB_PATH}}")


if __name__ == "__main__":
    setup()
'''

    def _generate_buggy_queries(self) -> str:
        """Generate queries.py with the same 5 bug types as the original."""
        return '''"""SQL query functions for company reporting.

Each function accepts a sqlite3.Connection and returns a list of dicts.
All 5 queries below contain a subtle bug -- fix them so main.py passes.
"""
import sqlite3


def get_high_salary_employees(db: sqlite3.Connection) -> list[dict]:
    """Return employees whose salary exceeds their department\'s average salary.

    Bug: uses a global AVG instead of a correlated per-department AVG.
    """
    cur = db.cursor()
    cur.execute("""
        SELECT e.id, e.name, e.department, e.salary
        FROM employees e
        WHERE e.salary > (SELECT AVG(salary) FROM employees)
        ORDER BY e.department, e.salary DESC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_over_budget_departments(db: sqlite3.Connection) -> list[dict]:
    """Return departments where total employee salary exceeds the department budget.

    Bug: JOIN condition uses d.id (integer PK) instead of d.name (text),
    so the text-to-integer comparison matches nothing in SQLite.
    """
    cur = db.cursor()
    cur.execute("""
        SELECT d.name, d.budget, SUM(e.salary) AS total_salary
        FROM employees e
        JOIN departments d ON e.department = d.id
        GROUP BY d.name
        HAVING SUM(e.salary) > d.budget
        ORDER BY d.name
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_overdue_projects(db: sqlite3.Connection) -> list[dict]:
    """Return active projects whose deadline has already passed.

    Uses a fixed reference date of 2025-01-01 for deterministic grading.

    Bug: compares ISO date strings against a Unix timestamp integer string
    produced by strftime(\'%s\', \'now\'), so the string comparison is wrong
    and no projects appear overdue.
    """
    cur = db.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.deadline, d.name AS department
        FROM projects p
        JOIN departments d ON p.department_id = d.id
        WHERE p.status = \'active\'
          AND p.deadline < strftime(\'%s\', \'now\')
        ORDER BY p.deadline
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_department_managers(db: sqlite3.Connection) -> list[dict]:
    """Return each department and its manager\'s name.

    Bug: JOIN condition uses d.id instead of m.id, so the join is always
    a self-match on the department\'s own PK rather than looking up the
    manager employee row.
    """
    cur = db.cursor()
    cur.execute("""
        SELECT d.name AS department, m.name AS manager_name
        FROM departments d
        JOIN employees m ON d.manager_id = d.id
        WHERE d.manager_id IS NOT NULL
        ORDER BY d.name
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_employee_count_by_dept(db: sqlite3.Connection) -> list[dict]:
    """Return each department and its employee count, ordered by count desc.

    Bug 1: RIGHT JOIN is not supported in SQLite < 3.39, dropping the
    department with 0 employees.
    Bug 2: ORDER BY references COUNT(e.id) as a new aggregate expression
    rather than the aliased column emp_count, producing undefined ordering.
    """
    cur = db.cursor()
    cur.execute("""
        SELECT d.name AS department, COUNT(*) AS emp_count
        FROM departments d
        RIGHT JOIN employees e ON e.department = d.name
        GROUP BY d.name
        ORDER BY COUNT(e.id) DESC, d.name ASC
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
'''

    def _generate_main(
        self,
        q1_count: int,
        q2_count: int,
        over_budget_names: list[str],
        q3_count: int,
        overdue_proj_names: list[str],
        q4_count: int,
        manager_map: dict[str, str],
        q5_count: int,
        q5_first_dept: str,
        dept_emp_count: dict[str, int],
    ) -> str:
        over_budget_set = set(over_budget_names)
        overdue_set = set(overdue_proj_names)
        dept_counts_repr = repr(dept_emp_count)

        manager_assertions = "\n        ".join(
            f"assert actual_mgrs.get({dept!r}) == {mgr!r}, "
            f"f'Manager for {dept}: expected {mgr!r}, got {{actual_mgrs.get({dept!r})!r}}'"
            for dept, mgr in manager_map.items()
        )

        return f'''"""Test runner for SQL1_query_repair.

Runs all 5 query functions, prints results, validates expected row counts,
and exits 0 if all pass or 1 if any fail.
"""
import json
import os
import sqlite3
import sys

from queries import (
    get_department_managers,
    get_employee_count_by_dept,
    get_high_salary_employees,
    get_over_budget_departments,
    get_overdue_projects,
)

DB_PATH = "company.db"

EXPECTED = {{
    "get_high_salary_employees": {{
        "row_count": {q1_count},
        "description": "employees earning above their department average",
    }},
    "get_over_budget_departments": {{
        "row_count": {q2_count},
        "description": "departments whose total salary exceeds budget",
        "names": {sorted(over_budget_names)!r},
    }},
    "get_overdue_projects": {{
        "row_count": {q3_count},
        "description": "active projects with deadline before {REFERENCE_DATE}",
    }},
    "get_department_managers": {{
        "row_count": {q4_count},
        "description": "departments with their manager names",
        "managers": {manager_map!r},
    }},
    "get_employee_count_by_dept": {{
        "row_count": {q5_count},
        "description": "employee count per department including zero-count depts",
        "first_dept": {q5_first_dept!r},
    }},
}}


def run_check(name, rows, spec):
    failures = []

    actual_count = len(rows)
    expected_count = spec["row_count"]
    if actual_count != expected_count:
        failures.append(
            f"row count: expected {{expected_count}}, got {{actual_count}}"
        )

    if "names" in spec:
        actual_names = sorted(r.get("name", r.get("department", "")) for r in rows)
        expected_names = sorted(spec["names"])
        if actual_names != expected_names:
            failures.append(
                f"department names: expected {{expected_names}}, got {{actual_names}}"
            )

    if "managers" in spec:
        actual_mgrs = {{r["department"]: r["manager_name"] for r in rows}}
        for dept, mgr in spec["managers"].items():
            if actual_mgrs.get(dept) != mgr:
                failures.append(
                    f"manager for {{dept}}: expected {{mgr!r}}, got {{actual_mgrs.get(dept)!r}}"
                )

    if "first_dept" in spec and rows:
        if rows[0]["department"] != spec["first_dept"]:
            failures.append(
                f"first dept: expected {{spec[\'first_dept\']!r}}, got {{rows[0][\'department\']!r}}"
            )

    return failures


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {{DB_PATH}} not found. Run `python3 setup_db.py` first.")
        sys.exit(1)

    db = sqlite3.connect(DB_PATH)

    checks = [
        ("get_high_salary_employees",  get_high_salary_employees),
        ("get_over_budget_departments", get_over_budget_departments),
        ("get_overdue_projects",        get_overdue_projects),
        ("get_department_managers",     get_department_managers),
        ("get_employee_count_by_dept",  get_employee_count_by_dept),
    ]

    all_passed = True

    for name, fn in checks:
        spec = EXPECTED[name]
        print(f"\\n=== {{name}} ===")
        print(f"    ({{spec[\'description\']}})")
        try:
            rows = fn(db)
        except Exception as exc:
            print(f"  ERROR: {{exc}}")
            all_passed = False
            continue

        for row in rows:
            print(f"  {{row}}")

        failures = run_check(name, rows, spec)
        if failures:
            all_passed = False
            for f in failures:
                print(f"  FAIL: {{f}}")
        else:
            print(f"  PASS ({{len(rows)}} rows)")

    db.close()

    print("\\n" + ("=" * 40))
    if all_passed:
        print("ALL CHECKS PASSED")
        att = {{"verdict": "pass", "checks": 5, "passed": 5}}
        with open("attestation.json", "w") as fh:
            json.dump(att, fh)
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    def _generate_spec(
        self,
        employees: list[dict],
        departments: list[dict],
        projects: list[dict],
        dept_names: list[str],
        q1_count: int,
        q2_count: int,
        over_budget_names: list[str],
        q3_count: int,
        q4_count: int,
        manager_map: dict[str, str],
        q5_count: int,
        q5_first_dept: str,
        dept_emp_count: dict[str, int],
    ) -> str:
        # Build employee table rows
        emp_rows = "\n".join(
            f"| {e['id']:2d} | {e['name']:<10} | {e['department']:<12} | {e['salary']:7.0f} | {e['hire_date']} |"
            for e in employees
        )
        # Build department table rows
        dept_rows = "\n".join(
            f"| {d['id']} | {d['name']:<12} | {d['budget']:7.0f} | {d['manager_id'] if d['manager_id'] is not None else 'NULL':>4} |"
            for d in departments
        )
        # Build project table rows
        proj_rows = "\n".join(
            f"| {p['id']} | {p['name']:<20} | {p['department_id']:13d} | {p['deadline']} | {p['status']:<10} |"
            for p in projects
        )
        over_budget_str = ", ".join(over_budget_names)
        mgr_str = ", ".join(f"{d}→{m}" for d, m in sorted(manager_map.items()))
        dept_counts_str = ", ".join(
            f"{d}: {dept_emp_count[d]}"
            for d in sorted(dept_names, key=lambda x: (-dept_emp_count[x], x))
        )

        return f"""# SQL1: Query Repair (Planner Specification)

## Database Schema

The app uses SQLite (`company.db`) with three tables:

```sql
CREATE TABLE employees (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    department  TEXT NOT NULL,
    salary      REAL NOT NULL,
    hire_date   TEXT NOT NULL   -- stored as ISO-8601: 'YYYY-MM-DD'
);

CREATE TABLE departments (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    budget      REAL NOT NULL,
    manager_id  INTEGER         -- FK -> employees.id
);

CREATE TABLE projects (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    department_id INTEGER NOT NULL,  -- FK -> departments.id
    deadline      TEXT NOT NULL,     -- stored as ISO-8601: 'YYYY-MM-DD'
    status        TEXT NOT NULL      -- 'active' | 'completed' | 'cancelled'
);
```

## Test Data Summary

**employees** ({len(employees)} rows):

| id | name       | department   | salary  | hire_date  |
|----|------------|--------------|---------|------------|
{emp_rows}

**departments** ({len(departments)} rows):

| id | name         | budget  | manager_id |
|----|--------------|---------|------------|
{dept_rows}

**projects** ({len(projects)} rows):

| id | name                 | department_id | deadline   | status     |
|----|----------------------|---------------|------------|------------|
{proj_rows}

## The 5 Broken Queries

### Query 1: `get_high_salary_employees(db)`

**Intent:** Return each employee whose salary exceeds the average salary of their own department (not the company-wide average).

**Current behavior:** The query returns incorrect results because it does not scope the average to the employee's department.

**Expected row count: {q1_count}**

### Query 2: `get_over_budget_departments(db)`

**Intent:** Return each department where the sum of employee salaries exceeds the department's budget.

**Current behavior:** The query produces incorrect results because the join between the employees and departments tables uses mismatched column types.

**Expected row count: {q2_count}** ({over_budget_str})

### Query 3: `get_overdue_projects(db)`

**Intent:** Return active projects whose deadline has already passed. For grading purposes, "today" is fixed at `{REFERENCE_DATE}` so results are deterministic.

**Current behavior:** The query returns no results (or wrong results) because the deadline comparison uses incompatible formats.

**Expected row count: {q3_count}**

### Query 4: `get_department_managers(db)`

**Intent:** Return each department's name alongside its manager's name, looked up from the employees table via the `manager_id` foreign key.

**Current behavior:** The join condition references the wrong column when resolving the manager.

**Expected row count: {q4_count}** ({mgr_str}; {EXECUTIVE_DEPT} excluded because it has no manager)

### Query 5: `get_employee_count_by_dept(db)`

**Intent:** Return each department and its employee count (including departments with zero employees), ordered by count descending, then department name ascending.

**Current behavior:** The query uses a join type that excludes departments with no employees, and the ordering is inconsistent.

**Expected row count: {q5_count}** ({dept_counts_str})

## Deliverables

The executor must edit `queries.py` so that all 5 functions return correct results. No schema changes and no data changes are permitted.
"""

    def _generate_brief(self) -> str:
        return """# SQL1: Query Repair (Brief)

Fix the 5 broken SQL queries in `queries.py`.

Run with:
```
python3 setup_db.py
python3 main.py
```

All 5 queries must pass their row-count and correctness checks.
"""
