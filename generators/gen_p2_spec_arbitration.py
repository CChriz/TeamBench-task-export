"""
Parameterized generator for P2: Spec Arbitration (Conflicting Requirements).

Each seed produces:
  - Different config key names (not always cache_ttl etc.)
  - 3 spec documents with varying priority classes and conflicts
  - Priority rules that vary which class beats which
  - A footnote/exception that overrides one priority rule for one key
  - expected.json with the resolved config

The task structure stays the same: read corpus/, apply priority rules, resolve conflicts,
produce output/resolved_config.json with exactly N keys.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Config key pools grouped by domain
CONFIG_KEY_POOLS = [
    # (key_name, description, value_type)
    # Performance/cache keys
    ("cache_ttl", "cache TTL in seconds", "int"),
    ("request_timeout", "request timeout in ms", "int"),
    ("max_connections", "maximum connections", "int"),
    ("pool_size", "connection pool size", "int"),
    ("batch_size", "batch processing size", "int"),
    ("queue_depth", "max queue depth", "int"),
    # Security keys
    ("max_payload_mb", "max payload size in MB", "int"),
    ("session_timeout", "session timeout in minutes", "int"),
    ("token_expiry", "token expiry in seconds", "int"),
    ("max_retries", "maximum retry attempts", "int"),
    # Feature flags (bool)
    ("backup_enabled", "backup feature flag", "bool"),
    ("compression_enabled", "compression feature flag", "bool"),
    ("audit_logging", "audit logging flag", "bool"),
    ("rate_limiting", "rate limiting flag", "bool"),
    # String/enum keys
    ("compression", "compression algorithm", "str"),
    ("encryption", "encryption algorithm", "str"),
    ("log_format", "log output format", "str"),
    ("auth_method", "authentication method", "str"),
    # Retention/duration keys
    ("log_retention_days", "log retention in days", "int"),
    ("retry_timeout", "retry timeout in seconds", "int"),
    ("backup_interval_hours", "backup interval in hours", "int"),
    ("metrics_window_sec", "metrics window in seconds", "int"),
]

# Priority class pools
PRIORITY_CLASSES = [
    ["security", "performance", "monitoring", "convenience", "operations"],
    ["security", "reliability", "observability", "usability", "maintenance"],
    ["compliance", "performance", "monitoring", "convenience", "operations"],
    ["security", "performance", "logging", "developer_experience", "cost"],
]

# Value sets for string keys
STR_VALUE_SETS = {
    "compression": [("gzip", "zstd", "none"), ("lz4", "snappy", "none"), ("brotli", "gzip", "none")],
    "encryption": [("aes256", "aes128", "none"), ("chacha20", "aes256", "none"), ("rsa2048", "aes256", "none")],
    "log_format": [("json", "text", "csv"), ("json", "syslog", "plain"), ("structured", "json", "raw")],
    "auth_method": [("jwt", "oauth2", "basic"), ("saml", "jwt", "apikey"), ("mtls", "jwt", "none")],
}

# Footnote exception templates
FOOTNOTE_TEMPLATES = [
    (
        "Exception: For `{key}`, operational stability takes precedence regardless of the "
        "standard priority hierarchy. This means when evaluating `{key}`, prefer the value "
        "that provides greater operational stability, even if it would not normally win under "
        "the standard priority rules."
    ),
    (
        "Exception: The `{key}` field follows a separate negotiation protocol. "
        "When conflict exists, always apply the value from the spec with the LOWEST priority class "
        "for this specific field. This overrides the standard resolution order."
    ),
    (
        "Special case: `{key}` is subject to a legacy compatibility requirement. "
        "Regardless of priority class, always use the higher numeric value for this field "
        "to preserve backward compatibility with existing integrations."
    ),
]


def _pick_int_values(rng: SeededRandom, n: int, low: int, high: int) -> list[int]:
    """Pick n distinct integers in [low, high]."""
    vals = set()
    while len(vals) < n:
        vals.add(rng.randint(low, high))
    return sorted(vals, reverse=True)[:n]


class Generator(TaskGenerator):
    task_id = "P2_spec_arbitration"
    domain = "policy"
    difficulty = "medium"
    languages = ["json"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick priority class ordering for this seed
        priority_order = rng.choice(PRIORITY_CLASSES)
        # priority_order[0] beats all, priority_order[1] beats [2:], etc.

        # Pick 8 config keys (4 conflicting across specs, 4 non-conflicting singletons)
        all_keys = list(CONFIG_KEY_POOLS)
        rng.shuffle(all_keys)
        selected_keys = all_keys[:8]

        # Assign keys to categories: 3 conflict between spec-A & spec-B,
        # 2 conflict between spec-B & spec-C, 1 non-conflict singleton each spec
        # and one key gets the footnote exception
        conflict_ab = selected_keys[0:2]   # spec-A vs spec-B
        conflict_bc = selected_keys[2:4]   # spec-B vs spec-C
        only_a = selected_keys[4]          # only in spec-A
        only_b = selected_keys[5]          # only in spec-B
        only_c = selected_keys[6]          # only in spec-C
        exception_key_entry = selected_keys[7]  # gets the footnote exception

        # Priority class for each spec
        spec_a_class = priority_order[0]   # highest priority
        spec_b_class = priority_order[1]   # second
        spec_c_class = priority_order[2]   # third

        def pick_value(key_entry, rng: SeededRandom):
            key_name, _, vtype = key_entry
            if vtype == "int":
                return rng.randint(10, 200) * 5
            elif vtype == "bool":
                return rng.choice([True, False])
            else:  # str
                base = key_name.split("_")[0] if "_" in key_name else key_name
                vset_key = None
                for k in STR_VALUE_SETS:
                    if k in key_name:
                        vset_key = k
                        break
                if vset_key:
                    opts = rng.choice(STR_VALUE_SETS[vset_key])
                    return rng.choice(list(opts))
                return rng.choice(["enabled", "disabled", "auto"])

        # Build values for each spec
        # conflict_ab[0]: spec-A wins (higher priority)
        ca0_a_val = pick_value(conflict_ab[0], rng)
        ca0_b_val = pick_value(conflict_ab[0], rng)
        while ca0_b_val == ca0_a_val:
            ca0_b_val = pick_value(conflict_ab[0], rng)

        # conflict_ab[1]: spec-A wins
        ca1_a_val = pick_value(conflict_ab[1], rng)
        ca1_b_val = pick_value(conflict_ab[1], rng)
        while ca1_b_val == ca1_a_val:
            ca1_b_val = pick_value(conflict_ab[1], rng)

        # conflict_bc[0]: spec-B wins (higher priority than C)
        cb0_b_val = pick_value(conflict_bc[0], rng)
        cb0_c_val = pick_value(conflict_bc[0], rng)
        while cb0_c_val == cb0_b_val:
            cb0_c_val = pick_value(conflict_bc[0], rng)

        # conflict_bc[1]: this is the exception key — footnote overrides normal priority
        # exception_key_entry is selected_keys[7]; conflict_bc[1] is selected_keys[3]
        cb1_b_val = pick_value(conflict_bc[1], rng)
        cb1_c_val = pick_value(conflict_bc[1], rng)
        while cb1_c_val == cb1_b_val:
            cb1_c_val = pick_value(conflict_bc[1], rng)
        # C would normally lose but exception makes C win
        # We'll make the exception key be conflict_bc[1]
        exception_key_name = conflict_bc[1][0]
        # Normal resolution: spec-B (higher) would win -> cb1_b_val
        # Exception resolution: spec-C (lower, "operational stability") wins -> cb1_c_val
        exception_resolved = cb1_c_val

        # Singleton values
        only_a_val = pick_value(only_a, rng)
        only_b_val = pick_value(only_b, rng)
        only_c_val = pick_value(only_c, rng)

        # Exception key value (separate key for spec A-level singleton)
        exc_a_val = pick_value(exception_key_entry, rng)

        # Build resolved config (what agent must produce)
        resolved = {}
        resolved[conflict_ab[0][0]] = ca0_a_val      # spec-A wins vs B
        resolved[conflict_ab[1][0]] = ca1_a_val      # spec-A wins vs B
        resolved[conflict_bc[0][0]] = cb0_b_val      # spec-B wins vs C
        resolved[conflict_bc[1][0]] = exception_resolved  # exception: C wins
        resolved[only_a[0]] = only_a_val
        resolved[only_b[0]] = only_b_val
        resolved[only_c[0]] = only_c_val
        resolved[exception_key_entry[0]] = exc_a_val  # only in spec-A

        # Pick footnote template
        footnote_tmpl = rng.choice(FOOTNOTE_TEMPLATES)
        footnote_text = footnote_tmpl.format(key=exception_key_name)

        # Build corpus documents
        spec_a_lines = [
            f"=== SPEC-A ({spec_a_class.title()} & Performance) ===",
            f"Priority class: {spec_a_class}, performance",
            "",
        ]
        def fmt_val(v):
            if isinstance(v, bool):
                return str(v).lower()
            return str(v)

        spec_a_lines.append(f"{conflict_ab[0][0]} = {fmt_val(ca0_a_val)}  # {spec_a_class}: {conflict_ab[0][1]}")
        spec_a_lines.append(f"{conflict_ab[1][0]} = {fmt_val(ca1_a_val)}  # {spec_a_class}: {conflict_ab[1][1]}")
        spec_a_lines.append(f"{only_a[0]} = {fmt_val(only_a_val)}  # {spec_a_class}: {only_a[1]}")
        spec_a_lines.append(f"{exception_key_entry[0]} = {fmt_val(exc_a_val)}  # {spec_a_class}: {exception_key_entry[1]}")

        spec_b_lines = [
            f"=== SPEC-B (Performance & {spec_b_class.title()}) ===",
            f"Priority class: performance, {spec_b_class}",
            "",
        ]
        spec_b_lines.append(f"{conflict_ab[0][0]} = {fmt_val(ca0_b_val)}  # Freshness: always serve latest (CONFLICTS with Spec-A)")
        spec_b_lines.append(f"{conflict_ab[1][0]} = {fmt_val(ca1_b_val)}  # Performance: allow retries (CONFLICTS with Spec-A)")
        spec_b_lines.append(f"{conflict_bc[0][0]} = {fmt_val(cb0_b_val)}  # Performance: {conflict_bc[0][1]}")
        spec_b_lines.append(f"{conflict_bc[1][0]} = {fmt_val(cb1_b_val)}  # {spec_b_class.title()}: {conflict_bc[1][1]} (CONFLICTS with Spec-C)")
        spec_b_lines.append(f"{only_b[0]} = {fmt_val(only_b_val)}  # {spec_b_class.title()}: {only_b[1]}")

        spec_c_lines = [
            f"=== SPEC-C (Convenience & {spec_c_class.title()}) ===",
            f"Priority class: convenience, {spec_c_class}",
            "",
        ]
        spec_c_lines.append(f"{conflict_bc[0][0]} = {fmt_val(cb0_c_val)}  # Convenience: simplify (CONFLICTS with Spec-B)")
        spec_c_lines.append(f"{conflict_bc[1][0]} = {fmt_val(cb1_c_val)}  # Convenience: {conflict_bc[1][1]} (CONFLICTS with Spec-B)")
        spec_c_lines.append(f"{only_c[0]} = {fmt_val(only_c_val)}  # {spec_c_class.title()}: {only_c[1]}")

        requirements_txt = "\n".join(spec_a_lines) + "\n\n" + "\n".join(spec_b_lines) + "\n\n" + "\n".join(spec_c_lines) + "\n"

        # Build priority rules document
        p0, p1, p2, p3, p4 = (priority_order + ["operations", "maintenance"])[:5]
        priority_rules_txt = f"""=== CONFLICT RESOLUTION PRIORITY ===

