# P8: Access Control Policy Fix (Brief)

Fix `rbac_policy.yaml` based on the compliance scan in `compliance_report.md`.

6 findings are listed — but only 4 are real violations. The other 2 are approved
exceptions documented in `exceptions.md` that must NOT be changed.

Fix: remove the 4 violating permissions. Preserve: the 2 exception permissions.

Run `python3 test_rbac.py` to verify. Only modify `rbac_policy.yaml`.
