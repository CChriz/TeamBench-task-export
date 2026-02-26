"""
Parameterized generator for P5: Audit Logging for Compliance.

Each seed produces:
  - A different application domain (finance, healthcare, e-commerce, HR)
  - Different event types (login, payment, record_access, etc.) with domain-specific names
  - Different required audit fields per event type (pulled from spec)
  - Different tamper-detection method (HMAC-SHA256, hash-chain, or signed log)
  - Different retention period (30/60/90/365 days depending on domain regulations)
  - A Flask app with no audit logging
  - An empty audit.py skeleton
  - A test suite checking audit requirements

TNI Pattern E, A:
  - Spec has full audit schema: required fields per event type, retention policy, tamper-detection
  - Brief says only "add audit logging for compliance"
  - Tamper detection, log rotation, field requirements are hidden from the Executor
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Domain pool ───────────────────────────────────────────────────────────────

DOMAIN_POOL = [
    # (domain_id, domain_label, regulation, app_name)
    ("finance",     "Financial Services", "SOX / PCI-DSS",    "FinanceApp"),
    ("healthcare",  "Healthcare",         "HIPAA",            "HealthPortal"),
    ("ecommerce",   "E-Commerce",         "PCI-DSS / GDPR",   "ShopPlatform"),
    ("hr",          "Human Resources",    "GDPR / SOC 2",     "HRSystem"),
    ("legal",       "Legal Services",     "ISO 27001",        "LegalVault"),
    ("government",  "Government Portal",  "FedRAMP / FISMA",  "GovPortal"),
]

# ── Event type pool — indexed per domain ──────────────────────────────────────
# Each entry: (event_type_id, label, description, base_fields)

EVENT_TYPE_POOL = {
    "finance": [
        ("user_login",       "User Login",          "A user authenticates into the system",
         ["user_id", "timestamp", "ip_address", "success"]),
        ("payment_initiated","Payment Initiated",   "A payment transaction is started",
         ["user_id", "timestamp", "amount", "currency", "recipient_account"]),
        ("report_accessed",  "Report Accessed",     "A financial report is viewed or exported",
         ["user_id", "timestamp", "report_id", "report_type"]),
        ("config_changed",   "Config Changed",      "System configuration is modified",
         ["user_id", "timestamp", "config_key", "old_value", "new_value"]),
        ("account_created",  "Account Created",     "A new user account is provisioned",
         ["admin_user_id", "timestamp", "new_user_id", "role_assigned"]),
        ("data_exported",    "Data Exported",       "Bulk data export is performed",
         ["user_id", "timestamp", "export_format", "record_count", "destination"]),
    ],
    "healthcare": [
        ("patient_record_accessed", "Patient Record Accessed",
         "A clinician or staff member views a patient record",
         ["user_id", "timestamp", "patient_id", "record_type"]),
        ("prescription_written",    "Prescription Written",
         "A prescription is created or modified",
         ["prescriber_id", "timestamp", "patient_id", "medication", "dosage"]),
        ("user_login",              "User Login",
         "A staff member authenticates into the system",
         ["user_id", "timestamp", "ip_address", "success"]),
        ("record_amended",          "Record Amended",
         "A clinical record is updated after initial entry",
         ["user_id", "timestamp", "patient_id", "field_changed", "reason"]),
        ("data_disclosed",          "Data Disclosed",
         "Patient data is shared with a third party",
         ["user_id", "timestamp", "patient_id", "recipient", "purpose"]),
        ("consent_updated",         "Consent Updated",
         "Patient consent preferences are changed",
         ["user_id", "timestamp", "patient_id", "consent_type", "granted"]),
    ],
    "ecommerce": [
        ("user_login",        "User Login",         "A user signs in to the platform",
         ["user_id", "timestamp", "ip_address", "success"]),
        ("order_placed",      "Order Placed",       "A customer places an order",
         ["user_id", "timestamp", "order_id", "total_amount", "currency"]),
        ("refund_processed",  "Refund Processed",   "A refund is issued to a customer",
         ["admin_id", "timestamp", "order_id", "refund_amount", "reason"]),
        ("product_updated",   "Product Updated",    "A product listing is modified",
         ["user_id", "timestamp", "product_id", "field_changed", "old_value", "new_value"]),
        ("payment_failed",    "Payment Failed",     "A payment attempt fails",
         ["user_id", "timestamp", "order_id", "failure_reason", "gateway_code"]),
        ("account_suspended", "Account Suspended",  "A user account is suspended or banned",
         ["admin_id", "timestamp", "target_user_id", "reason", "duration_days"]),
    ],
    "hr": [
        ("employee_hired",     "Employee Hired",      "A new employee record is created",
         ["hr_user_id", "timestamp", "employee_id", "department", "role"]),
        ("salary_changed",     "Salary Changed",      "An employee's compensation is modified",
         ["hr_user_id", "timestamp", "employee_id", "old_salary", "new_salary", "reason"]),
        ("user_login",         "User Login",           "An HR user authenticates",
         ["user_id", "timestamp", "ip_address", "success"]),
        ("record_accessed",    "Record Accessed",      "An employee file is viewed",
         ["user_id", "timestamp", "employee_id", "access_type"]),
        ("termination_logged", "Termination Logged",   "An employee separation is recorded",
         ["hr_user_id", "timestamp", "employee_id", "termination_type", "effective_date"]),
        ("policy_acknowledged","Policy Acknowledged",  "An employee acknowledges a policy update",
         ["employee_id", "timestamp", "policy_id", "policy_version"]),
    ],
    "legal": [
        ("document_accessed",  "Document Accessed",    "A legal document is opened or downloaded",
         ["user_id", "timestamp", "document_id", "document_type"]),
        ("case_created",       "Case Created",         "A new legal case is opened",
         ["user_id", "timestamp", "case_id", "client_id", "case_type"]),
        ("user_login",         "User Login",           "A user authenticates into the vault",
         ["user_id", "timestamp", "ip_address", "success"]),
        ("document_signed",    "Document Signed",      "An electronic signature is applied",
         ["user_id", "timestamp", "document_id", "signer_name", "signature_hash"]),
        ("privilege_escalated","Privilege Escalated",  "A user's access level is elevated",
         ["admin_id", "timestamp", "target_user_id", "old_role", "new_role"]),
        ("case_closed",        "Case Closed",          "A legal matter is closed",
         ["user_id", "timestamp", "case_id", "outcome", "closing_notes"]),
    ],
    "government": [
        ("citizen_record_accessed","Citizen Record Accessed","A citizen file is retrieved",
         ["officer_id", "timestamp", "citizen_id", "record_category"]),
        ("form_submitted",         "Form Submitted",        "A government form is submitted",
         ["user_id", "timestamp", "form_id", "form_type", "reference_number"]),
        ("user_login",             "User Login",            "An officer authenticates",
         ["user_id", "timestamp", "ip_address", "success"]),
        ("permit_issued",          "Permit Issued",         "An official permit or licence is granted",
         ["officer_id", "timestamp", "permit_id", "applicant_id", "permit_type"]),
        ("data_shared",            "Data Shared",           "Data is transmitted to another agency",
         ["officer_id", "timestamp", "recipient_agency", "data_category", "record_count"]),
        ("access_revoked",         "Access Revoked",        "A user's system access is removed",
         ["admin_id", "timestamp", "target_user_id", "reason"]),
    ],
}

# ── Tamper detection methods ───────────────────────────────────────────────────

TAMPER_DETECTION_POOL = [
    {
        "method_id": "hmac_sha256",
        "label": "HMAC-SHA256 Entry Signature",
        "description": (
            "Each audit log entry must include a `signature` field containing an "
            "HMAC-SHA256 digest of the canonical JSON of the entry (fields sorted "
            "alphabetically, excluding the `signature` field itself). The HMAC key is "
            "the value of the environment variable AUDIT_HMAC_KEY (default: 'default-key' "
            "if unset). This allows any entry to be independently verified for tampering."
        ),
        "required_field": "signature",
        "verify_snippet": (
            "import hmac, hashlib, json, os\n"
            "key = os.environ.get('AUDIT_HMAC_KEY', 'default-key').encode()\n"
            "entry_copy = {k: v for k, v in entry.items() if k != 'signature'}\n"
            "canonical = json.dumps(entry_copy, sort_keys=True)\n"
            "expected_sig = hmac.new(key, canonical.encode(), hashlib.sha256).hexdigest()\n"
            "assert entry['signature'] == expected_sig"
        ),
    },
    {
        "method_id": "hash_chain",
        "label": "Hash-Chain Integrity",
        "description": (
            "Each audit log entry must include a `prev_hash` field containing the "
            "SHA-256 hash of the previous entry's canonical JSON (fields sorted "
            "alphabetically, excluding `prev_hash`). The first entry uses "
            "prev_hash='0'*64 (64 zeros). This creates an immutable chain: any "
            "modification to a prior entry breaks all subsequent hashes."
        ),
        "required_field": "prev_hash",
        "verify_snippet": (
            "import hashlib, json\n"
            "prev = log[i-1] if i > 0 else None\n"
            "if prev is None:\n"
            "    assert entry['prev_hash'] == '0'*64\n"
            "else:\n"
            "    prev_copy = {k: v for k, v in prev.items()}\n"
            "    canonical = json.dumps(prev_copy, sort_keys=True)\n"
            "    expected = hashlib.sha256(canonical.encode()).hexdigest()\n"
            "    assert entry['prev_hash'] == expected"
        ),
    },
    {
        "method_id": "entry_checksum",
        "label": "Per-Entry SHA-256 Checksum",
        "description": (
            "Each audit log entry must include a `checksum` field containing the "
            "SHA-256 hex digest of the canonical JSON of the entry (all fields sorted "
            "alphabetically, excluding the `checksum` field). On read, any entry whose "
            "recomputed checksum does not match the stored `checksum` must be flagged "
            "as TAMPERED. The audit module must expose a `verify_log(entries)` function "
            "that returns a list of tampered entry indices."
        ),
        "required_field": "checksum",
        "verify_snippet": (
            "import hashlib, json\n"
            "entry_copy = {k: v for k, v in entry.items() if k != 'checksum'}\n"
            "canonical = json.dumps(entry_copy, sort_keys=True)\n"
            "expected = hashlib.sha256(canonical.encode()).hexdigest()\n"
            "assert entry['checksum'] == expected"
        ),
    },
]

# ── Retention policy pool ─────────────────────────────────────────────────────

RETENTION_POOL = [
    # (days, label, regulation_note)
    (90,  "90 days",    "Minimum retention for operational audit logs."),
    (180, "180 days",   "Six-month retention for standard compliance frameworks."),
    (365, "1 year",     "Annual retention mandated by most financial regulations."),
    (730, "2 years",    "Extended retention for healthcare records (HIPAA)."),
    (2555,"7 years",    "Seven-year statutory retention for SOX financial records."),
]

# ── Log rotation requirements pool ────────────────────────────────────────────

ROTATION_POOL = [
    {
        "strategy": "daily",
        "description": (
            "Audit log files must be rotated daily. Each file is named "
            "audit_YYYY-MM-DD.jsonl. The current day's entries are written to "
            "audit_today.jsonl and renamed at midnight."
        ),
    },
    {
        "strategy": "size_based",
        "description": (
            "Audit log files must be rotated when they exceed 10 MB. Rotated files "
            "are named audit_<timestamp>.jsonl where timestamp is the ISO-8601 UTC "
            "time of rotation."
        ),
    },
    {
        "strategy": "weekly",
        "description": (
            "Audit log files are rotated weekly (every Monday at 00:00 UTC). Each "
            "file is named audit_week_<YYYY-WNN>.jsonl."
        ),
    },
]


class Generator(TaskGenerator):
    task_id = "P5_audit_logging"
    domain = "policy"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # ── Pick domain for this seed ───────────────────────────────────────
        domain_entry = DOMAIN_POOL[seed % len(DOMAIN_POOL)]
        domain_id, domain_label, regulation, app_name = domain_entry

        # ── Pick event types (4-5) ─────────────────────────────────────────
        pool = EVENT_TYPE_POOL[domain_id]
        num_events = rng.randint(4, 5)
        selected_events = rng.sample(pool, num_events)
        # Always ensure user_login is present (universal event)
        has_login = any(e[0] == "user_login" for e in selected_events)
        if not has_login:
            login_ev = next(e for e in pool if e[0] == "user_login")
            selected_events[-1] = login_ev

        # ── Per-event field jitter: add 0-1 extra universal fields ─────────
        extra_universal_fields = ["session_id", "user_agent", "request_id", "correlation_id"]
        event_schemas: dict[str, list[str]] = {}
        for ev_id, ev_label, ev_desc, base_fields in selected_events:
            fields = list(base_fields)
            # Add "event_type" and "log_id" as mandatory universal fields
            if "event_type" not in fields:
                fields = ["event_type", "log_id"] + fields
            # Optionally add one extra universal field based on seed+event hash
            extra_idx = (seed + hash(ev_id)) % len(extra_universal_fields)
            extra_field = extra_universal_fields[extra_idx]
            if extra_field not in fields:
                fields.append(extra_field)
            event_schemas[ev_id] = fields

        # ── Pick tamper detection method ────────────────────────────────────
        tamper_idx = seed % len(TAMPER_DETECTION_POOL)
        tamper = TAMPER_DETECTION_POOL[tamper_idx]

        # ── Pick retention policy ──────────────────────────────────────────
        # Healthcare -> longer, finance -> 7yr statutory, others -> moderate
        if domain_id == "healthcare":
            retention = next(r for r in RETENTION_POOL if r[0] == 730)
        elif domain_id == "finance":
            retention = next(r for r in RETENTION_POOL if r[0] == 2555)
        elif domain_id == "government":
            retention = next(r for r in RETENTION_POOL if r[0] == 365)
        else:
            # ecommerce, hr, legal — pick from moderate range with seed jitter
            moderate = [r for r in RETENTION_POOL if r[0] in (90, 180, 365)]
            retention = moderate[seed % len(moderate)]
        retention_days, retention_label, retention_note = retention

        # ── Pick log rotation strategy ─────────────────────────────────────
        rotation = ROTATION_POOL[seed % len(ROTATION_POOL)]

        # ── Build expected values ──────────────────────────────────────────
        event_type_ids = [ev[0] for ev in selected_events]
        expected = {
            "domain": domain_id,
            "regulation": regulation,
            "required_event_types": event_type_ids,
            "required_fields_per_event": event_schemas,
            "retention_days": retention_days,
            "tamper_detection_method": tamper["method_id"],
            "tamper_detection_required_field": tamper["required_field"],
            "log_rotation_strategy": rotation["strategy"],
        }

        # ── Generate corpus/audit_policy.txt ──────────────────────────────
        policy_txt = self._generate_policy(
            domain_label=domain_label,
            regulation=regulation,
            app_name=app_name,
            selected_events=selected_events,
            event_schemas=event_schemas,
            tamper=tamper,
            retention_days=retention_days,
            retention_label=retention_label,
            retention_note=retention_note,
            rotation=rotation,
            seed=seed,
        )

        # ── Generate workspace files ───────────────────────────────────────
        app_py = self._generate_app(
            app_name=app_name,
            domain_id=domain_id,
            selected_events=selected_events,
        )
        audit_py = self._generate_audit_stub(
            tamper=tamper,
            event_type_ids=event_type_ids,
        )
        test_py = self._generate_tests(
            domain_id=domain_id,
            selected_events=selected_events,
            event_schemas=event_schemas,
            tamper=tamper,
            retention_days=retention_days,
        )

        spec_md = self._generate_spec(
            domain_label=domain_label,
            regulation=regulation,
            app_name=app_name,
            selected_events=selected_events,
            event_schemas=event_schemas,
            tamper=tamper,
            retention_days=retention_days,
            retention_label=retention_label,
            rotation=rotation,
        )
        brief_md = self._generate_brief(app_name=app_name)

        corpus_files = {
            "audit_policy.txt": policy_txt,
        }

        workspace_files = {
            "app.py": app_py,
            "audit.py": audit_py,
            "tests/test_audit.py": test_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_policy(
        self,
        domain_label: str,
        regulation: str,
        app_name: str,
        selected_events: list,
        event_schemas: dict,
        tamper: dict,
        retention_days: int,
        retention_label: str,
        retention_note: str,
        rotation: dict,
        seed: int,
    ) -> str:
        ver = f"{1 + seed % 5}.{seed % 10}"
        year = 2024 + (seed % 3)

        lines = [
            f"AUDIT LOGGING COMPLIANCE POLICY — {domain_label.upper()}",
            f"Application: {app_name}",
            f"Regulation: {regulation}",
            f"Policy Version: {ver}",
            f"Effective Date: {year}-01-01",
            "Classification: INTERNAL — COMPLIANCE SENSITIVE",
            "",
            "=== PURPOSE ===",
            "",
            f"This policy defines mandatory audit logging requirements for {app_name}.",
            f"Compliance with {regulation} requires that all security-relevant events",
            "are captured in an immutable, tamper-evident audit trail.",
            "",
            "=== SECTION 1: REQUIRED EVENT TYPES ===",
            "",
            "The following event types MUST be logged. Any event of these types that",
            "occurs in the application must produce an audit log entry.",
            "",
        ]

        for ev_id, ev_label, ev_desc, _ in selected_events:
            fields = event_schemas[ev_id]
            lines.append(f"Event Type: {ev_id}")
            lines.append(f"  Label: {ev_label}")
            lines.append(f"  Description: {ev_desc}")
            lines.append(f"  Required Fields: {', '.join(fields)}")
            lines.append("")

        lines += [
            "=== SECTION 2: FIELD REQUIREMENTS ===",
            "",
            "Every audit log entry must contain ALL required fields for its event type.",
            "Missing fields constitute a compliance violation.",
            "",
            "Universal fields required on ALL event types:",
            "  - event_type (string): the event type identifier (e.g. 'user_login')",
            "  - log_id (string): a unique UUID for this log entry",
            "",
            "Event-type-specific fields are listed under Section 1.",
            "The full required field list per event type (including universal fields)",
            "is the union of universal fields and event-specific fields shown above.",
            "",
            "=== SECTION 3: TAMPER DETECTION ===",
            "",
            f"Method: {tamper['label']}",
            "",
            tamper["description"],
            "",
            f"The required tamper-detection field is: `{tamper['required_field']}`",
            "This field must be present on every audit log entry.",
            "Entries missing this field, or entries whose tamper-detection value does",
            "not verify correctly, are considered INVALID.",
            "",
            "=== SECTION 4: RETENTION POLICY ===",
            "",
            f"Minimum Retention Period: {retention_label} ({retention_days} days)",
            f"Regulatory basis: {retention_note}",
            "",
            "Audit logs MUST be retained for at least the minimum retention period.",
            "Logs must NOT be deleted or overwritten before the retention period expires.",
            "After the retention period, logs MAY be archived or deleted, but only",
            "after producing a signed deletion certificate.",
            "",
            "=== SECTION 5: LOG ROTATION ===",
            "",
            f"Rotation strategy: {rotation['strategy']}",
            "",
            rotation["description"],
            "",
            "=== SECTION 6: IMPLEMENTATION REQUIREMENTS ===",
            "",
            "1. Implement audit logging in `audit.py`. The module must expose:",
            "     - `log_event(event_type: str, **fields) -> dict`",
            "       Creates, stores, and returns the audit log entry.",
            "     - `get_log() -> list[dict]`",
            "       Returns all audit log entries (in-memory for this task).",
            "     - `verify_log(entries: list[dict]) -> list[int]`",
            "       Returns indices of tampered entries (empty list if all valid).",
            "",
            "2. Integrate `log_event()` into `app.py` so every endpoint call that",
            "   triggers a loggable event produces an audit entry.",
            "",
            "3. The audit module must produce entries containing ALL required fields",
            "   for the relevant event type (see Section 1).",
            "",
            "4. Every entry must include the tamper-detection field as described in",
            "   Section 3. The `verify_log()` function must detect tampered entries.",
            "",
            "5. The `log_id` field must be a UUID4 string (use `uuid.uuid4()`).",
            "",
            "=== END OF POLICY ===",
        ]

        return "\n".join(lines) + "\n"

    def _generate_app(
        self,
        app_name: str,
        domain_id: str,
        selected_events: list,
    ) -> str:
        """Generate Flask app with no audit logging — skeleton only."""

        # Build endpoint definitions based on event types
        endpoints = []
        for ev_id, ev_label, ev_desc, base_fields in selected_events:
            route = f"/{ev_id.replace('_', '-')}"
            endpoints.append((ev_id, route, ev_label, ev_desc))

        ep_lines = []
        for ev_id, route, ev_label, ev_desc in endpoints:
            ep_lines.append(f"@app.route('{route}', methods=['POST'])")
            fn_name = ev_id
            ep_lines.append(f"def {fn_name}():")
            ep_lines.append(f'    """Handle {ev_label}: {ev_desc}"""')
            ep_lines.append("    data = request.get_json() or {}")
            ep_lines.append(
                "    # TODO: call audit.log_event() with the appropriate fields"
            )
            ep_lines.append(
                f"    # audit.log_event('{ev_id}', **data)  # uncomment and implement"
            )
            ep_lines.append(
                f"    return jsonify({{'status': 'ok', 'event': '{ev_id}'}}), 200"
            )
            ep_lines.append("")
            ep_lines.append("")

        ep_block = "\n".join(ep_lines)

        return f'''"""
{app_name} — Flask application skeleton.

