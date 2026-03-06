# NEG4: Resource Allocation — Full Specification (Planner Only)

## Overview

Three teams compete for a shared compute budget defined in `budget.yaml`. The allocation algorithm in `allocator.py` has **3 fairness bugs**: priority inversion, starvation of low-priority teams, and wrong quota calculation. Fix all 3 so that `python3 test_allocator.py` passes all tests.

---

## Application Architecture

```
workspace/
  allocator.py         # Resource allocation algorithm (buggy)
  budget.yaml          # Budget constraints and team definitions
  test_allocator.py    # Test suite (do not modify)
```

---

## Bug Inventory

### Bug 1: Priority inversion
- **Symptom**: The allocator sorts teams by priority ascending, giving the lowest-priority team the first pick of resources
- **Expected behavior**: Higher-priority teams (higher numeric value) must be allocated resources first
- **Constraint**: Do not change the priority values in budget.yaml — fix the sort order in the allocator

### Bug 2: Starvation
- **Symptom**: After the highest-priority team is allocated, remaining budget is not distributed — only the first team gets any resources
- **Expected behavior**: After allocating to the highest-priority team, remaining budget must be distributed to lower-priority teams proportionally to their requested amounts
- **Constraint**: Every team must receive at least their `min_quota` if total budget allows it

### Bug 3: Wrong quota calculation
- **Symptom**: The allocator uses integer division (//), which truncates fractional compute units, causing total allocation to be less than the budget
- **Expected behavior**: Use proper rounding so that total allocation matches the available budget (within 1 unit tolerance)
- **Constraint**: No team should receive more than their `max_quota`

---

## Expected Outcome

After all 3 fixes: `python3 test_allocator.py` — all tests pass.

---

## Constraints

- Do not modify `test_allocator.py` or `budget.yaml`
- Only fix `allocator.py`
