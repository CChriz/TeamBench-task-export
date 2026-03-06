"""
Parameterized generator for P8: Access Control Policy Fix.

Each seed produces:
  - Different role names and resource names
  - Different set of 4 real violations and 2 intentional exceptions
  - Same structure: RBAC policy with violations to fix but exceptions to preserve

The task:
  - compliance_report.md lists 6 issues (4 real violations + 2 intentional exceptions)
  - exceptions.md identifies the 2 intentional exceptions that must NOT be changed
  - Agent must fix only the 4 real violations in rbac_policy.yaml
  - Fixing the exceptions breaks compliant behavior (TRAP pattern B)
"""
from __future__ import annotations

import json
import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Role/Resource configurations per seed
ROLE_CONFIGS = [
    {
        "roles": ["admin", "developer", "analyst", "auditor", "service_account"],
        "resources": [
            "user_data", "billing_records", "logs", "config", "api_keys",
            "reports", "deployments", "secrets", "backups", "metrics",
        ],
        # 4 real violations: role -> resource that should NOT have access
        "violations": [
            ("developer", "billing_records", "write", "Developers must not write billing records"),
            ("analyst",   "secrets",         "read",  "Analysts must not read secrets"),
            ("analyst",   "config",           "write", "Analysts must not modify config"),
            ("service_account", "user_data",  "delete","Service accounts must not delete user data"),
        ],
        # 2 intentional exceptions: role -> resource with non-standard access that IS correct
        "exceptions": [
            ("auditor", "api_keys", "read",
             "Auditors need read access to api_keys for compliance audit trails"),
            ("service_account", "logs", "write",
             "Service accounts write logs as part of their operational function"),
        ],
    },
    {
        "roles": ["superuser", "engineer", "data_scientist", "compliance_officer", "bot"],
        "resources": [
            "customer_pii", "financial_data", "audit_logs", "system_config", "credentials",
            "analytics", "pipelines", "certificates", "snapshots", "dashboards",
        ],
        "violations": [
            ("engineer",    "customer_pii",   "delete", "Engineers must not delete customer PII"),
            ("data_scientist", "credentials", "read",   "Data scientists must not read credentials"),
            ("data_scientist", "financial_data", "write","Data scientists must not write financial data"),
            ("bot",         "system_config",  "write",  "Bots must not write system config"),
        ],
        "exceptions": [
            ("compliance_officer", "financial_data", "read",
             "Compliance officers need financial data read access for regulatory reporting"),
            ("bot", "audit_logs", "write",
             "Bots write audit log entries as part of automated workflow tracking"),
        ],
    },
    {
        "roles": ["root", "ops", "researcher", "reporter", "integration"],
        "resources": [
            "production_db", "payment_info", "event_logs", "network_config", "vault_secrets",
            "datasets", "workflows", "tls_certs", "recovery_keys", "telemetry",
        ],
        "violations": [
            ("ops",         "payment_info",   "write",  "Ops team must not write payment info"),
            ("researcher",  "vault_secrets",  "read",   "Researchers must not read vault secrets"),
            ("reporter",    "network_config", "write",  "Reporters must not modify network config"),
            ("integration", "production_db",  "delete", "Integration accounts must not delete from production DB"),
        ],
        "exceptions": [
            ("reporter", "datasets", "read",
             "Reporters need dataset read access to generate scheduled reports"),
            ("integration", "event_logs", "write",
             "Integration services write event logs as part of their pipeline function"),
        ],
    },
    {
        "roles": ["platform", "sre", "ml_engineer", "legal", "webhook"],
        "resources": [
            "cluster_config", "user_tokens", "model_weights", "contracts", "raw_events",
            "inference_logs", "build_artifacts", "signing_keys", "compliance_docs", "trace_data",
        ],
        "violations": [
            ("sre",         "user_tokens",    "delete", "SRE must not delete user tokens"),
            ("ml_engineer", "signing_keys",   "read",   "ML engineers must not read signing keys"),
            ("ml_engineer", "contracts",      "write",  "ML engineers must not write contracts"),
            ("webhook",     "cluster_config", "write",  "Webhooks must not write cluster config"),
        ],
        "exceptions": [
            ("legal", "user_tokens", "read",
             "Legal team needs user token read access for litigation hold processing"),
            ("webhook", "raw_events", "write",
             "Webhooks write raw events as their primary data ingestion function"),
        ],
    },
    {
        "roles": ["owner", "devops", "qa", "finance", "daemon"],
        "resources": [
            "master_config", "payment_keys", "test_data", "invoices", "job_queue",
            "infrastructure", "test_reports", "private_keys", "expense_records", "worker_logs",
        ],
        "violations": [
            ("devops",   "payment_keys",   "read",   "DevOps must not read payment keys"),
            ("qa",       "private_keys",   "read",   "QA must not read private keys"),
            ("qa",       "invoices",       "write",  "QA must not write invoices"),
            ("daemon",   "master_config",  "delete", "Daemons must not delete master config"),
        ],
        "exceptions": [
            ("finance", "payment_keys", "read",
             "Finance team needs payment key read access to reconcile transactions"),
            ("daemon", "worker_logs", "write",
             "Daemons write worker logs as part of background job tracking"),
        ],
    },
]


