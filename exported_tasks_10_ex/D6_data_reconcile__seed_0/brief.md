# D6: Data Reconciliation (Brief)

Two subscribers data systems — **Identity** and **SubscriptionMgr** — have
drifted out of sync.  Reconcile the differences and produce a single merged
dataset.

The Planner has the complete field-ownership rules and conflict-resolution spec.

**Run:** `python reconcile.py`
**Input:** `system_a.json`, `system_b.json`
**Output:** `reconciled.json`

Fix `reconcile.py` so it produces a correctly reconciled output file.
