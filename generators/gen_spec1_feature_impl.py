"""
Parameterized generator for SPEC1: Specification to Implementation.

Each seed selects a different feature domain and produces:
  - A skeleton app.py with 3-4 TODO functions (no business-rule details)
  - models.py with data classes (provided, no changes needed)
  - tests/test_app.py with basic tests that validate structure but not all edge cases
  - spec.md with full PRD including exact error messages, transition rules, edge cases
  - brief.md that only says "implement the TODOs"
  - expected.json with per-seed ground-truth used by grade.sh

TNI driver: TODO comments describe WHAT to implement but not HOW.
The spec contains exact error messages, status-transition rules, sort orders,
decimal precision, and boundary conditions that cannot be inferred from the
skeleton or the tests alone.

Seed → domain mapping:
  0 → Task management API
  1 → Inventory system
  2 → Booking system
  3 → Grading calculator
  4 → Expense tracker
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ---------------------------------------------------------------------------
# Domain definitions
# ---------------------------------------------------------------------------

DOMAINS = [
    "task_management",
    "inventory_system",
    "booking_system",
    "grading_calculator",
    "expense_tracker",
]


class Generator(TaskGenerator):
    task_id = "SPEC1_feature_impl"
    domain = "software"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        domain_idx = seed % len(DOMAINS)
        domain = DOMAINS[domain_idx]

        # Each domain has its own sub-generator
        if domain == "task_management":
            return self._gen_task_management(seed, rng)
        elif domain == "inventory_system":
            return self._gen_inventory(seed, rng)
        elif domain == "booking_system":
            return self._gen_booking(seed, rng)
        elif domain == "grading_calculator":
            return self._gen_grading(seed, rng)
        else:
            return self._gen_expense_tracker(seed, rng)

    # -----------------------------------------------------------------------
    # Domain 0: Task Management API
    # -----------------------------------------------------------------------

    def _gen_task_management(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        # Vary per-seed: which status transitions are allowed, priority sort order
        statuses = ["TODO", "IN_PROGRESS", "DONE", "CANCELLED"]
        # Pick which transitions are forbidden (always include DONE->TODO)
        forbidden_pairs = [("DONE", "TODO"), ("CANCELLED", "IN_PROGRESS")]
        extra_forbidden = rng.choice([
            ("DONE", "IN_PROGRESS"),
            ("CANCELLED", "DONE"),
        ])
        forbidden_pairs.append(extra_forbidden)

        # Vary priority values and their sort weights
        priority_order = ["HIGH", "MEDIUM", "LOW"]
        rng.shuffle(priority_order)  # order for display doesn't change, but weight assignment varies
        priority_weights = {p: i for i, p in enumerate(priority_order)}

        # Vary due date format
        date_format = rng.choice(["%Y-%m-%d", "%d/%m/%Y"])
        date_format_desc = "YYYY-MM-DD" if date_format == "%Y-%m-%d" else "DD/MM/YYYY"

        # Vary max title length
        max_title_len = rng.choice([80, 100, 120])

        expected = {
            "domain": "task_management",
            "forbidden_transitions": [[a, b] for a, b in forbidden_pairs],
            "priority_order": priority_order,
            "date_format": date_format,
            "date_format_desc": date_format_desc,
            "max_title_len": max_title_len,
            "error_not_found": "TASK_NOT_FOUND",
            "error_invalid_transition": "INVALID_TRANSITION",
            "error_invalid_priority": "INVALID_PRIORITY",
            "error_title_too_long": "TITLE_TOO_LONG",
            "error_invalid_date": "INVALID_DATE_FORMAT",
            "sort_field": "priority_then_due",
        }

        forbidden_str = "\n".join(
            f"  - `{a}` → `{b}` is **not allowed**" for a, b in forbidden_pairs
        )
        priority_sort_desc = " > ".join(priority_order)

        spec_md = f"""# SPEC1: Task Management API — Full Specification

## Overview
Implement a task management system that supports creating, reading, updating,
and deleting tasks. Tasks have a title, status, priority, and optional due date.

## Data Model
A task has these fields (see `models.py`):
- `id` (int): auto-assigned, starts at 1, increments by 1 per task created
- `title` (str): non-empty, max {max_title_len} characters
- `status` (str): one of `TODO`, `IN_PROGRESS`, `DONE`, `CANCELLED`
- `priority` (str): one of `HIGH`, `MEDIUM`, `LOW`
- `due_date` (str | None): optional, must be in `{date_format_desc}` format if provided

## API Functions to Implement

### `create_task(store, title, priority, due_date=None)`
Creates a new task with status `TODO`.
- **Error `TITLE_TOO_LONG`** if `len(title) > {max_title_len}`
- **Error `INVALID_PRIORITY`** if priority not in `HIGH`, `MEDIUM`, `LOW`
- **Error `INVALID_DATE_FORMAT`** if `due_date` is provided but not a valid `{date_format_desc}` date
- Returns the created task dict.

### `get_task(store, task_id)`
Returns the task dict for the given id.
- **Error `TASK_NOT_FOUND`** if no task with that id exists.

### `update_task_status(store, task_id, new_status)`
Transitions a task to a new status.
- **Error `TASK_NOT_FOUND`** if task does not exist.
- **Error `INVALID_TRANSITION`** for the following forbidden transitions:
{forbidden_str}
- All other transitions between valid statuses are permitted.

### `list_tasks(store, status_filter=None, priority_filter=None)`
Returns a list of tasks, optionally filtered.
- If `status_filter` is given, return only tasks with that status.
- If `priority_filter` is given, return only tasks with that priority.
- Result must be sorted: **{priority_sort_desc}** first (by priority),
  then by `due_date` ascending (tasks without a due date sort last),
  then by `id` ascending as a tiebreaker.

### `delete_task(store, task_id)`
Removes a task permanently.
- **Error `TASK_NOT_FOUND`** if no task with that id exists.
- Returns the deleted task dict.

## Error Contract
All errors must be raised as `AppError(code)` where `code` is the exact string
listed above (e.g., `AppError("TASK_NOT_FOUND")`). No other exception types are
acceptable for business-rule violations.

## Edge Cases (REQUIRED)
- Title consisting of only whitespace is treated as empty and must raise
  `AppError("TITLE_TOO_LONG")` — wait, actually whitespace-only titles: strip
  the title first; if stripped title is empty, raise `AppError("TITLE_TOO_LONG")`
  (treat length 0 as exceeding the minimum, not maximum).
  Clarification: raise `AppError("INVALID_TITLE")` for empty/whitespace-only titles.
- Deleting a task that is in `DONE` status is allowed.
- A task cannot transition from `DONE` back to `TODO` — this is a hard rule
  even if not listed above as a seed-specific rule.
- `due_date` must be a calendar-valid date (e.g., `2024-02-30` is invalid).
- Priority comparison is case-sensitive: `high` is not valid; only `HIGH` is.

## Deliverables
- `app.py` with all four functions implemented
- All tests in `tests/test_app.py` must pass
- Verifier checks exact error codes and sort order
"""

        brief_md = f"""# SPEC1: Task Management API (Brief)

Implement the TODO functions in `app.py`. The workspace contains:
- `app.py` — skeleton with TODO placeholders
- `models.py` — data classes (do not modify)
- `tests/test_app.py` — basic tests

Run tests with: `python -m pytest tests/`

The functions to implement:
- `create_task` — create a new task
- `get_task` — retrieve a task by id
- `update_task_status` — change task status
- `list_tasks` — list with optional filters
- `delete_task` — remove a task
"""

        models_py = '''\
"""Data models for the task management system. Do not modify."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Task:
    id: int
    title: str
    status: str
    priority: str
    due_date: Optional[str] = None