Audit logging has NOT been implemented yet.
Your task: integrate audit.log_event() into each endpoint so that every
relevant event produces a compliant audit log entry per corpus/audit_policy.txt.

Do NOT modify the route signatures or return structures.
"""

from flask import Flask, request, jsonify
import audit

app = Flask(__name__)


{ep_block}@app.route('/audit-log', methods=['GET'])
def get_audit_log():
    """Return all audit log entries."""
    return jsonify({{'entries': audit.get_log()}}), 200


@app.route('/verify-log', methods=['GET'])
def verify_audit_log():
    """Verify audit log integrity and return tampered entry indices."""
    entries = audit.get_log()
    tampered = audit.verify_log(entries)
    return jsonify({{'tampered_indices': tampered}}), 200


if __name__ == '__main__':
    app.run(debug=False)
'''

    def _generate_audit_stub(
        self,
        tamper: dict,
        event_type_ids: list[str],
    ) -> str:
        """Generate audit.py skeleton for the agent to implement."""

        events_comment = ", ".join(f'"{e}"' for e in event_type_ids)
        tamper_field = tamper["required_field"]
        tamper_method = tamper["method_id"]
        tamper_label = tamper["label"]

        return f'''"""
Audit logging module — implement this file to satisfy the compliance requirements
in corpus/audit_policy.txt.