When specifications conflict, apply these rules in order:

1. {p0.title()} specs ALWAYS override all other categories.
   ({p0} > {p1} > {p2} > {p3} > {p4})

2. {p1.title()} specs override freshness, convenience, and {p3} specs.

3. {p2.title()} specs override {p3} and {p4} specs.

4. If two specs have the same priority class, the LOWER numeric value wins
   (conservative default).

=== EXAMPLES ===

- {conflict_ab[0][0]}: Spec-A ({spec_a_class}) vs Spec-B (freshness) \u2192 {spec_a_class.title()} wins \u2192 {fmt_val(ca0_a_val)}
- {conflict_bc[0][0]}: Spec-B (performance) vs Spec-C (convenience) \u2192 Performance wins \u2192 {fmt_val(cb0_b_val)}
- {conflict_ab[1][0]}: Spec-A ({spec_a_class}) vs Spec-B ({spec_b_class}) \u2192 {spec_a_class.title()} wins \u2192 {fmt_val(ca1_a_val)}

=== FOOTNOTES ===

{footnote_text}
"""

        # Buggy starting config (all wrong)
        buggy_resolved = {}
        for k, v in resolved.items():
            if isinstance(v, int):
                buggy_resolved[k] = v + rng.randint(1, 50)
            elif isinstance(v, bool):
                buggy_resolved[k] = not v
            else:
                buggy_resolved[k] = "wrong_value"

        corpus_files = {
            "requirements.txt": requirements_txt,
            "priority_rules.txt": priority_rules_txt,
        }

        workspace_files = {
            "resolved_config.json": json.dumps(buggy_resolved, indent=2) + "\n",
        }

        expected = {
            "resolved_config": resolved,
            "key_count": 8,
            "conflict_resolutions": {
                conflict_ab[0][0]: {"winner": "spec-A", "reason": f"{spec_a_class} > performance"},
                conflict_ab[1][0]: {"winner": "spec-A", "reason": f"{spec_a_class} > {spec_b_class}"},
                conflict_bc[0][0]: {"winner": "spec-B", "reason": "performance > convenience"},
                conflict_bc[1][0]: {"winner": "spec-C", "reason": "footnote exception overrides standard priority"},
            },
            "exception_key": exception_key_name,
            "exception_value": exception_resolved,
        }

        spec_md = self._generate_spec(
            key_count=len(resolved),
            priority_order=priority_order,
            exception_key_name=exception_key_name,
            key_names=sorted(resolved.keys()),
        )
        brief_md = self._generate_brief()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
        )

    def _generate_spec(self, key_count: int, priority_order: list[str],
                       exception_key_name: str, key_names: list[str]) -> str:
        top_priority = priority_order[0]
        keys_str = ", ".join(f"`{k}`" for k in key_names)
        return f"""# P2: Spec Arbitration (Conflicting Requirements)