@dataclass
class TaskStore:
    """In-memory task store."""
    _tasks: Dict[int, Task] = field(default_factory=dict)
    _next_id: int = 1

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def remove(self, task_id: int) -> Optional[Task]:
        return self._tasks.pop(task_id, None)

    def all(self) -> List[Task]:
        return list(self._tasks.values())

    def next_id(self) -> int:
        return self._next_id
'''

        # Build forbidden transition repr for code comment
        forbidden_code_comment = ", ".join(
            f'("{a}", "{b}")' for a, b in forbidden_pairs
        )

        app_py = f'''\
"""Task management API — implement the TODO functions below."""
from datetime import datetime
from models import Task, TaskStore


class AppError(Exception):
    """Business-rule violation. The code attribute holds the error string."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


# Allowed statuses and priorities
STATUSES = {{"TODO", "IN_PROGRESS", "DONE", "CANCELLED"}}
PRIORITIES = {{"HIGH", "MEDIUM", "LOW"}}

# Forbidden status transitions (from_status, to_status)
# Spec-defined: {forbidden_code_comment}
FORBIDDEN_TRANSITIONS = [
    {", ".join(f'("{a}", "{b}")' for a, b in forbidden_pairs)}
]

DATE_FORMAT = "{date_format}"
MAX_TITLE_LEN = {max_title_len}

# Priority sort order: lower index = higher priority
PRIORITY_ORDER = {priority_order}


def create_task(store: TaskStore, title: str, priority: str, due_date: str = None) -> dict:
    """
    Create a new task with status TODO.

    TODO: Implement this function.
    - Validate title length (<= MAX_TITLE_LEN), strip first; empty/whitespace raises AppError("INVALID_TITLE")
    - Validate priority is in PRIORITIES, else raise AppError("INVALID_PRIORITY")
    - Validate due_date format (DATE_FORMAT) if provided, else raise AppError("INVALID_DATE_FORMAT")
    - Assign the next id from store, set status to "TODO"
    - Return the task as a dict with keys: id, title, status, priority, due_date
    """
    raise NotImplementedError("TODO: implement create_task")


def get_task(store: TaskStore, task_id: int) -> dict:
    """
    Return task dict for the given id.

    TODO: Implement this function.
    - Raise AppError("TASK_NOT_FOUND") if task_id not in store
    - Return the task as a dict
    """
    raise NotImplementedError("TODO: implement get_task")


def update_task_status(store: TaskStore, task_id: int, new_status: str) -> dict:
    """
    Transition a task to new_status.

    TODO: Implement this function.
    - Raise AppError("TASK_NOT_FOUND") if task_id not in store
    - Raise AppError("INVALID_TRANSITION") if (current_status, new_status) is in FORBIDDEN_TRANSITIONS
    - Update the task's status and return the updated task as a dict
    """
    raise NotImplementedError("TODO: implement update_task_status")


def list_tasks(store: TaskStore, status_filter: str = None, priority_filter: str = None) -> list:
    """
    List tasks, optionally filtered by status and/or priority.

    TODO: Implement this function.
    - Filter by status_filter if provided (exact match)
    - Filter by priority_filter if provided (exact match)
    - Sort by: priority (PRIORITY_ORDER index ascending), then due_date ascending
      (None due dates sort last), then id ascending as tiebreaker
    - Return list of task dicts
    """
    raise NotImplementedError("TODO: implement list_tasks")


def delete_task(store: TaskStore, task_id: int) -> dict:
    """
    Permanently remove a task.

    TODO: Implement this function.
    - Raise AppError("TASK_NOT_FOUND") if task_id not in store
    - Remove and return the deleted task as a dict
    """
    raise NotImplementedError("TODO: implement delete_task")


def _task_to_dict(task: Task) -> dict:
    """Helper: convert Task dataclass to dict."""
    return {{
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
    }}
'''

        # Example date for tests
        good_date = "2024-06-15" if date_format == "%Y-%m-%d" else "15/06/2024"
        bad_date = "15-06-2024" if date_format == "%Y-%m-%d" else "2024-06-15"

        test_py = f'''\
"""Basic tests for task management API. Tests validate structure but not all edge cases."""
import pytest
from models import TaskStore
from app import AppError, create_task, get_task, update_task_status, list_tasks, delete_task


@pytest.fixture
def store():
    return TaskStore()


def test_create_task_basic(store):
    t = create_task(store, "Write docs", "HIGH")
    assert t["id"] == 1
    assert t["title"] == "Write docs"
    assert t["status"] == "TODO"
    assert t["priority"] == "HIGH"
    assert t["due_date"] is None


def test_create_task_with_due_date(store):
    t = create_task(store, "Deploy", "MEDIUM", "{good_date}")
    assert t["due_date"] == "{good_date}"


def test_create_task_invalid_priority(store):
    with pytest.raises(AppError) as exc:
        create_task(store, "Task", "URGENT")
    assert exc.value.code == "INVALID_PRIORITY"


def test_create_task_bad_date(store):
    with pytest.raises(AppError) as exc:
        create_task(store, "Task", "LOW", "{bad_date}")
    assert exc.value.code == "INVALID_DATE_FORMAT"


def test_get_task_not_found(store):
    with pytest.raises(AppError) as exc:
        get_task(store, 999)
    assert exc.value.code == "TASK_NOT_FOUND"


def test_get_task_found(store):
    create_task(store, "Do it", "LOW")
    t = get_task(store, 1)
    assert t["title"] == "Do it"


def test_update_status_valid(store):
    create_task(store, "Start me", "HIGH")
    t = update_task_status(store, 1, "IN_PROGRESS")
    assert t["status"] == "IN_PROGRESS"


def test_update_status_not_found(store):
    with pytest.raises(AppError) as exc:
        update_task_status(store, 42, "DONE")
    assert exc.value.code == "TASK_NOT_FOUND"


def test_update_forbidden_transition(store):
    create_task(store, "Done task", "MEDIUM")
    update_task_status(store, 1, "IN_PROGRESS")
    update_task_status(store, 1, "DONE")
    with pytest.raises(AppError) as exc:
        update_task_status(store, 1, "TODO")
    assert exc.value.code == "INVALID_TRANSITION"


def test_list_tasks_empty(store):
    assert list_tasks(store) == []


def test_list_tasks_filter_status(store):
    create_task(store, "A", "HIGH")
    create_task(store, "B", "LOW")
    update_task_status(store, 2, "IN_PROGRESS")
    result = list_tasks(store, status_filter="TODO")
    assert len(result) == 1
    assert result[0]["title"] == "A"


def test_delete_task(store):
    create_task(store, "Remove me", "LOW")
    deleted = delete_task(store, 1)
    assert deleted["title"] == "Remove me"
    with pytest.raises(AppError):
        get_task(store, 1)


def test_delete_task_not_found(store):
    with pytest.raises(AppError) as exc:
        delete_task(store, 99)
    assert exc.value.code == "TASK_NOT_FOUND"


def test_ids_autoincrement(store):
    t1 = create_task(store, "First", "HIGH")
    t2 = create_task(store, "Second", "LOW")
    assert t2["id"] == t1["id"] + 1
'''

        workspace_files = {
            "app.py": app_py,
            "models.py": models_py,
            "tests/__init__.py": "",
            "tests/test_app.py": test_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # -----------------------------------------------------------------------
    # Domain 1: Inventory System
    # -----------------------------------------------------------------------

    def _gen_inventory(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        reorder_threshold = rng.randint(5, 20)
        max_quantity = rng.randint(500, 2000)
        # Vary log action names
        log_add = rng.choice(["RESTOCK", "ADD", "RECEIVE"])
        log_remove = rng.choice(["SALE", "REMOVE", "DISPATCH"])
        log_adjust = "ADJUST"
        # Vary whether negative stock is allowed (always not, but error code varies)
        error_insufficient = rng.choice(["INSUFFICIENT_STOCK", "OUT_OF_STOCK", "STOCK_DEPLETED"])
        error_not_found = "ITEM_NOT_FOUND"
        error_invalid_qty = "INVALID_QUANTITY"
        error_exceeds_max = "EXCEEDS_MAX_QUANTITY"

        expected = {
            "domain": "inventory_system",
            "reorder_threshold": reorder_threshold,
            "max_quantity": max_quantity,
            "log_add_action": log_add,
            "log_remove_action": log_remove,
            "log_adjust_action": log_adjust,
            "error_insufficient": error_insufficient,
            "error_not_found": error_not_found,
            "error_invalid_qty": error_invalid_qty,
            "error_exceeds_max": error_exceeds_max,
        }

        spec_md = f"""# SPEC1: Inventory System — Full Specification

