# SQL1: Query Repair (Planner Specification)

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

**employees** (15 rows):

| id | name    | department  | salary | hire_date  |
|----|---------|-------------|--------|------------|
| 1  | Alice   | Engineering | 95000  | 2019-03-15 |
| 2  | Bob     | Engineering | 72000  | 2020-07-01 |
| 3  | Carol   | Marketing   | 68000  | 2018-11-20 |
| 4  | Dave    | Engineering | 110000 | 2017-05-10 |
| 5  | Eve     | Marketing   | 75000  | 2021-02-28 |
| 6  | Frank   | Sales       | 58000  | 2022-01-15 |
| 7  | Grace   | Sales       | 62000  | 2021-09-03 |
| 8  | Heidi   | HR          | 70000  | 2019-06-22 |
| 9  | Ivan    | HR          | 66000  | 2020-04-11 |
| 10 | Judy    | Engineering | 88000  | 2018-08-30 |
| 11 | Karl    | Marketing   | 71000  | 2023-03-01 |
| 12 | Liam    | Sales       | 54000  | 2022-11-14 |
| 13 | Mia     | HR          | 73000  | 2021-07-19 |
| 14 | Noah    | Engineering | 91000  | 2016-12-05 |
| 15 | Olivia  | Marketing   | 65000  | 2023-06-30 |

**departments** (5 rows):

| id | name        | budget | manager_id |
|----|-------------|--------|------------|
| 1  | Engineering | 500000 | 4          |
| 2  | Marketing   | 200000 | 3          |
| 3  | Sales       | 150000 | 7          |
| 4  | HR          | 180000 | 8          |
| 5  | Executive   | 300000 | NULL       |

**projects** (8 rows):

| id | name               | department_id | deadline   | status    |
|----|--------------------|---------------|------------|-----------|
| 1  | Platform Rewrite   | 1             | 2023-06-01 | completed |
| 2  | Q4 Campaign        | 2             | 2024-01-15 | completed |
| 3  | Sales Automation   | 3             | 2024-03-01 | active    |
| 4  | HR Portal          | 4             | 2023-12-31 | completed |
| 5  | Mobile App         | 1             | 2025-01-01 | active    |
| 6  | Brand Refresh      | 2             | 2024-09-01 | active    |
| 7  | Recruit Pipeline   | 4             | 2024-06-15 | active    |
| 8  | Data Warehouse     | 1             | 2024-11-30 | active    |

## The 5 Broken Queries

### Query 1: `get_high_salary_employees(db)`

**Intent:** Return each employee whose salary exceeds the average salary of their own department (not the company-wide average).

**Current behavior:** The query returns incorrect results because it does not scope the average to the employee's department.

**Expected row count: 7**

### Query 2: `get_over_budget_departments(db)`

**Intent:** Return each department where the sum of employee salaries exceeds the department's budget.

**Current behavior:** The query produces incorrect results because the join between the employees and departments tables uses mismatched column types, causing the join to not match records as intended.

**Expected row count: 3** (Marketing, Sales, HR)

### Query 3: `get_overdue_projects(db)`

**Intent:** Return active projects whose deadline has already passed. For grading purposes, "today" is fixed at `2025-01-01` so results are deterministic.

**Current behavior:** The query returns no results (or wrong results) because the deadline column value and the comparison value are expressed in incompatible formats, causing the comparison to evaluate incorrectly.

**Expected row count: 4** (Sales Automation, Brand Refresh, Recruit Pipeline, Data Warehouse)

### Query 4: `get_department_managers(db)`

**Intent:** Return each department's name alongside its manager's name, looked up from the employees table via the `manager_id` foreign key.

**Current behavior:** The join condition references the wrong column when resolving the manager, so manager names are not correctly retrieved.

**Expected row count: 4** (Engineering→Dave, HR→Heidi, Marketing→Carol, Sales→Grace; Executive excluded because it has no manager)

### Query 5: `get_employee_count_by_dept(db)`

**Intent:** Return each department and its employee count (including departments with zero employees), ordered by count descending, then department name ascending.

**Current behavior:** The query uses a join type that excludes departments with no employees, and the ordering does not produce consistent results.

**Expected row count: 5** (Engineering: 5, Marketing: 4, HR: 3, Sales: 3, Executive: 0)

## Deliverables

The executor must edit `queries.py` so that all 5 functions return correct results. No schema changes and no data changes are permitted.