Required exports:
    log_event(event_type, **fields) -> dict
        Create, store, and return a compliant audit log entry.
        The entry must include ALL required fields for the event type,
        plus the tamper-detection field ({tamper_field!r}).

    get_log() -> list[dict]
        Return all stored audit log entries.

    verify_log(entries) -> list[int]
        Return indices of entries that fail tamper-detection verification.
        Return an empty list if all entries are valid.

Tamper detection method: {tamper_label}
Required tamper-detection field: {tamper_field!r}

Read corpus/audit_policy.txt for full field requirements per event type.
"""

import uuid
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any

# Supported event types: {events_comment}
# See corpus/audit_policy.txt Section 1 for required fields per event type.

# In-memory audit log store (do not change this to a persistent store)
_AUDIT_LOG: list[dict] = []


def log_event(event_type: str, **fields: Any) -> dict:
    """
    Create a compliant audit log entry for the given event_type.

    - Adds universal fields: event_type, log_id
    - Adds all caller-supplied fields
    - Computes and attaches the tamper-detection field ({tamper_field!r})
    - Appends the entry to _AUDIT_LOG
    - Returns the completed entry

    Raises ValueError if event_type is not a recognized event type.
    """
    # TODO: implement audit entry creation
    # 1. Build the base entry with event_type + log_id (uuid4) + all **fields
    # 2. Compute {tamper_field!r} using the {tamper_method} method (see policy)
    # 3. Attach {tamper_field!r} to the entry
    # 4. Append to _AUDIT_LOG
    # 5. Return the entry
    raise NotImplementedError("log_event() must be implemented")


def get_log() -> list[dict]:
    """Return all audit log entries."""
    return list(_AUDIT_LOG)


def verify_log(entries: list[dict]) -> list[int]:
    """
    Verify tamper-detection field ({tamper_field!r}) on every entry.

    Returns a list of 0-based indices of entries that fail verification.
    Returns an empty list if all entries are valid.
    """
    # TODO: implement tamper detection verification
    # For each entry, recompute the expected {tamper_field!r} and compare.
    # Return indices where verification fails.
    raise NotImplementedError("verify_log() must be implemented")
'''

    def _generate_tests(
        self,
        domain_id: str,
        selected_events: list,
        event_schemas: dict,
        tamper: dict,
        retention_days: int,
    ) -> str:
        """Generate test suite for audit requirements."""

        first_event = selected_events[0]
        first_ev_id = first_event[0]
        first_ev_fields = event_schemas[first_ev_id]

        # Build a minimal valid payload for the first event (exclude universal fields)
        universal = {"event_type", "log_id", "signature", "prev_hash", "checksum"}
        first_ev_payload_fields = [
            fld for fld in first_ev_fields if fld not in universal
        ]
        payload_dict = {fld: f"test_{fld}_value" for fld in first_ev_payload_fields}
        payload_repr = repr(payload_dict)

        tamper_field = tamper["required_field"]
        tamper_field_r = repr(tamper_field)
        tamper_method = tamper["method_id"]

        # Collect all event ids and their required fields for parametrized checks
        ev_check_lines = []
        for ev_id, _ev_label, _, _ in selected_events:
            required = event_schemas[ev_id]
            required_repr = repr(required)
            ev_check_lines.append(
                f"    ({repr(ev_id)}, {required_repr}),"
            )
        ev_checks_block = "\n".join(ev_check_lines)

        # Pre-build the two multi-event test data literals so we don't need
        # complex expressions inside the template string.
        two_events = selected_events[:2]
        two_events_list_r = repr([(e[0], e[1], e[2], e[3]) for e in two_events])
        event_schemas_r = repr(event_schemas)

        first_ev_id_r = repr(first_ev_id)
        first_ev_pf_r = repr(first_ev_payload_fields)

        # Use a plain (non-f) triple-quoted string with .format() to avoid
        # any ambiguity between f-string braces and set/dict literals.
        template = '''\
"""
Test suite for P5: Audit Logging Compliance