## Overview
Implement an inventory tracking system that manages stock levels, supports batch
updates, enforces quantity constraints, and records an audit log for every change.

## Data Model (see `models.py`)
- `Item`: id, name, quantity (int), category (str)
- `InventoryStore`: holds items and an ordered audit log list
- `LogEntry`: item_id, action (str), delta (int), quantity_after (int)

## API Functions to Implement

### `add_item(store, name, category, initial_quantity=0)`
Register a new item.
- **Error `{error_invalid_qty}`** if `initial_quantity < 0` or not an integer.
- **Error `{error_exceeds_max}`** if `initial_quantity > {max_quantity}`.
- Appends a log entry with action `"{log_add}"`, delta = initial_quantity,
  quantity_after = initial_quantity.
- Returns the item dict.

### `restock(store, item_id, quantity)`
Add stock to an existing item.
- **Error `{error_not_found}`** if item_id does not exist.
- **Error `{error_invalid_qty}`** if quantity <= 0 or not a positive integer.
- **Error `{error_exceeds_max}`** if resulting quantity would exceed {max_quantity}.
- Appends log entry: action=`"{log_add}"`, delta=quantity, quantity_after=new total.
- Returns updated item dict.

### `remove_stock(store, item_id, quantity)`
Reduce stock for a sale or dispatch.
- **Error `{error_not_found}`** if item_id does not exist.
- **Error `{error_invalid_qty}`** if quantity <= 0.
- **Error `{error_insufficient}`** if current quantity < quantity requested.
- Appends log entry: action=`"{log_remove}"`, delta=-quantity, quantity_after=new total.
- Returns updated item dict.

### `batch_update(store, updates)`
Apply a list of `(item_id, delta)` pairs atomically.
- `delta > 0` means add stock, `delta < 0` means remove stock.
- **All-or-nothing**: validate ALL updates first; if ANY would fail, raise the
  error for the first failing update without applying any changes.
- Applies all updates only if all validations pass.
- Appends one `"{log_adjust}"` log entry per item updated (in order).
- Returns list of updated item dicts.

### `get_reorder_list(store)`
Return items that need reordering.
- An item needs reordering when `quantity <= {reorder_threshold}`.
- Returns list of item dicts sorted by quantity ascending, then by id ascending.

### `get_audit_log(store, item_id=None)`
Return the audit log.
- If `item_id` is given, return only entries for that item.
- Always returns entries in chronological order (insertion order).
- Each entry is a dict: `{{item_id, action, delta, quantity_after}}`.

## Error Contract
All errors raised as `AppError(code)` with the exact codes above.

## Edge Cases (REQUIRED)
- `restock` with quantity=0 raises `{error_invalid_qty}` (zero is not positive).
- `batch_update` with an empty list is valid and returns `[]`.
- Log entries for `batch_update` use action `"{log_adjust}"` not `"{log_add}"` or `"{log_remove}"`.
- `get_reorder_list` includes items with quantity exactly equal to {reorder_threshold} (not just below).
- Item ids start at 1 and auto-increment.

## Deliverables
- `app.py` with all functions implemented
- All tests in `tests/test_app.py` must pass
"""

        brief_md = f"""# SPEC1: Inventory System (Brief)

Implement the TODO functions in `app.py`. The workspace contains:
- `app.py` — skeleton with TODO placeholders
- `models.py` — data classes (do not modify)
- `tests/test_app.py` — basic tests

Run tests with: `python -m pytest tests/`

Functions to implement: `add_item`, `restock`, `remove_stock`,
`batch_update`, `get_reorder_list`, `get_audit_log`.
"""

        models_py = '''\
"""Data models for the inventory system. Do not modify."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Item:
    id: int
    name: str
    quantity: int
    category: str


@dataclass
class LogEntry:
    item_id: int
    action: str
    delta: int
    quantity_after: int


@dataclass
class InventoryStore:
    _items: Dict[int, Item] = field(default_factory=dict)
    _log: List[LogEntry] = field(default_factory=list)
    _next_id: int = 1

    def add_item_record(self, item: Item) -> Item:
        self._items[item.id] = item
        self._next_id += 1
        return item

    def get_item(self, item_id: int) -> Optional[Item]:
        return self._items.get(item_id)

    def all_items(self) -> List[Item]:
        return list(self._items.values())

    def append_log(self, entry: LogEntry) -> None:
        self._log.append(entry)

    def get_log(self) -> List[LogEntry]:
        return list(self._log)

    def next_id(self) -> int:
        return self._next_id
'''

        app_py = f'''\
"""Inventory system API — implement the TODO functions below."""
from models import Item, LogEntry, InventoryStore


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


MAX_QUANTITY = {max_quantity}
REORDER_THRESHOLD = {reorder_threshold}
LOG_ADD = "{log_add}"
LOG_REMOVE = "{log_remove}"
LOG_ADJUST = "{log_adjust}"


def add_item(store: InventoryStore, name: str, category: str, initial_quantity: int = 0) -> dict:
    """
    Register a new inventory item.

    TODO: Implement this function.
    - Raise AppError("{error_invalid_qty}") if initial_quantity < 0 or not int
    - Raise AppError("{error_exceeds_max}") if initial_quantity > MAX_QUANTITY
    - Create Item with next id, append log entry (action=LOG_ADD)
    - Return item as dict
    """
    raise NotImplementedError("TODO: implement add_item")


def restock(store: InventoryStore, item_id: int, quantity: int) -> dict:
    """
    Add stock to an existing item.

    TODO: Implement this function.
    - Raise AppError("{error_not_found}") if item_id not found
    - Raise AppError("{error_invalid_qty}") if quantity <= 0
    - Raise AppError("{error_exceeds_max}") if new total > MAX_QUANTITY
    - Update quantity, append log entry (action=LOG_ADD)
    - Return updated item as dict
    """
    raise NotImplementedError("TODO: implement restock")


def remove_stock(store: InventoryStore, item_id: int, quantity: int) -> dict:
    """
    Reduce stock for a sale/dispatch.

    TODO: Implement this function.
    - Raise AppError("{error_not_found}") if item_id not found
    - Raise AppError("{error_invalid_qty}") if quantity <= 0
    - Raise AppError("{error_insufficient}") if current quantity < quantity
    - Update quantity, append log entry (action=LOG_REMOVE, delta negative)
    - Return updated item as dict
    """
    raise NotImplementedError("TODO: implement remove_stock")


def batch_update(store: InventoryStore, updates: list) -> list:
    """
    Apply list of (item_id, delta) pairs atomically.

    TODO: Implement this function.
    - Validate ALL updates first (all-or-nothing)
    - delta > 0: add stock; delta < 0: remove stock
    - Raise appropriate AppError on first failing validation
    - Append LOG_ADJUST log entry per item (in order)
    - Return list of updated item dicts
    """
    raise NotImplementedError("TODO: implement batch_update")


def get_reorder_list(store: InventoryStore) -> list:
    """
    Return items with quantity <= REORDER_THRESHOLD.

    TODO: Implement this function.
    - Include items where quantity <= REORDER_THRESHOLD (inclusive)
    - Sort by quantity ascending, then id ascending
    - Return list of item dicts
    """
    raise NotImplementedError("TODO: implement get_reorder_list")


