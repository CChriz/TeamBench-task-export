"""
Data reconciliation script — merge System A (Identity) and System B (SubscriptionMgr).

FIXED: Implements all 6 reconciliation rules in strict priority order:
  1. manual_override=True in System B -> System B wins ALL fields for that record
  2. System A is authoritative for its owned fields
  3. System B is authoritative for its owned fields
  4. For shared fields with conflicting values: newer last_updated timestamp wins
  5. Records only in System A: include them, null-fill System B fields
  6. Records only in System B: include them, null-fill System A fields

Output: reconciled.json — list of merged records sorted by subscriber_id.
"""
import json

ID_FIELD = "subscriber_id"

# Field ownership — DO NOT CHANGE these assignments
A_OWNED_FIELDS = ['username', 'email', 'display_name', 'auth_provider']
B_OWNED_FIELDS = ['plan_id', 'renewal_date', 'seats', 'discount_pct']
SHARED_FIELDS  = ['account_status', 'timezone']

ALL_OUTPUT_FIELDS = [ID_FIELD] + A_OWNED_FIELDS + B_OWNED_FIELDS + SHARED_FIELDS + ["reconcile_source"]


def load_system(path):
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    return {r[ID_FIELD]: r for r in records}


def reconcile(a_records, b_records):
    all_ids = sorted(set(a_records) | set(b_records))
    result = []

    for rid in all_ids:
        a = a_records.get(rid)
        b = b_records.get(rid)

        # Initialize output record with all 12 fields defaulting to None,
        # ensuring correct field ordering and null-fill for missing domains.
        out = {field: None for field in ALL_OUTPUT_FIELDS}
        out[ID_FIELD] = rid

        if a is not None and b is not None:
            # --- Rule 1 (highest priority): Manual Override ---
            if b.get("manual_override") is True:
                # System B wins ALL fields, including those normally owned by A.
                for f in A_OWNED_FIELDS + B_OWNED_FIELDS + SHARED_FIELDS:
                    out[f] = b.get(f)
                out["reconcile_source"] = "manual_override"
            else:
                # --- Rule 2: Field Ownership ---
                # A-owned fields always from System A.
                for f in A_OWNED_FIELDS:
                    out[f] = a.get(f)
                # B-owned fields always from System B.
                for f in B_OWNED_FIELDS:
                    out[f] = b.get(f)

                # --- Rule 3: Shared Field Conflict Resolution ---
                # Compare last_updated timestamps; newer wins. Equal -> A takes precedence.
                ts_a = a.get("last_updated", "")
                ts_b = b.get("last_updated", "")
                shared_source = a if ts_a >= ts_b else b
                for f in SHARED_FIELDS:
                    out[f] = shared_source.get(f)

                # --- Rule 6 (no-conflict merge) ---
                out["reconcile_source"] = "merged"

        elif a is not None:
            # --- Rule 4: System A Only ---
            for f in A_OWNED_FIELDS:
                out[f] = a.get(f)
            for f in SHARED_FIELDS:
                out[f] = a.get(f)
            # B-owned fields remain None (initialized above)
            out["reconcile_source"] = "system_a_only"

        else:
            # --- Rule 5: System B Only ---
            for f in B_OWNED_FIELDS:
                out[f] = b.get(f)
            for f in SHARED_FIELDS:
                out[f] = b.get(f)
            # A-owned fields remain None (initialized above)
            out["reconcile_source"] = "system_b_only"

        # Ensure output fields are in the exact order specified by ALL_OUTPUT_FIELDS.
        ordered_out = {f: out[f] for f in ALL_OUTPUT_FIELDS}
        result.append(ordered_out)

    return result


def main():
    a_records = load_system("system_a.json")
    b_records = load_system("system_b.json")

    reconciled = reconcile(a_records, b_records)

    with open("reconciled.json", "w", encoding="utf-8") as f:
        json.dump(reconciled, f, indent=2, ensure_ascii=False)

    print(f"Reconciled {len(reconciled)} records -> reconciled.json")


if __name__ == "__main__":
    main()
