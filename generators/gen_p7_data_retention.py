"""
Parameterized generator for P7: Data Retention Policy Compliance.

Each seed produces:
  - Different user records with varying ages
  - Different retention periods and reference dates
  - A buggy manage.py with 3 policy violations
"""
from __future__ import annotations

import json
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool

PHONE_PREFIXES = ["+1-555", "+44-20", "+49-30"]


class Generator(TaskGenerator):
    task_id = "P7_data_retention"
    domain = "policy"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=20)

        retention_days = [90, 60, 120][seed % 3]
        # Reference date: 2024-06-15 for all seeds (simplicity)
        ref_date = "2024-06-15"

        n_users = rng.randint(10, 15)
        users = []
        expired_ids = []
        keep_ids = []

        for i in range(1, n_users + 1):
            name = names.next()
            email = f"{name.lower().replace(' ', '.')}@example.com"
            phone = f"{rng.choice(PHONE_PREFIXES)}-{rng.randint(1000, 9999)}"

            # Half are expired (last_active > retention_days before ref_date)
            if i <= n_users // 2:
                # Expired: last_active 120-300 days before ref_date
                days_ago = rng.randint(retention_days + 30, retention_days + 210)
                expired_ids.append(i)
            else:
                # Active: last_active 1-60 days before ref_date
                days_ago = rng.randint(1, min(60, retention_days - 1))
                keep_ids.append(i)

            # Compute dates
            from datetime import datetime, timedelta
            ref = datetime(2024, 6, 15)
            last_active = (ref - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            created_at = (ref - timedelta(days=days_ago + rng.randint(30, 365))).strftime("%Y-%m-%d")

            users.append({
                "id": i,
                "name": name,
                "email": email,
                "phone": phone,
                "created_at": created_at,
                "last_active": last_active,
            })

        # Pick one active user for anonymization test
        anonymize_test_id = keep_ids[0] if keep_ids else expired_ids[-1]

        config = {
            "retention_days": retention_days,
            "reference_date": ref_date,
        }

        workspace_files = {
            "data/users.json": json.dumps(users, indent=2),
            "config.json": json.dumps(config, indent=2),
            "manage.py": self._make_buggy_manage(),
            "audit_log.json": "[]",
        }

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "expired_ids": expired_ids,
                "keep_ids": keep_ids,
                "anonymize_test_id": anonymize_test_id,
                "retention_days": retention_days,
                "reference_date": ref_date,
                "total_users": n_users,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "medium", "category": "Policy"},
        )

    def _make_buggy_manage(self) -> str:
        return '''"""User data management with retention policy."""
import json
import sys
from datetime import datetime, timedelta


def load_config():
    with open("config.json") as f:
        return json.load(f)


def load_users():
    with open("data/users.json") as f:
        return json.load(f)


def save_users(users):
    with open("data/users.json", "w") as f:
        json.dump(users, f, indent=2)


def enforce_retention():
    """Delete users whose last_active is older than retention_days.

    BUG 1: This is a no-op stub — does not actually delete expired records.
    """
    config = load_config()
    users = load_users()
    # TODO: implement retention enforcement
    print(f"Retention policy: {config['retention_days']} days")
    print(f"Total users: {len(users)}")
    # No deletion happens — this is the bug
    save_users(users)


def anonymize_user(user_id):
    """Anonymize PII fields for a specific user.

    BUG 2: Only clears email, should also clear name and phone.
    """
    users = load_users()
    for user in users:
        if user["id"] == int(user_id):
            user["email"] = "[REDACTED]"
            # BUG: name and phone not anonymized
            break
    save_users(users)
    print(f"Anonymized user {user_id}")

    # BUG 3: No audit logging for any operations


def generate_report():
    """Generate a compliance report."""
    config = load_config()
    users = load_users()
    ref_date = datetime.strptime(config["reference_date"], "%Y-%m-%d")
    retention_days = config["retention_days"]
    cutoff = ref_date - timedelta(days=retention_days)

    expired = []
    active = []
    for user in users:
        last_active = datetime.strptime(user["last_active"], "%Y-%m-%d")
        if last_active < cutoff:
            expired.append(user["id"])
        else:
            active.append(user["id"])

    report = {
        "reference_date": config["reference_date"],
        "retention_days": retention_days,
        "total_users": len(users),
        "expired_count": len(expired),
        "active_count": len(active),
        "expired_ids": expired,
    }
    print(json.dumps(report, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <enforce|anonymize|report> [args]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "enforce":
        enforce_retention()
    elif command == "anonymize":
        if len(sys.argv) < 3:
            print("Usage: python manage.py anonymize USER_ID")
            sys.exit(1)
        anonymize_user(sys.argv[2])
    elif command == "report":
        generate_report()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