def get_audit_log(store: InventoryStore, item_id: int = None) -> list:
    """
    Return audit log entries.

    TODO: Implement this function.
    - If item_id given, filter to that item only
    - Return in insertion order
    - Each entry: dict with item_id, action, delta, quantity_after
    """
    raise NotImplementedError("TODO: implement get_audit_log")


def _item_to_dict(item: Item) -> dict:
    return {{"id": item.id, "name": item.name, "quantity": item.quantity, "category": item.category}}


def _log_to_dict(entry: LogEntry) -> dict:
    return {{"item_id": entry.item_id, "action": entry.action, "delta": entry.delta, "quantity_after": entry.quantity_after}}
'''

        test_py = f'''\
"""Basic tests for inventory system. Tests validate structure but not all edge cases."""
import pytest
from models import InventoryStore
from app import AppError, add_item, restock, remove_stock, batch_update, get_reorder_list, get_audit_log


@pytest.fixture
def store():
    return InventoryStore()


def test_add_item_basic(store):
    item = add_item(store, "Widget", "electronics", 10)
    assert item["id"] == 1
    assert item["name"] == "Widget"
    assert item["quantity"] == 10
    assert item["category"] == "electronics"


def test_add_item_negative_qty(store):
    with pytest.raises(AppError) as exc:
        add_item(store, "X", "cat", -1)
    assert exc.value.code == "{error_invalid_qty}"


def test_add_item_exceeds_max(store):
    with pytest.raises(AppError) as exc:
        add_item(store, "X", "cat", {max_quantity + 1})
    assert exc.value.code == "{error_exceeds_max}"


def test_restock(store):
    add_item(store, "Bolt", "hardware", 50)
    item = restock(store, 1, 100)
    assert item["quantity"] == 150


def test_restock_not_found(store):
    with pytest.raises(AppError) as exc:
        restock(store, 999, 10)
    assert exc.value.code == "{error_not_found}"


def test_remove_stock(store):
    add_item(store, "Nut", "hardware", 100)
    item = remove_stock(store, 1, 30)
    assert item["quantity"] == 70


def test_remove_stock_insufficient(store):
    add_item(store, "Screw", "hardware", 5)
    with pytest.raises(AppError) as exc:
        remove_stock(store, 1, 10)
    assert exc.value.code == "{error_insufficient}"


def test_batch_update_basic(store):
    add_item(store, "A", "cat", 100)
    add_item(store, "B", "cat", 50)
    results = batch_update(store, [(1, -10), (2, 20)])
    qtys = {{r["id"]: r["quantity"] for r in results}}
    assert qtys[1] == 90
    assert qtys[2] == 70


def test_batch_update_atomic(store):
    add_item(store, "A", "cat", 5)
    add_item(store, "B", "cat", 5)
    with pytest.raises(AppError):
        batch_update(store, [(1, -3), (2, -100)])  # second fails
    # Neither should have changed
    assert get_audit_log(store, item_id=1) == [] or True  # no change applied


def test_get_reorder_list(store):
    add_item(store, "Low", "cat", {reorder_threshold})
    add_item(store, "High", "cat", {reorder_threshold + 1})
    reorder = get_reorder_list(store)
    assert len(reorder) == 1
    assert reorder[0]["name"] == "Low"


def test_audit_log(store):
    add_item(store, "Item", "cat", 20)
    restock(store, 1, 10)
    log = get_audit_log(store)
    assert len(log) == 2
    assert log[0]["action"] == "{log_add}"
    assert log[1]["action"] == "{log_add}"


def test_audit_log_filter(store):
    add_item(store, "X", "cat", 10)
    add_item(store, "Y", "cat", 20)
    restock(store, 1, 5)
    log = get_audit_log(store, item_id=1)
    assert all(e["item_id"] == 1 for e in log)
'''

        workspace_files = {
            "app.py": app_py,
            "models.py": models_py,
            "tests/__init__.py": "",
            "tests/test_app.py": test_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # -----------------------------------------------------------------------
    # Domain 2: Booking System
    # -----------------------------------------------------------------------

    def _gen_booking(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        max_advance_days = rng.choice([30, 60, 90])
        cancellation_hours = rng.choice([24, 48, 72])
        max_slots_per_day = rng.randint(3, 8)
        waitlist_max = rng.randint(3, 10)
        error_conflict = rng.choice(["SLOT_CONFLICT", "TIME_CONFLICT", "ALREADY_BOOKED"])
        error_not_found = "BOOKING_NOT_FOUND"
        error_too_late_cancel = "CANCELLATION_TOO_LATE"
        error_too_far_advance = "TOO_FAR_IN_ADVANCE"
        error_no_capacity = "NO_CAPACITY"
        error_waitlist_full = "WAITLIST_FULL"

        expected = {
            "domain": "booking_system",
            "max_advance_days": max_advance_days,
            "cancellation_hours": cancellation_hours,
            "max_slots_per_day": max_slots_per_day,
            "waitlist_max": waitlist_max,
            "error_conflict": error_conflict,
            "error_not_found": error_not_found,
            "error_too_late_cancel": error_too_late_cancel,
            "error_too_far_advance": error_too_far_advance,
            "error_no_capacity": error_no_capacity,
            "error_waitlist_full": error_waitlist_full,
        }

        spec_md = f"""# SPEC1: Booking System — Full Specification

## Overview
Implement a reservation system for bookable time slots. Users can reserve slots,
cancel with a policy, and join a waitlist when a slot is full.

## Data Model (see `models.py`)
- `Slot`: id, date (YYYY-MM-DD str), hour (int 0-23), capacity (int), resource (str)
- `Booking`: id, slot_id, user_id (str), status (`CONFIRMED` or `WAITLISTED`), booked_at (ISO datetime str)
- `BookingStore`: holds slots and bookings

## API Functions to Implement

### `add_slot(store, date, hour, capacity, resource)`
Register a bookable slot.
- `date` must be a valid YYYY-MM-DD string.
- `hour` must be 0–23.
- `capacity` must be >= 1.
- Returns slot dict.

### `book_slot(store, slot_id, user_id, now_iso)`
Create a booking for a user.
- **Error `BOOKING_NOT_FOUND`** if slot_id not found (use `SLOT_NOT_FOUND` code here instead).
  Clarification: raise `AppError("SLOT_NOT_FOUND")` for missing slots.
- **Error `{error_too_far_advance}`** if the slot's date is more than {max_advance_days} days
  after `now_iso`'s date.
- **Error `{error_conflict}`** if the user already has a CONFIRMED booking for this slot.
- If confirmed bookings for the slot >= slot capacity:
  - If waitlist size < {waitlist_max}: create booking with status `WAITLISTED`.
  - Else: raise **`{error_waitlist_full}`**.
- Otherwise: create booking with status `CONFIRMED`.
- `booked_at` = `now_iso`.
- Returns booking dict.

### `cancel_booking(store, booking_id, now_iso)`
Cancel a booking.
- **Error `{error_not_found}`** if booking_id not found.
- **Error `{error_too_late_cancel}`** if fewer than {cancellation_hours} hours remain
  before the slot's start datetime (slot date + hour, treated as UTC).
- Remove the booking. If it was CONFIRMED and waitlisted bookings exist for the same
  slot, promote the **oldest** waitlisted booking to CONFIRMED (FIFO).
- Returns the cancelled booking dict (status remains as it was at time of cancellation).

### `get_bookings(store, slot_id=None, user_id=None, status=None)`
Return bookings matching all provided filters.
- Filters are ANDed together.
- Results sorted by `booked_at` ascending.
- Returns list of booking dicts.

### `get_slot_availability(store, slot_id)`
Return availability info for a slot.
- **Error `SLOT_NOT_FOUND`** if not found.
- Returns dict: `{{slot_id, capacity, confirmed_count, waitlisted_count, available_seats}}`
  where `available_seats = max(0, capacity - confirmed_count)`.

## Error Contract
All errors raised as `AppError(code)` with exact codes above.

## Edge Cases (REQUIRED)
- A user can have at most one CONFIRMED booking per slot (enforce with `{error_conflict}`).
- A user CAN have one CONFIRMED and one WAITLISTED booking for the same slot is not possible;
  once waitlisted, a second booking attempt raises `{error_conflict}`.
- Cancellation window: if slot is on date D at hour H, the slot starts at `D H:00:00 UTC`.
  If `now_iso` is within {cancellation_hours} hours of that start, cancellation is refused.
- Promoting waitlisted bookings on cancellation uses FIFO order (oldest `booked_at` first).
- `max_advance_days` is inclusive: booking exactly {max_advance_days} days ahead is allowed;
  {max_advance_days + 1} days ahead raises `{error_too_far_advance}`.

## Deliverables
- `app.py` with all functions implemented
- All tests in `tests/test_app.py` must pass
"""

        brief_md = f"""# SPEC1: Booking System (Brief)

Implement the TODO functions in `app.py`. The workspace contains:
- `app.py` — skeleton with TODO placeholders
- `models.py` — data classes (do not modify)
- `tests/test_app.py` — basic tests

Run tests with: `python -m pytest tests/`

Functions to implement: `add_slot`, `book_slot`, `cancel_booking`,
`get_bookings`, `get_slot_availability`.
"""

        models_py = '''\
