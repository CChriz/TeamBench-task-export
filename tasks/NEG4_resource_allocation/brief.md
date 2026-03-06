# NEG4: Resource Allocation (Brief)

Fix 3 fairness bugs in `allocator.py`: priority inversion, starvation of low-priority teams, and wrong quota calculation.

Three teams share a compute budget defined in `budget.yaml`.

Run `python3 test_allocator.py` to verify. Only modify `allocator.py`.