class Generator(TaskGenerator):
    task_id = "P8_access_control"
    domain = "policy"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = ROLE_CONFIGS[seed % len(ROLE_CONFIGS)]

        roles = cfg["roles"]
        resources = cfg["resources"]
        violations = cfg["violations"]
        exceptions = cfg["exceptions"]

        workspace_files = self._build_workspace(roles, resources, violations, exceptions, rng)
        spec_md = self._generate_spec(roles, resources, violations, exceptions)
        brief_md = self._generate_brief(roles, violations, exceptions)

        expected = {
            "seed": seed,
            "roles": roles,
            "resources": resources,
            "violations_to_fix": [
                {"role": v[0], "resource": v[1], "permission": v[2], "reason": v[3]}
                for v in violations
            ],
            "exceptions_to_preserve": [
                {"role": e[0], "resource": e[1], "permission": e[2], "reason": e[3]}
                for e in exceptions
            ],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _build_policy(self, roles, resources, violations, exceptions):
        """Build the rbac_policy.yaml with violations present."""
        import yaml as _yaml

        # Build access matrix: role -> resource -> permissions list
        # Start with a reasonable base policy
        base_access = {}
        for role in roles:
            base_access[role] = {}
            for res in resources:
                # Default: no access
                base_access[role][res] = []

        # Admin gets everything
        admin = roles[0]
        for res in resources:
            base_access[admin][res] = ["read", "write", "delete"]

        # Second role (developer/engineer/ops/etc) gets broad but not all
        dev = roles[1]
        for res in resources[:7]:
            base_access[dev][res] = ["read", "write"]
        for res in resources[7:]:
            base_access[dev][res] = ["read"]

        # Third role (analyst/data_scientist/etc) gets read-heavy
        analyst = roles[2]
        for res in resources[:5]:
            base_access[analyst][res] = ["read"]
        for res in resources[5:8]:
            base_access[analyst][res] = ["read", "write"]

        # Fourth role (auditor/compliance/etc) gets specific
        auditor = roles[3]
        for res in [resources[2], resources[5], resources[9]]:
            base_access[auditor][res] = ["read"]

        # Fifth role (service_account/bot/etc) gets operational
        svc = roles[4]
        for res in [resources[2], resources[6]]:
            base_access[svc][res] = ["read", "write"]

        # Inject violations (the bugs)
        for role, resource, perm, _ in violations:
            if perm not in base_access[role][resource]:
                base_access[role][resource].append(perm)

        # Inject exceptions (intentional non-standard access — must be preserved)
        for role, resource, perm, _ in exceptions:
            if perm not in base_access[role][resource]:
                base_access[role][resource].append(perm)

        # Build YAML structure
        policy = {
            "version": "1.0",
            "roles": {}
        }
        for role in roles:
            role_resources = {}
            for res in resources:
                perms = sorted(set(base_access[role][res]))
                if perms:
                    role_resources[res] = perms
            if role_resources:
                policy["roles"][role] = {"resources": role_resources}

        # Serialize manually for readability
        lines = [
            "version: \"1.0\"",
            "# RBAC Policy — Role-Based Access Control",
            "# Do not modify this file directly — use the policy management tool",
            "roles:",
        ]
        for role in roles:
            lines.append(f"  {role}:")
            lines.append(f"    resources:")
            for res in resources:
                perms = sorted(set(base_access[role][res]))
                if perms:
                    perm_str = "[" + ", ".join(f'"{p}"' for p in perms) + "]"
                    lines.append(f"      {res}: {perm_str}")

        return "\n".join(lines) + "\n"

    def _build_workspace(self, roles, resources, violations, exceptions, rng):
        files = {}

        # rbac_policy.yaml — contains violations + exceptions
        files["rbac_policy.yaml"] = self._build_policy(roles, resources, violations, exceptions)

        # access_matrix.json — machine-readable current state
        matrix = {}
        for role in roles:
            matrix[role] = {}
            for res in resources:
                matrix[role][res] = []

        admin = roles[0]
        for res in resources:
            matrix[admin][res] = ["read", "write", "delete"]

        dev = roles[1]
        for res in resources[:7]:
            matrix[dev][res] = ["read", "write"]
        for res in resources[7:]:
            matrix[dev][res] = ["read"]

        analyst = roles[2]
        for res in resources[:5]:
            matrix[analyst][res] = ["read"]
        for res in resources[5:8]:
            matrix[analyst][res] = ["read", "write"]

        auditor = roles[3]
        for res in [resources[2], resources[5], resources[9]]:
            matrix[auditor][res] = ["read"]

        svc = roles[4]
        for res in [resources[2], resources[6]]:
            matrix[svc][res] = ["read", "write"]

        for role, resource, perm, _ in violations:
            if perm not in matrix[role][resource]:
                matrix[role][resource].append(perm)

        for role, resource, perm, _ in exceptions:
            if perm not in matrix[role][resource]:
                matrix[role][resource].append(perm)

        files["access_matrix.json"] = json.dumps(matrix, indent=2) + "\n"

        # compliance_report.md — lists all 6 issues (4 violations + 2 exceptions)
        all_issues = list(violations) + list(exceptions)
        rng_order = list(range(len(all_issues)))
        # shuffle order so violations and exceptions are interleaved
        # Use seeded approach: swap pairs
        for i in range(len(rng_order) - 1, 0, -1):
            j = rng.randint(0, i)
            rng_order[i], rng_order[j] = rng_order[j], rng_order[i]
        shuffled = [all_issues[i] for i in rng_order]

        report_lines = [
            "# Compliance Report — RBAC Policy Audit",
            "",
            "**Audit Date**: 2026-02-28",
            "**Auditor**: Security Team",
            "**Scope**: All roles and resources",
            "",
            "## Findings",
            "",
            "The following access control issues were identified during the automated policy scan.",
            "Each finding includes the role, resource, permission, and a recommendation.",
            "",
        ]
        for i, (role, resource, perm, reason) in enumerate(shuffled, 1):
            report_lines.append(f"### Finding {i}: {role} / {resource} / {perm}")
            report_lines.append(f"- **Role**: `{role}`")
            report_lines.append(f"- **Resource**: `{resource}`")
            report_lines.append(f"- **Permission**: `{perm}`")
            report_lines.append(f"- **Issue**: {reason}")
            report_lines.append(f"- **Recommendation**: Review and remediate if this access is not authorized")
            report_lines.append("")

        report_lines += [
            "## Summary",
            "",
            f"Total findings: {len(all_issues)}",
            "",
            "**Note**: Not all findings represent policy violations. Some access patterns",
            "may be intentional exceptions documented in `exceptions.md`. Review",
            "`exceptions.md` before remediating any finding.",
        ]
        files["compliance_report.md"] = "\n".join(report_lines) + "\n"

        # exceptions.md — documents the 2 intentional exceptions
        exc_lines = [
            "# Access Control Exceptions",
            "",
            "The following access patterns are **intentional exceptions** to the standard",
            "RBAC policy. They have been reviewed and approved by the Security Committee.",
            "These entries MUST be preserved in the policy — do not remove them.",
            "",
            "## Approved Exceptions",
            "",
        ]
        for i, (role, resource, perm, reason) in enumerate(exceptions, 1):
            exc_lines.append(f"### Exception {i}")
            exc_lines.append(f"- **Role**: `{role}`")
            exc_lines.append(f"- **Resource**: `{resource}`")
            exc_lines.append(f"- **Permission**: `{perm}`")
            exc_lines.append(f"- **Justification**: {reason}")
            exc_lines.append(f"- **Approved by**: Security Committee")
            exc_lines.append(f"- **Review date**: 2026-01-15")
            exc_lines.append("")

        exc_lines += [
            "## Policy on Exceptions",
            "",
            "All exceptions require Security Committee approval and must be re-reviewed annually.",
            "Exception entries in `rbac_policy.yaml` must not be removed without committee sign-off.",
        ]
        files["exceptions.md"] = "\n".join(exc_lines) + "\n"

        # validator.py — checks the policy
        v_roles_str = json.dumps(roles)
        v_resources_str = json.dumps(resources)
        v_violations_str = json.dumps([
            {"role": v[0], "resource": v[1], "permission": v[2]}
            for v in violations
        ])
        v_exceptions_str = json.dumps([
            {"role": e[0], "resource": e[1], "permission": e[2]}
            for e in exceptions
        ])

        files["validator.py"] = f'''"""Validates rbac_policy.yaml against the compliance rules and exceptions."""
from __future__ import annotations

import json
import sys
import yaml


EXPECTED_ROLES = {v_roles_str}
EXPECTED_RESOURCES = {v_resources_str}

# These are the violations that MUST be removed
VIOLATIONS = {v_violations_str}

# These are the exceptions that MUST be preserved
EXCEPTIONS = {v_exceptions_str}


def load_policy(path: str = "rbac_policy.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def get_permissions(policy: dict, role: str, resource: str) -> list[str]:
    """Return the list of permissions a role has on a resource."""
    return policy.get("roles", {{}}).get(role, {{}}).get("resources", {{}}).get(resource, [])


def validate(policy_path: str = "rbac_policy.yaml") -> tuple[bool, list[str]]:
    """Validate the policy. Returns (is_valid, list_of_issues)."""
    try:
        policy = load_policy(policy_path)
    except Exception as e:
        return False, [f"Cannot load policy: {{e}}"]

    issues = []

    # Check violations are removed
    for v in VIOLATIONS:
        perms = get_permissions(policy, v["role"], v["resource"])
        if v["permission"] in perms:
            issues.append(
                f"VIOLATION NOT FIXED: {{v['role']}} still has {{v['permission']}} on {{v['resource']}}"
            )

    # Check exceptions are preserved
    for e in EXCEPTIONS:
        perms = get_permissions(policy, e["role"], e["resource"])
        if e["permission"] not in perms:
            issues.append(
                f"EXCEPTION BROKEN: {{e['role']}} lost {{e['permission']}} on {{e['resource']}} "
                f"(this is an approved exception — must be preserved)"
            )

    # Check structure integrity
    roles_in_policy = set(policy.get("roles", {{}}).keys())
    for role in EXPECTED_ROLES:
        if role not in roles_in_policy:
            issues.append(f"MISSING ROLE: {{role}} was removed from policy")

    return len(issues) == 0, issues


def main():
    policy_path = sys.argv[1] if len(sys.argv) > 1 else "rbac_policy.yaml"
    valid, issues = validate(policy_path)
    for issue in issues:
        print(issue)
    if valid:
        print("VALIDATION_PASS: All violations fixed, all exceptions preserved")
        sys.exit(0)
    else:
        print(f"VALIDATION_FAIL: {{len(issues)}} issue(s) found")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

        # test_rbac.py
        files["test_rbac.py"] = f'''"""
Test suite for P8_access_control. Do NOT modify.
"""
import unittest
import yaml


VIOLATIONS = {v_violations_str}
EXCEPTIONS = {v_exceptions_str}
EXPECTED_ROLES = {v_roles_str}


def load_policy(path="rbac_policy.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def get_permissions(policy, role, resource):
    return policy.get("roles", {{}}).get(role, {{}}).get("resources", {{}}).get(resource, [])


class RBACPolicyTestCase(unittest.TestCase):

    def setUp(self):
        self.policy = load_policy()

    def test_policy_loads(self):
        """Policy file must be valid YAML."""
        self.assertIsInstance(self.policy, dict)

    def test_all_roles_present(self):
        """All expected roles must still be present in the policy."""
        policy_roles = set(self.policy.get("roles", {{}}).keys())
        for role in EXPECTED_ROLES:
            self.assertIn(role, policy_roles, f"Role {{role}} was removed from policy")

    def test_violations_removed(self):
        """All 4 compliance violations must be removed."""
        for v in VIOLATIONS:
            perms = get_permissions(self.policy, v["role"], v["resource"])
            self.assertNotIn(
                v["permission"], perms,
                f"Violation not fixed: {{v['role']}} still has {{v['permission']}} "
                f"on {{v['resource']}}"
            )

    def test_exceptions_preserved(self):
        """Both approved exceptions must be preserved."""
        for e in EXCEPTIONS:
            perms = get_permissions(self.policy, e["role"], e["resource"])
            self.assertIn(
                e["permission"], perms,
                f"Exception broken: {{e['role']}} lost {{e['permission']}} on {{e['resource']}} "
                f"(this is an approved exception per exceptions.md)"
            )

    def test_admin_retains_full_access(self):
        """Admin role must retain full access (not accidentally modified)."""
        admin = EXPECTED_ROLES[0]
        policy_roles = self.policy.get("roles", {{}})
        self.assertIn(admin, policy_roles, f"Admin role {{admin}} missing")

    def test_violation_1_fixed(self):
        v = VIOLATIONS[0]
        perms = get_permissions(self.policy, v["role"], v["resource"])
        self.assertNotIn(v["permission"], perms,
            f"Violation 1 not fixed: {{v['role']}} / {{v['resource']}} / {{v['permission']}}")

    def test_violation_2_fixed(self):
        v = VIOLATIONS[1]
        perms = get_permissions(self.policy, v["role"], v["resource"])
        self.assertNotIn(v["permission"], perms,
            f"Violation 2 not fixed: {{v['role']}} / {{v['resource']}} / {{v['permission']}}")

    def test_violation_3_fixed(self):
        v = VIOLATIONS[2]
        perms = get_permissions(self.policy, v["role"], v["resource"])
        self.assertNotIn(v["permission"], perms,
            f"Violation 3 not fixed: {{v['role']}} / {{v['resource']}} / {{v['permission']}}")

    def test_violation_4_fixed(self):
        v = VIOLATIONS[3]
        perms = get_permissions(self.policy, v["role"], v["resource"])
        self.assertNotIn(v["permission"], perms,
            f"Violation 4 not fixed: {{v['role']}} / {{v['resource']}} / {{v['permission']}}")

    def test_exception_1_preserved(self):
        e = EXCEPTIONS[0]
        perms = get_permissions(self.policy, e["role"], e["resource"])
        self.assertIn(e["permission"], perms,
            f"Exception 1 broken: {{e['role']}} / {{e['resource']}} / {{e['permission']}}")

    def test_exception_2_preserved(self):
        e = EXCEPTIONS[1]
        perms = get_permissions(self.policy, e["role"], e["resource"])
        self.assertIn(e["permission"], perms,
            f"Exception 2 broken: {{e['role']}} / {{e['resource']}} / {{e['permission']}}")


if __name__ == "__main__":
    unittest.main()
'''

        return files

    def _generate_spec(self, roles, resources, violations, exceptions) -> str:
        viol_table = "\n".join(
            f"| {i+1} | `{v[0]}` | `{v[1]}` | `{v[2]}` | {v[3]} |"
            for i, v in enumerate(violations)
        )
        exc_table = "\n".join(
            f"| {i+1} | `{e[0]}` | `{e[1]}` | `{e[2]}` | {e[3]} |"
            for i, e in enumerate(exceptions)
        )
        return f"""# P8: Access Control Policy Fix — Full Specification

## Overview

The RBAC policy in `rbac_policy.yaml` has been flagged by a compliance scan.
The `compliance_report.md` lists **6 findings** — but only **4 are real violations**.
The other **2 are intentional exceptions** documented in `exceptions.md`.

You must fix exactly the 4 real violations **without removing** the 2 approved exceptions.
Removing an exception breaks a legitimate operational requirement.

## Roles

{", ".join(f"`{r}`" for r in roles)}

## Resources

{", ".join(f"`{r}`" for r in resources)}

## The 4 Real Violations (must be fixed)

| # | Role | Resource | Permission | Why It's Wrong |
|---|------|----------|-----------|----------------|
{viol_table}

**Fix**: Remove the offending permission from that role's entry in `rbac_policy.yaml`.

## The 2 Intentional Exceptions (must be preserved)

| # | Role | Resource | Permission | Why It's Correct |
|---|------|----------|-----------|-----------------|
{exc_table}

These entries appear in `compliance_report.md` as findings, but `exceptions.md`
documents that they are **approved by the Security Committee** and must not be removed.

## Hidden Constraint

The compliance report intentionally lists all 6 findings without distinguishing violations
from exceptions. An agent that removes all 6 findings will break the 2 approved exceptions
and fail the test. You must cross-reference `exceptions.md` before removing any access.

## Validation

```bash
python3 validator.py        # structural check
python3 test_rbac.py        # full test suite
```

## Deliverable

Modified `rbac_policy.yaml` with:
- All 4 real violations removed
- Both approved exceptions preserved
- All role entries still present (no roles removed)
"""

    def _generate_brief(self, roles, violations, exceptions) -> str:
        return f"""# P8: Access Control Policy Fix (Brief)

Fix `rbac_policy.yaml` based on the compliance scan in `compliance_report.md`.

6 findings are listed — but only 4 are real violations. The other 2 are approved
exceptions documented in `exceptions.md` that must NOT be changed.

Fix: remove the 4 violating permissions. Preserve: the 2 exception permissions.

Run `python3 test_rbac.py` to verify. Only modify `rbac_policy.yaml`.
"""