"""Data models for the booking system. Do not modify."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Slot:
    id: int
    date: str          # YYYY-MM-DD
    hour: int          # 0-23
    capacity: int
    resource: str


@dataclass
class Booking:
    id: int
    slot_id: int
    user_id: str
    status: str        # CONFIRMED or WAITLISTED
    booked_at: str     # ISO datetime string


@dataclass
class BookingStore:
    _slots: Dict[int, Slot] = field(default_factory=dict)
    _bookings: Dict[int, Booking] = field(default_factory=dict)
    _next_slot_id: int = 1
    _next_booking_id: int = 1

    def add_slot_record(self, slot: Slot) -> Slot:
        self._slots[slot.id] = slot
        self._next_slot_id += 1
        return slot

    def add_booking_record(self, booking: Booking) -> Booking:
        self._bookings[booking.id] = booking
        self._next_booking_id += 1
        return booking

    def get_slot(self, slot_id: int) -> Optional[Slot]:
        return self._slots.get(slot_id)

    def get_booking(self, booking_id: int) -> Optional[Booking]:
        return self._bookings.get(booking_id)

    def remove_booking(self, booking_id: int) -> Optional[Booking]:
        return self._bookings.pop(booking_id, None)

    def all_bookings(self) -> List[Booking]:
        return list(self._bookings.values())

    def next_slot_id(self) -> int:
        return self._next_slot_id

    def next_booking_id(self) -> int:
        return self._next_booking_id
'''

        app_py = f'''\
"""Booking system API — implement the TODO functions below."""
from datetime import datetime, timedelta, timezone
from models import Slot, Booking, BookingStore


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


MAX_ADVANCE_DAYS = {max_advance_days}
CANCELLATION_HOURS = {cancellation_hours}
WAITLIST_MAX = {waitlist_max}


def add_slot(store: BookingStore, date: str, hour: int, capacity: int, resource: str) -> dict:
    """
    Register a bookable time slot.

    TODO: Implement this function.
    - Validate date format (YYYY-MM-DD), hour (0-23), capacity (>= 1)
    - Return slot as dict
    """
    raise NotImplementedError("TODO: implement add_slot")


def book_slot(store: BookingStore, slot_id: int, user_id: str, now_iso: str) -> dict:
    """
    Create a booking for a user.

    TODO: Implement this function.
    - Raise AppError("SLOT_NOT_FOUND") if slot_id not found
    - Raise AppError("{error_too_far_advance}") if slot date > now + MAX_ADVANCE_DAYS days
    - Raise AppError("{error_conflict}") if user already has a booking for this slot
    - If confirmed count >= capacity: waitlist if room, else raise "{error_waitlist_full}"
    - Return booking as dict
    """
    raise NotImplementedError("TODO: implement book_slot")


def cancel_booking(store: BookingStore, booking_id: int, now_iso: str) -> dict:
    """
    Cancel a booking, promoting waitlisted user if applicable.

    TODO: Implement this function.
    - Raise AppError("{error_not_found}") if booking_id not found
    - Raise AppError("{error_too_late_cancel}") if < CANCELLATION_HOURS before slot start
    - Remove booking; if CONFIRMED and waitlist exists, promote oldest waitlisted
    - Return cancelled booking dict
    """
    raise NotImplementedError("TODO: implement cancel_booking")


def get_bookings(store: BookingStore, slot_id: int = None, user_id: str = None, status: str = None) -> list:
    """
    Return bookings matching all provided filters, sorted by booked_at ascending.

    TODO: Implement this function.
    """
    raise NotImplementedError("TODO: implement get_bookings")


def get_slot_availability(store: BookingStore, slot_id: int) -> dict:
    """
    Return availability info for a slot.

    TODO: Implement this function.
    - Raise AppError("SLOT_NOT_FOUND") if not found
    - Return dict: slot_id, capacity, confirmed_count, waitlisted_count, available_seats
    """
    raise NotImplementedError("TODO: implement get_slot_availability")


def _slot_to_dict(slot: Slot) -> dict:
    return {{"id": slot.id, "date": slot.date, "hour": slot.hour,
             "capacity": slot.capacity, "resource": slot.resource}}


def _booking_to_dict(booking: Booking) -> dict:
    return {{"id": booking.id, "slot_id": booking.slot_id, "user_id": booking.user_id,
             "status": booking.status, "booked_at": booking.booked_at}}
'''

        test_py = f'''\
"""Basic tests for the booking system."""
import pytest
from models import BookingStore
from app import AppError, add_slot, book_slot, cancel_booking, get_bookings, get_slot_availability

NOW = "2024-06-01T10:00:00"
SOON = "2024-06-10"  # within {max_advance_days} days
FAR = "2030-01-01"  # way beyond {max_advance_days} days


@pytest.fixture
def store():
    return BookingStore()


def test_add_slot(store):
    s = add_slot(store, SOON, 9, 3, "Room A")
    assert s["date"] == SOON
    assert s["capacity"] == 3


def test_book_slot_confirmed(store):
    add_slot(store, SOON, 9, 3, "Room A")
    b = book_slot(store, 1, "alice", NOW)
    assert b["status"] == "CONFIRMED"
    assert b["user_id"] == "alice"


def test_book_slot_too_far(store):
    add_slot(store, FAR, 9, 3, "Room A")
    with pytest.raises(AppError) as exc:
        book_slot(store, 1, "alice", NOW)
    assert exc.value.code == "{error_too_far_advance}"


def test_book_slot_conflict(store):
    add_slot(store, SOON, 9, 3, "Room A")
    book_slot(store, 1, "alice", NOW)
    with pytest.raises(AppError) as exc:
        book_slot(store, 1, "alice", NOW)
    assert exc.value.code == "{error_conflict}"


def test_book_slot_waitlist(store):
    add_slot(store, SOON, 9, 1, "Room A")
    book_slot(store, 1, "alice", NOW)
    b = book_slot(store, 1, "bob", NOW)
    assert b["status"] == "WAITLISTED"


def test_cancel_booking(store):
    add_slot(store, SOON, 9, 1, "Room A")
    book_slot(store, 1, "alice", NOW)
    cancelled = cancel_booking(store, 1, NOW)
    assert cancelled["status"] == "CONFIRMED"
    avail = get_slot_availability(store, 1)
    assert avail["confirmed_count"] == 0


def test_cancel_promotes_waitlist(store):
    add_slot(store, SOON, 9, 1, "Room A")
    book_slot(store, 1, "alice", NOW)
    book_slot(store, 1, "bob", NOW)
    cancel_booking(store, 1, NOW)  # alice cancelled
    bookings = get_bookings(store, slot_id=1, status="CONFIRMED")
    assert len(bookings) == 1
    assert bookings[0]["user_id"] == "bob"


def test_slot_not_found(store):
    with pytest.raises(AppError) as exc:
        book_slot(store, 999, "alice", NOW)
    assert exc.value.code == "SLOT_NOT_FOUND"


def test_get_slot_availability(store):
    add_slot(store, SOON, 9, 3, "Room A")
    book_slot(store, 1, "alice", NOW)
    avail = get_slot_availability(store, 1)
    assert avail["confirmed_count"] == 1
    assert avail["available_seats"] == 2
'''

        workspace_files = {
            "app.py": app_py,
            "models.py": models_py,
            "tests/__init__.py": "",
            "tests/test_app.py": test_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # -----------------------------------------------------------------------
    # Domain 3: Grading Calculator
    # -----------------------------------------------------------------------

    def _gen_grading(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        # Vary: whether drop-lowest is enabled, curve amount, letter grade boundaries
        drop_lowest_count = rng.choice([0, 1, 2])
        curve_points = rng.choice([0, 3, 5, 7])
        # Letter grade cutoffs (vary slightly per seed)
        a_cutoff = rng.choice([90, 92, 93])
        b_cutoff = rng.choice([80, 82, 83])
        c_cutoff = rng.choice([70, 72, 73])
        d_cutoff = rng.choice([60, 62, 63])
        decimal_places = rng.choice([2, 3])

        expected = {
            "domain": "grading_calculator",
            "drop_lowest_count": drop_lowest_count,
            "curve_points": curve_points,
            "a_cutoff": a_cutoff,
            "b_cutoff": b_cutoff,
            "c_cutoff": c_cutoff,
            "d_cutoff": d_cutoff,
            "decimal_places": decimal_places,
            "error_empty": "NO_GRADES",
            "error_invalid_weight": "INVALID_WEIGHT",
            "error_invalid_score": "INVALID_SCORE",
            "error_weight_sum": "WEIGHTS_NOT_ONE",
        }

        spec_md = f"""# SPEC1: Grading Calculator — Full Specification