## Goal
Resolve conflicting requirements using the priority rules defined in the corpus,
then produce a configuration that satisfies the highest-priority rules.

## Context
This deployment involves {key_count} configuration keys: {keys_str}.
The highest priority class is "{top_priority}". Note that the field `{exception_key_name}` has
a documented exception in the priority rules that overrides normal resolution.

## Hard Requirements

1. Produce `output/resolved_config.json`.
2. Read the source documents in `corpus/` to identify all requirements and any conflicts between them.
3. Apply the priority rules from `corpus/priority_rules.txt` to resolve each conflict. Where two specs disagree on a value, the higher-priority spec's value wins.
4. Note that priority rules may have documented exceptions or special cases — these must be respected when resolving specific fields.
5. Non-conflicting values from any spec must be included as-is.
6. Output must have exactly {key_count} keys covering all fields from across the specs.

## Requirements Sources

Read the documents in `corpus/` to obtain all requirements and priority rules. The Planner must derive the resolved values for each key by applying the priority rules to the conflicting specs — the resolution must not be assumed.

## Deliverables
- `output/resolved_config.json` in workspace.
- Verifier must confirm each resolved value traces to the correct priority rule and produce attestation.
"""

    def _generate_brief(self) -> str:
        return """# P2: Spec Arbitration (Brief)

Resolve conflicting requirements from multiple spec documents.
The Planner has the priority rules and full requirements — ask the Planner for conflict resolution guidance.
Produce `output/resolved_config.json`.
"""