Tests verify that audit.py correctly implements:
  1. Required fields per event type
  2. Tamper-detection field presence ({tamper_field_r})
  3. verify_log() detects tampered entries
  4. log_event() returns entries and populates get_log()
  5. Universal fields (event_type, log_id) on all entries

Domain: {domain_id}
Tamper detection method: {tamper_method}
"""

import pytest
import json
import hashlib
import sys
import os

# Ensure workspace root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audit


@pytest.fixture(autouse=True)
def reset_audit_log():
    """Clear audit log between tests."""
    audit._AUDIT_LOG.clear()
    yield
    audit._AUDIT_LOG.clear()


# ── 1. log_event() returns a dict ─────────────────────────────────────────────

def test_log_event_returns_dict():
    payload = {payload_repr}
    result = audit.log_event({first_ev_id_r}, **payload)
    assert isinstance(result, dict), "log_event() must return a dict"


# ── 2. Universal fields present ───────────────────────────────────────────────

def test_universal_fields_event_type():
    result = audit.log_event({first_ev_id_r}, **{payload_repr})
    assert "event_type" in result, "entry must contain \'event_type\'"
    assert result["event_type"] == {first_ev_id_r}


def test_universal_fields_log_id():
    result = audit.log_event({first_ev_id_r}, **{payload_repr})
    assert "log_id" in result, "entry must contain \'log_id\'"
    assert isinstance(result["log_id"], str), "\'log_id\' must be a string"
    assert len(result["log_id"]) > 0, "\'log_id\' must not be empty"


def test_log_ids_unique():
    r1 = audit.log_event({first_ev_id_r}, **{payload_repr})
    r2 = audit.log_event({first_ev_id_r}, **{payload_repr})
    assert r1["log_id"] != r2["log_id"], "Each entry must have a unique log_id"


# ── 3. Required fields per event type ────────────────────────────────────────

@pytest.mark.parametrize("event_type,required_fields", [
{ev_checks_block}
])
def test_required_fields_present(event_type, required_fields):
    # Build a minimal payload with dummy values for non-universal fields
    _universal = {{"event_type", "log_id", "signature", "prev_hash", "checksum"}}
    payload = {{f: "test_" + f for f in required_fields if f not in _universal}}
    entry = audit.log_event(event_type, **payload)
    for field in required_fields:
        assert field in entry, (
            "Event type \'" + event_type + "\' entry missing required field \'" + field + "\'"
        )


# ── 4. Tamper-detection field present ────────────────────────────────────────

def test_tamper_field_present():
    result = audit.log_event({first_ev_id_r}, **{payload_repr})
    assert {tamper_field_r} in result, (
        "Entry must contain tamper-detection field " + repr({tamper_field_r})
    )


def test_tamper_field_non_empty():
    result = audit.log_event({first_ev_id_r}, **{payload_repr})
    assert result.get({tamper_field_r}), (
        "Tamper-detection field " + repr({tamper_field_r}) + " must not be empty"
    )


# ── 5. get_log() returns all entries ─────────────────────────────────────────

def test_get_log_empty_initially():
    assert audit.get_log() == [], "get_log() must return [] before any events"


def test_get_log_contains_logged_entries():
    audit.log_event({first_ev_id_r}, **{payload_repr})
    audit.log_event({first_ev_id_r}, **{payload_repr})
    log = audit.get_log()
    assert len(log) == 2, "Expected 2 entries in log, got " + str(len(log))


def test_get_log_returns_list():
    result = audit.get_log()
    assert isinstance(result, list), "get_log() must return a list"


# ── 6. verify_log() on untampered log ────────────────────────────────────────

def test_verify_log_empty():
    result = audit.verify_log([])
    assert result == [], "verify_log([]) must return []"


def test_verify_log_valid_entries_no_tamper():
    audit.log_event({first_ev_id_r}, **{payload_repr})
    audit.log_event({first_ev_id_r}, **{payload_repr})
    entries = audit.get_log()
    tampered = audit.verify_log(entries)
    assert tampered == [], (
        "verify_log() must return [] for untampered entries, got " + str(tampered)
    )


# ── 7. verify_log() detects tampered entry ───────────────────────────────────

def test_verify_log_detects_tampering():
    audit.log_event({first_ev_id_r}, **{payload_repr})
    entries = audit.get_log()
    # Tamper with the entry by mutating a copy
    tampered_entries = [dict(e) for e in entries]
    tampered_entries[0]["event_type"] = "tampered_event"
    # Remove tamper-detection field to simulate manual edit
    tampered_entries[0].pop({tamper_field_r}, None)
    result = audit.verify_log(tampered_entries)
    assert 0 in result, (
        "verify_log() must detect the tampered entry at index 0"
    )


# ── 8. Multiple event types produce correct field sets ───────────────────────

def test_multiple_event_types_logged():
    _two_events = {two_events_list_r}
    _schemas = {event_schemas_r}
    _universal = {{"event_type", "log_id", "signature", "prev_hash", "checksum"}}
    results = []
    for ev_id, _label, _desc, _fields in _two_events:
        fields = _schemas[ev_id]
        payload = {{f: "val_" + f for f in fields if f not in _universal}}
        entry = audit.log_event(ev_id, **payload)
        results.append(entry)
    assert len(results) == 2, "Expected 2 logged entries"
    # Just ensure no crash and event_type is set correctly
    for i, (ev_id, _, _, _) in enumerate(_two_events):
        assert results[i]["event_type"] == ev_id


# ── 9. Retention metadata (structural check) ─────────────────────────────────

def test_retention_days_constant_exists():
    """audit.py should work correctly (retention config is in the policy doc)."""
    entry = audit.log_event({first_ev_id_r}, **{payload_repr})
    assert entry is not None


# ── 10. log_event stores entry in get_log ────────────────────────────────────

def test_log_event_persists_to_store():
    entry = audit.log_event({first_ev_id_r}, **{payload_repr})
    stored = audit.get_log()
    assert len(stored) == 1
    assert stored[0]["log_id"] == entry["log_id"], (
        "Stored entry must match the returned entry"
    )
'''
        return template.format(
            tamper_field_r=tamper_field_r,
            domain_id=domain_id,
            tamper_method=tamper_method,
            payload_repr=payload_repr,
            first_ev_id_r=first_ev_id_r,
            first_ev_pf_r=first_ev_pf_r,
            ev_checks_block=ev_checks_block,
            tamper_field=tamper_field,
            two_events_list_r=two_events_list_r,
            event_schemas_r=event_schemas_r,
        )

    def _generate_spec(
        self,
        domain_label: str,
        regulation: str,
        app_name: str,
        selected_events: list,
        event_schemas: dict,
        tamper: dict,
        retention_days: int,
        retention_label: str,
        rotation: dict,
    ) -> str:
        event_list = "\n".join(
            f"- **{ev_id}** ({ev_label}): {ev_desc}\n"
            f"  Required fields: `{'`, `'.join(event_schemas[ev_id])}`"
            for ev_id, ev_label, ev_desc, _ in selected_events
        )

        return f"""# P5: Audit Logging for Compliance