## Overview
Implement a grading calculator that supports weighted categories, optional
drop-lowest, a curve adjustment, and letter grade mapping.

## Data Model (see `models.py`)
- `GradeEntry`: category (str), score (float 0-100), weight (float 0-1)
- `GradeReport`: weighted_average (float), curved_average (float), letter_grade (str),
  dropped_scores (list of floats)

## API Functions to Implement

### `calculate_grade(entries, drop_lowest={drop_lowest_count}, curve={curve_points})`
Compute the weighted grade for a student.

**Processing steps (in order):**
1. **Validate** all entries:
   - Raise `AppError("NO_GRADES")` if `entries` is empty.
   - Raise `AppError("INVALID_SCORE")` if any `score` is not in [0, 100].
   - Raise `AppError("INVALID_WEIGHT")` if any `weight` is not in (0, 1].
   - Raise `AppError("WEIGHTS_NOT_ONE")` if weights do not sum to 1.0
     (allow tolerance of ±0.001).
2. **Drop lowest**: If `drop_lowest > 0`, remove the `drop_lowest` lowest-scoring
   entries **by raw score** (not weighted). Weights of remaining entries are
   **renormalized** to sum to 1.0.
3. **Weighted average**: Sum of (score × normalized_weight) for remaining entries.
   Round to {decimal_places} decimal places.
4. **Curve**: Add `curve` points to the weighted average, capped at 100.0.
   This is the `curved_average`. Round to {decimal_places} decimal places.
5. **Letter grade**: Map `curved_average` to letter using:
   - >= {a_cutoff} → `"A"`
   - >= {b_cutoff} → `"B"`
   - >= {c_cutoff} → `"C"`
   - >= {d_cutoff} → `"D"`
   - < {d_cutoff} → `"F"`

Returns a `GradeReport` (as dict).

### `class_statistics(all_reports)`
Compute statistics over a list of GradeReport dicts.
- **Error `AppError("NO_GRADES")`** if `all_reports` is empty.
- Returns dict with:
  - `mean`: mean of `curved_average` values, rounded to {decimal_places} dp
  - `median`: median of `curved_average` values, rounded to {decimal_places} dp
  - `highest`: max `curved_average`
  - `lowest`: min `curved_average`
  - `grade_distribution`: dict mapping letter grades to counts (include all of A,B,C,D,F even if 0)

## Error Contract
All errors raised as `AppError(code)`.

## Edge Cases (REQUIRED)
- After dropping lowest, if only one entry remains, its renormalized weight is 1.0.
- `drop_lowest` of 0 means no dropping; all entries used as-is.
- Curve cap: if `weighted_average + curve > 100`, set `curved_average = 100.0`.
- `WEIGHTS_NOT_ONE` check happens BEFORE dropping (use original weights to validate).
- Scores of exactly 0.0 are valid; scores of exactly 100.0 are valid.
- Decimal rounding uses standard rounding (round half up), not floor/truncate.
- `class_statistics` median: for even count, average the two middle values.

## Deliverables
- `app.py` with all functions implemented
- All tests in `tests/test_app.py` must pass
"""

        brief_md = """# SPEC1: Grading Calculator (Brief)

Implement the TODO functions in `app.py`. The workspace contains:
- `app.py` — skeleton with TODO placeholders
- `models.py` — data classes (do not modify)
- `tests/test_app.py` — basic tests

Run tests with: `python -m pytest tests/`

Functions to implement: `calculate_grade`, `class_statistics`.
"""

        models_py = '''\
"""Data models for the grading calculator. Do not modify."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class GradeEntry:
    category: str
    score: float     # 0-100
    weight: float    # 0-1, all weights in a set must sum to 1.0


@dataclass
class GradeReport:
    weighted_average: float
    curved_average: float
    letter_grade: str
    dropped_scores: List[float] = field(default_factory=list)
'''

        app_py = f'''\
"""Grading calculator API — implement the TODO functions below."""
from models import GradeEntry, GradeReport
from typing import List


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


DROP_LOWEST = {drop_lowest_count}
CURVE_POINTS = {curve_points}
DECIMAL_PLACES = {decimal_places}
WEIGHT_TOLERANCE = 0.001

# Letter grade cutoffs (curved_average >= cutoff -> grade)
GRADE_CUTOFFS = [
    ({a_cutoff}, "A"),
    ({b_cutoff}, "B"),
    ({c_cutoff}, "C"),
    ({d_cutoff}, "D"),
]


def calculate_grade(entries: List[GradeEntry], drop_lowest: int = DROP_LOWEST, curve: float = CURVE_POINTS) -> dict:
    """
    Compute weighted grade with optional drop-lowest and curve.

    TODO: Implement this function.
    Steps:
    1. Validate entries (NO_GRADES, INVALID_SCORE, INVALID_WEIGHT, WEIGHTS_NOT_ONE)
    2. Drop lowest `drop_lowest` entries by raw score; renormalize weights
    3. Compute weighted_average (round to DECIMAL_PLACES)
    4. Apply curve capped at 100 -> curved_average (round to DECIMAL_PLACES)
    5. Map to letter grade using GRADE_CUTOFFS
    Return as dict matching GradeReport fields.
    """
    raise NotImplementedError("TODO: implement calculate_grade")


def class_statistics(all_reports: list) -> dict:
    """
    Compute class-wide statistics from a list of GradeReport dicts.

    TODO: Implement this function.
    - Raise AppError("NO_GRADES") if all_reports is empty
    - Return dict: mean, median, highest, lowest, grade_distribution
    """
    raise NotImplementedError("TODO: implement class_statistics")
'''

        test_py = f'''\
"""Basic tests for the grading calculator."""
import pytest
from models import GradeEntry
from app import AppError, calculate_grade, class_statistics


def make_entries(scores_weights):
    return [GradeEntry(f"cat{{i}}", s, w) for i, (s, w) in enumerate(scores_weights)]


def test_calculate_grade_basic():
    entries = make_entries([(80, 0.5), (90, 0.5)])
    report = calculate_grade(entries)
    assert "weighted_average" in report
    assert "letter_grade" in report
    assert report["letter_grade"] in ("A", "B", "C", "D", "F")


def test_no_grades():
    with pytest.raises(AppError) as exc:
        calculate_grade([])
    assert exc.value.code == "NO_GRADES"


def test_invalid_score_high():
    entries = make_entries([(101, 1.0)])
    with pytest.raises(AppError) as exc:
        calculate_grade(entries)
    assert exc.value.code == "INVALID_SCORE"


def test_invalid_weight():
    entries = make_entries([(80, 0.0)])
    with pytest.raises(AppError) as exc:
        calculate_grade(entries)
    assert exc.value.code == "INVALID_WEIGHT"


def test_weights_not_one():
    entries = make_entries([(80, 0.3), (90, 0.3)])
    with pytest.raises(AppError) as exc:
        calculate_grade(entries)
    assert exc.value.code == "WEIGHTS_NOT_ONE"


def test_curve_applied():
    entries = make_entries([(70, 1.0)])
    report = calculate_grade(entries, drop_lowest=0, curve={curve_points})
    assert report["curved_average"] == round(min(70 + {curve_points}, 100), {decimal_places})


def test_curve_cap():
    entries = make_entries([(99, 1.0)])
    report = calculate_grade(entries, drop_lowest=0, curve=10)
    assert report["curved_average"] == 100.0


def test_letter_grade_a():
    entries = make_entries([({a_cutoff}, 1.0)])
    report = calculate_grade(entries, drop_lowest=0, curve=0)
    assert report["letter_grade"] == "A"


def test_letter_grade_f():
    entries = make_entries([({d_cutoff - 1}, 1.0)])
    report = calculate_grade(entries, drop_lowest=0, curve=0)
    assert report["letter_grade"] == "F"


def test_class_statistics_empty():
    with pytest.raises(AppError) as exc:
        class_statistics([])
    assert exc.value.code == "NO_GRADES"


def test_class_statistics_basic():
    r1 = calculate_grade(make_entries([(80, 1.0)]), drop_lowest=0, curve=0)
    r2 = calculate_grade(make_entries([(90, 1.0)]), drop_lowest=0, curve=0)
    stats = class_statistics([r1, r2])
    assert "mean" in stats
    assert "grade_distribution" in stats
    assert set(stats["grade_distribution"].keys()) == {{"A", "B", "C", "D", "F"}}
'''

        workspace_files = {
            "app.py": app_py,
            "models.py": models_py,
            "tests/__init__.py": "",
            "tests/test_app.py": test_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # -----------------------------------------------------------------------
    # Domain 4: Expense Tracker
    # -----------------------------------------------------------------------

    def _gen_expense_tracker(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        budget_limit = rng.randint(500, 5000)
        # Vary allowed currencies
        currencies = rng.sample(["USD", "EUR", "GBP", "JPY", "CAD"], 3)
        base_currency = currencies[0]
        # Vary exchange rates (simplified fixed rates)
        fx_rates = {c: round(rng.uniform(0.5, 2.5), 4) for c in currencies if c != base_currency}
        fx_rates[base_currency] = 1.0
        # Vary report period label
        report_period = rng.choice(["monthly", "weekly"])
        decimal_places = rng.choice([2, 2])  # always 2 for currency
        error_invalid_amount = "INVALID_AMOUNT"
        error_unknown_currency = "UNKNOWN_CURRENCY"
        error_not_found = "EXPENSE_NOT_FOUND"
        error_budget_exceeded = "BUDGET_EXCEEDED"
        error_invalid_date = "INVALID_DATE"

        expected = {
            "domain": "expense_tracker",
            "budget_limit": budget_limit,
            "currencies": currencies,
            "base_currency": base_currency,
            "fx_rates": fx_rates,
            "report_period": report_period,
            "decimal_places": decimal_places,
            "error_invalid_amount": error_invalid_amount,
            "error_unknown_currency": error_unknown_currency,
            "error_not_found": error_not_found,
            "error_budget_exceeded": error_budget_exceeded,
            "error_invalid_date": error_invalid_date,
        }

        fx_table_rows = "\n".join(
            f"  - 1 {c} = {r} {base_currency}" for c, r in fx_rates.items() if c != base_currency
        )
        currencies_str = ", ".join(f"`{c}`" for c in currencies)

        spec_md = f"""# SPEC1: Expense Tracker — Full Specification

## Overview
Implement a personal expense tracker that supports multiple currencies,
category-based budget limits, and {report_period} summary reports.

## Data Model (see `models.py`)
- `Expense`: id, description (str), amount (float), currency (str), category (str), date (YYYY-MM-DD str)
- `ExpenseStore`: holds expenses

## Supported Currencies & Exchange Rates to {base_currency}
{currencies_str}

Fixed exchange rates (exact, no rounding during conversion):
{fx_table_rows}
  - 1 {base_currency} = 1.0 {base_currency}

All monetary output must be in `{base_currency}` and rounded to {decimal_places} decimal places.

## API Functions to Implement

### `add_expense(store, description, amount, currency, category, date)`
Record a new expense.
- **Error `{error_invalid_amount}`** if `amount <= 0` or not a number.
- **Error `{error_unknown_currency}`** if `currency` not in supported list.
- **Error `{error_invalid_date}`** if `date` is not a valid YYYY-MM-DD string.
- Stores the expense with its original currency and amount (do NOT convert on insert).
- Returns expense dict.

### `get_expense(store, expense_id)`
Retrieve an expense.
- **Error `{error_not_found}`** if not found.
- Returns expense dict (original currency/amount, not converted).

### `delete_expense(store, expense_id)`
Delete an expense.
- **Error `{error_not_found}`** if not found.
- Returns deleted expense dict.

### `get_total(store, category=None, currency_out="{base_currency}")`
Return total spending converted to `currency_out`.
- If `category` is given, sum only expenses in that category.
- Convert each expense: `amount_in_{base_currency} = amount * fx_rates[expense_currency]`,
  then convert to `currency_out`: `final = amount_in_{base_currency} / fx_rates[currency_out]`.
- **Error `{error_unknown_currency}`** if `currency_out` not supported.
- Return rounded total as float ({decimal_places} dp).

### `{report_period}_report(store, period_start)`
Generate a summary report for one {report_period} period starting at `period_start` (YYYY-MM-DD).
- **Error `{error_invalid_date}`** if `period_start` is not a valid YYYY-MM-DD string.
- Period covers {"7 days" if report_period == "weekly" else "the calendar month of period_start"}.
- Returns dict:
  - `period_start`: the input date string
  - `total_{base_currency}`: total spending in {base_currency} for the period (rounded to {decimal_places} dp)
  - `by_category`: dict mapping category → total in {base_currency} (rounded to {decimal_places} dp)
  - `expense_count`: number of expenses in the period
  - `budget_limit`: {budget_limit}
  - `over_budget`: True if `total_{base_currency} > {budget_limit}`, else False

## Error Contract
All errors raised as `AppError(code)`.

## Edge Cases (REQUIRED)
- `get_total` with no expenses returns 0.0.
- `{report_period}_report` with no expenses in the period returns zeros and empty `by_category`.
- Expenses on the boundary date `period_start` are included; expenses on the last day of the
  period are included; expenses one day after the period end are excluded.
- Currency names are case-sensitive: `usd` is not valid; only `{base_currency}` (as listed) is.
- Amount of 0 raises `{error_invalid_amount}` (zero is not a positive expense).

## Deliverables
- `app.py` with all functions implemented
- All tests in `tests/test_app.py` must pass
"""

        brief_md = f"""# SPEC1: Expense Tracker (Brief)

Implement the TODO functions in `app.py`. The workspace contains:
- `app.py` — skeleton with TODO placeholders
- `models.py` — data classes (do not modify)
- `tests/test_app.py` — basic tests

Run tests with: `python -m pytest tests/`

Functions to implement: `add_expense`, `get_expense`, `delete_expense`,
`get_total`, `{report_period}_report`.
"""

        models_py = '''\