## Goal

Implement compliant audit logging in `audit.py` and integrate it into `app.py` so that
every security-relevant event produces a tamper-evident audit log entry meeting
{regulation} requirements.

## Application Domain

**{domain_label}** — {app_name}
Regulatory framework: **{regulation}**

## Required Event Types and Fields

The following events must be logged. Each entry must contain ALL listed fields.

{event_list}

**Universal fields** (required on every entry regardless of event type):
- `event_type` (string): the event type identifier
- `log_id` (string): a unique UUID4 string for this entry

## Tamper Detection

**Method:** {tamper['label']}

{tamper['description']}

Required tamper-detection field: `{tamper['required_field']}`

## Retention Policy

Minimum retention period: **{retention_label}** ({retention_days} days)

Audit logs must be retained for at least this period and must not be modified or
deleted before expiry.

## Log Rotation

Strategy: **{rotation['strategy']}**

{rotation['description']}

## Hard Requirements

1. Implement `log_event(event_type, **fields) -> dict` in `audit.py`.
   - Must include all required fields for the event type (see above).
   - Must compute and attach the `{tamper['required_field']}` tamper-detection field.
   - Must append the entry to an in-memory log and return it.

2. Implement `get_log() -> list[dict]` returning all stored entries.

3. Implement `verify_log(entries) -> list[int]` returning indices of tampered entries.

4. Integrate `audit.log_event()` into every relevant endpoint in `app.py`.

5. All entries must have unique `log_id` values (UUID4).

6. `verify_log()` must correctly detect entries whose `{tamper['required_field']}` field
   has been corrupted or is missing.

## Files

- `corpus/audit_policy.txt` — authoritative compliance policy (read this first)
- `audit.py` — implement all audit functions here
- `app.py` — integrate audit logging into each endpoint
- `tests/test_audit.py` — test suite that must pass

## Deliverables

- `audit.py` fully implemented
- `app.py` with `audit.log_event()` called at each event endpoint
- All tests in `tests/test_audit.py` passing
- Verifier produces `output/attestation.json` with verdict
"""

    def _generate_brief(self, app_name: str) -> str:
        return f"""# P5: Audit Logging (Brief)

Add audit logging to {app_name} for compliance.

Read `corpus/audit_policy.txt` for the required event types, field schemas,
tamper-detection requirements, and retention policy.

Implement `audit.py` and integrate logging into `app.py`.
"""