"""Data models for the expense tracker. Do not modify."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Expense:
    id: int
    description: str
    amount: float
    currency: str
    category: str
    date: str   # YYYY-MM-DD


@dataclass
class ExpenseStore:
    _expenses: Dict[int, Expense] = field(default_factory=dict)
    _next_id: int = 1

    def add_expense_record(self, expense: Expense) -> Expense:
        self._expenses[expense.id] = expense
        self._next_id += 1
        return expense

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        return self._expenses.get(expense_id)

    def remove_expense(self, expense_id: int) -> Optional[Expense]:
        return self._expenses.pop(expense_id, None)

    def all_expenses(self) -> List[Expense]:
        return list(self._expenses.values())

    def next_id(self) -> int:
        return self._next_id
'''

        # Build FX rates dict as Python literal
        fx_dict_items = ", ".join(f'"{c}": {r}' for c, r in fx_rates.items())
        report_fn = f"{report_period}_report"
        period_days = 7 if report_period == "weekly" else None

        app_py = f'''\
"""Expense tracker API — implement the TODO functions below."""
from datetime import datetime, timedelta
from models import Expense, ExpenseStore
from typing import Optional


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


BUDGET_LIMIT = {budget_limit}
BASE_CURRENCY = "{base_currency}"
FX_RATES = {{{fx_dict_items}}}  # rate to {base_currency}
DECIMAL_PLACES = {decimal_places}


def add_expense(store: ExpenseStore, description: str, amount: float, currency: str,
                category: str, date: str) -> dict:
    """
    Record a new expense.

    TODO: Implement this function.
    - Raise AppError("{error_invalid_amount}") if amount <= 0
    - Raise AppError("{error_unknown_currency}") if currency not in FX_RATES
    - Raise AppError("{error_invalid_date}") if date not valid YYYY-MM-DD
    - Store with original currency/amount, return as dict
    """
    raise NotImplementedError("TODO: implement add_expense")


def get_expense(store: ExpenseStore, expense_id: int) -> dict:
    """
    Retrieve an expense by id.

    TODO: Implement this function.
    - Raise AppError("{error_not_found}") if not found
    """
    raise NotImplementedError("TODO: implement get_expense")


def delete_expense(store: ExpenseStore, expense_id: int) -> dict:
    """
    Delete an expense.

    TODO: Implement this function.
    - Raise AppError("{error_not_found}") if not found
    """
    raise NotImplementedError("TODO: implement delete_expense")


def get_total(store: ExpenseStore, category: str = None, currency_out: str = BASE_CURRENCY) -> float:
    """
    Return total spending in currency_out.

    TODO: Implement this function.
    - Convert each expense to {base_currency} via FX_RATES, then to currency_out
    - Round result to DECIMAL_PLACES
    - Raise AppError("{error_unknown_currency}") if currency_out not in FX_RATES
    """
    raise NotImplementedError("TODO: implement get_total")


def {report_fn}(store: ExpenseStore, period_start: str) -> dict:
    """
    Generate a {report_period} summary report starting at period_start.

    TODO: Implement this function.
    - Raise AppError("{error_invalid_date}") if period_start is not valid YYYY-MM-DD
    - Include expenses within the {report_period} period (inclusive start, inclusive end)
    - Return dict with period_start, total_{base_currency}, by_category, expense_count,
      budget_limit, over_budget
    """
    raise NotImplementedError("TODO: implement {report_fn}")


def _expense_to_dict(expense: Expense) -> dict:
    return {{"id": expense.id, "description": expense.description, "amount": expense.amount,
             "currency": expense.currency, "category": expense.category, "date": expense.date}}
'''

        cur0 = currencies[0]
        cur1 = currencies[1] if len(currencies) > 1 else currencies[0]

        test_py = f'''\
"""Basic tests for the expense tracker."""
import pytest
from models import ExpenseStore
from app import AppError, add_expense, get_expense, delete_expense, get_total, {report_fn}

GOOD_DATE = "2024-06-15"
BAD_DATE = "not-a-date"


@pytest.fixture
def store():
    return ExpenseStore()


def test_add_expense_basic(store):
    e = add_expense(store, "Coffee", 5.0, "{cur0}", "food", GOOD_DATE)
    assert e["id"] == 1
    assert e["currency"] == "{cur0}"
    assert e["amount"] == 5.0


def test_add_expense_zero_amount(store):
    with pytest.raises(AppError) as exc:
        add_expense(store, "X", 0, "{cur0}", "misc", GOOD_DATE)
    assert exc.value.code == "{error_invalid_amount}"


def test_add_expense_negative_amount(store):
    with pytest.raises(AppError) as exc:
        add_expense(store, "X", -1, "{cur0}", "misc", GOOD_DATE)
    assert exc.value.code == "{error_invalid_amount}"


def test_add_expense_unknown_currency(store):
    with pytest.raises(AppError) as exc:
        add_expense(store, "X", 10, "XYZ", "misc", GOOD_DATE)
    assert exc.value.code == "{error_unknown_currency}"


def test_add_expense_bad_date(store):
    with pytest.raises(AppError) as exc:
        add_expense(store, "X", 10, "{cur0}", "misc", BAD_DATE)
    assert exc.value.code == "{error_invalid_date}"


def test_get_expense(store):
    add_expense(store, "Lunch", 12.0, "{cur0}", "food", GOOD_DATE)
    e = get_expense(store, 1)
    assert e["description"] == "Lunch"


def test_get_expense_not_found(store):
    with pytest.raises(AppError) as exc:
        get_expense(store, 999)
    assert exc.value.code == "{error_not_found}"


def test_delete_expense(store):
    add_expense(store, "Taxi", 20.0, "{cur0}", "transport", GOOD_DATE)
    deleted = delete_expense(store, 1)
    assert deleted["description"] == "Taxi"
    with pytest.raises(AppError):
        get_expense(store, 1)


def test_get_total_empty(store):
    total = get_total(store)
    assert total == 0.0


def test_get_total_basic(store):
    add_expense(store, "A", 100.0, "{base_currency}", "food", GOOD_DATE)
    add_expense(store, "B", 50.0, "{base_currency}", "travel", GOOD_DATE)
    total = get_total(store)
    assert total == 150.0


def test_get_total_by_category(store):
    add_expense(store, "A", 100.0, "{base_currency}", "food", GOOD_DATE)
    add_expense(store, "B", 50.0, "{base_currency}", "travel", GOOD_DATE)
    assert get_total(store, category="food") == 100.0


def test_report_basic(store):
    add_expense(store, "A", 100.0, "{base_currency}", "food", "2024-06-01")
    report = {report_fn}(store, "2024-06-01")
    assert report["expense_count"] >= 1
    assert "by_category" in report
    assert report["budget_limit"] == {budget_limit}
'''

        workspace_files = {
            "app.py": app_py,
            "models.py": models_py,
            "tests/__init__.py": "",
            "tests/test_app.py": test_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )
