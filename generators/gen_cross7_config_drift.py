"""
Parameterized generator for CROSS7: Configuration Drift Reconciliation.

Each seed produces 3 microservices with different names, different drifted fields,
and different override rules. The reconcile.py script has 4 bugs that must be fixed.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


DOMAINS = [
    {
        # Seed 0: Web platform services
        "services": ["auth_service", "billing_service", "notification_service"],
        "canonical": {
            "log_level": "INFO",
            "max_retries": 3,
            "timeout_ms": 5000,
            "enable_cache": True,
            "cache_ttl_seconds": 300,
            "db_pool_size": 10,
            "rate_limit_rps": 100,
            "enable_metrics": True,
            "deprecated_legacy_mode": False,
            "deprecated_v1_compat": False,
        },
        "drifts": {
            "auth_service": {
                "added": {"jwt_expiry_seconds": 3600, "session_timeout_minutes": 30},
                "changed": {"timeout_ms": 10000},
                "removed": [],
            },
            "billing_service": {
                "added": {},
                "changed": {"max_retries": 5, "db_pool_size": 20, "rate_limit_rps": 50},
                "removed": [],
            },
            "notification_service": {
                "added": {},
                "changed": {"cache_ttl_seconds": 60},
                "removed": ["deprecated_legacy_mode", "deprecated_v1_compat"],
            },
        },
        "overrides": {
            "auth_service": {
                "keep_added": ["jwt_expiry_seconds", "session_timeout_minutes"],
                "keep_changed": ["timeout_ms"],
            },
            "billing_service": {
                "keep_added": [],
                "keep_changed": ["db_pool_size"],
            },
            "notification_service": {
                "keep_added": [],
                "keep_changed": [],
            },
        },
        "deprecated_fields": ["deprecated_legacy_mode", "deprecated_v1_compat"],
    },
    {
        # Seed 1: Data pipeline services
        "services": ["ingestion_service", "transform_service", "storage_service"],
        "canonical": {
            "log_level": "WARNING",
            "batch_size": 1000,
            "flush_interval_ms": 5000,
            "compression": "gzip",
            "enable_dedup": True,
            "max_queue_depth": 10000,
            "worker_threads": 4,
            "enable_telemetry": True,
            "deprecated_sync_mode": False,
            "deprecated_v1_format": False,
        },
        "drifts": {
            "ingestion_service": {
                "added": {"source_timeout_ms": 30000, "max_connections": 50},
                "changed": {"batch_size": 5000},
                "removed": [],
            },
            "transform_service": {
                "added": {},
                "changed": {"worker_threads": 8, "compression": "zstd", "flush_interval_ms": 1000},
                "removed": [],
            },
            "storage_service": {
                "added": {},
                "changed": {"max_queue_depth": 50000},
                "removed": ["deprecated_sync_mode", "deprecated_v1_format"],
            },
        },
        "overrides": {
            "ingestion_service": {
                "keep_added": ["source_timeout_ms", "max_connections"],
                "keep_changed": ["batch_size"],
            },
            "transform_service": {
                "keep_added": [],
                "keep_changed": ["worker_threads"],
            },
            "storage_service": {
                "keep_added": [],
                "keep_changed": [],
            },
        },
        "deprecated_fields": ["deprecated_sync_mode", "deprecated_v1_format"],
    },
    {
        # Seed 2: API gateway services
        "services": ["gateway_service", "routing_service", "cache_service"],
        "canonical": {
            "log_level": "DEBUG",
            "request_timeout_ms": 3000,
            "max_body_size_kb": 1024,
            "cors_enabled": True,
            "enable_rate_limit": True,
            "circuit_breaker_threshold": 5,
            "health_check_interval_s": 30,
            "enable_tracing": True,
            "deprecated_xml_support": False,
            "deprecated_soap_mode": False,
        },
        "drifts": {
            "gateway_service": {
                "added": {"ssl_cert_path": "/etc/ssl/gateway.pem", "proxy_buffer_kb": 256},
                "changed": {"request_timeout_ms": 10000},
                "removed": [],
            },
            "routing_service": {
                "added": {},
                "changed": {"circuit_breaker_threshold": 10, "health_check_interval_s": 10, "max_body_size_kb": 2048},
                "removed": [],
            },
            "cache_service": {
                "added": {},
                "changed": {"enable_tracing": "true"},
                "removed": ["deprecated_xml_support", "deprecated_soap_mode"],
            },
        },
        "overrides": {
            "gateway_service": {
                "keep_added": ["ssl_cert_path", "proxy_buffer_kb"],
                "keep_changed": ["request_timeout_ms"],
            },
            "routing_service": {
                "keep_added": [],
                "keep_changed": ["circuit_breaker_threshold"],
            },
            "cache_service": {
                "keep_added": [],
                "keep_changed": [],
            },
        },
        "deprecated_fields": ["deprecated_xml_support", "deprecated_soap_mode"],
    },
]


def _yaml_value(v) -> str:
    """Convert a Python value to YAML-compatible string."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        if " " in v or "/" in v:
            return f'"{v}"'
        return v
    return str(v)


class Generator(TaskGenerator):
    task_id = "CROSS7_config_drift"
    domain = "Operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        d = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(d, seed)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CROSS7_config_drift")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CROSS7_config_drift",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": [
                    "B1_override_per_service",
                    "B2_keep_added_fields",
                    "B3_skip_deprecated",
                    "B4_type_normalization",
                ],
                "seed": seed,
                "services": d["services"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Operations"},
        )

    def _make_workspace(self, d: dict, seed: int) -> dict:
        files = {}
        files["canonical_config.yaml"] = self._canonical(d)
        for svc in d["services"]:
            files[f"{svc}/config.yaml"] = self._service_config(d, svc)
        files["overrides.md"] = self._overrides_md(d)
        files["reconcile.py"] = self._reconcile(d)
        files["tests/__init__.py"] = ""
        files["tests/test_reconcile.py"] = self._tests(d)
        return files

    def _canonical(self, d: dict) -> str:
        lines = ["# Canonical shared configuration\n"]
        for k, v in d["canonical"].items():
            lines.append(f"{k}: {_yaml_value(v)}")
        return "\n".join(lines) + "\n"

    def _service_config(self, d: dict, svc: str) -> str:
        drift = d["drifts"][svc]
        config = dict(d["canonical"])
        # Apply changes
        for k, v in drift["changed"].items():
            config[k] = v
        # Remove deprecated
        for k in drift["removed"]:
            config.pop(k, None)
        # Add new fields
        for k, v in drift.get("added", {}).items():
            config[k] = v

        lines = [f"# {svc} configuration\n"]
        for k, v in config.items():
            lines.append(f"{k}: {_yaml_value(v)}")
        return "\n".join(lines) + "\n"

    def _overrides_md(self, d: dict) -> str:
        lines = ["# Service Configuration Overrides\n"]
        lines.append("This document specifies which configuration deviations are")
        lines.append("intentional and must be preserved during reconciliation.\n")

        for svc in d["services"]:
            ov = d["overrides"][svc]
            lines.append(f"## {svc}\n")
            if ov["keep_added"]:
                lines.append("### Service-Specific Additions")
                lines.append("These fields are unique to this service and must be kept:\n")
                for field in ov["keep_added"]:
                    val = d["drifts"][svc]["added"][field]
                    lines.append(f"- `{field}`: {_yaml_value(val)}")
                lines.append("")
            if ov["keep_changed"]:
                lines.append("### Intentional Overrides")
                lines.append("These values differ from canonical intentionally:\n")
                for field in ov["keep_changed"]:
                    val = d["drifts"][svc]["changed"][field]
                    lines.append(f"- `{field}`: {_yaml_value(val)} (canonical: {_yaml_value(d['canonical'][field])})")
                lines.append("")
            if not ov["keep_added"] and not ov["keep_changed"]:
                lines.append("No intentional overrides. All deviations should be reverted to canonical.\n")

        lines.append("## Deprecated Fields\n")
        lines.append("The following fields are deprecated and should NOT be re-added")
        lines.append("to services that have removed them:\n")
        for field in d["deprecated_fields"]:
            lines.append(f"- `{field}`")
        lines.append("")
        return "\n".join(lines)

    def _reconcile(self, d: dict) -> str:
        svcs_repr = ", ".join(f'"{s}"' for s in d["services"])
        return f'''"""
Configuration reconciliation script.

Reads canonical config and each service's config, then reconciles them
according to override rules. Contains 4 bugs.
"""
import yaml
import os
import sys


SERVICES = [{svcs_repr}]


def load_yaml(path: str) -> dict:
    """Load a YAML file and return as dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path: str, data: dict) -> None:
    """Save a dict as YAML."""
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def parse_overrides(overrides_path: str) -> dict:
    """Parse overrides.md to extract per-service override info.

    Returns dict like:
        {{
            "service_name": {{
                "keep_added": ["field1", ...],
                "keep_changed": ["field2", ...],
            }},
            "deprecated": ["field3", ...],
        }}
    """
    result = {{"deprecated": []}}
    current_service = None
    current_section = None

    with open(overrides_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("## ") and not line.startswith("## Deprecated"):
                current_service = line[3:].strip()
                result[current_service] = {{"keep_added": [], "keep_changed": []}}
                current_section = None
            elif line.startswith("## Deprecated"):
                current_service = None
                current_section = "deprecated"
            elif line.startswith("### Service-Specific Additions"):
                current_section = "keep_added"
            elif line.startswith("### Intentional Overrides"):
                current_section = "keep_changed"
            elif line.startswith("- `") and "`" in line[3:]:
                field_name = line[3:line.index("`", 3)]
                if current_section == "deprecated":
                    result["deprecated"].append(field_name)
                elif current_service and current_section:
                    result[current_service][current_section].append(field_name)

    return result


def reconcile_service(
    canonical: dict,
    service_config: dict,
    service_name: str,
    overrides: dict,
) -> dict:
    """Reconcile a single service config against canonical.

    Bug 1: Checks if key is in ANY service's overrides, not just this service's.
    Bug 2: Deletes service-added fields even if listed in keep_added.
    Bug 3: Re-adds deprecated fields from canonical.
    Bug 4: Compares with == without normalizing types (string "true" != bool True).
    """
    result = dict(service_config)
    deprecated = overrides.get("deprecated", [])

    # Collect ALL override fields across all services (Bug 1: should be per-service)
    all_override_fields = set()
    for svc_key, svc_ov in overrides.items():
        if svc_key == "deprecated":
            continue
        if isinstance(svc_ov, dict):
            all_override_fields.update(svc_ov.get("keep_changed", []))

    # Step 1: Revert drifted values to canonical (unless overridden)
    for key, canonical_val in canonical.items():
        if key in result and result[key] != canonical_val:
            # Bug 1: checks all_override_fields instead of this service's overrides
            if key in all_override_fields:
                pass  # Keep the override
            else:
                # Bug 4: no type normalization — string "true" != bool True
                result[key] = canonical_val

    # Step 2: Add missing canonical fields to service
    for key, canonical_val in canonical.items():
        if key not in result:
            # Bug 3: re-adds deprecated fields that were intentionally removed
            result[key] = canonical_val

    # Step 3: Remove fields not in canonical (unless service-specific addition)
    keys_to_remove = []
    for key in result:
        if key not in canonical:
            # Bug 2: always removes extra keys (should check keep_added for this service)
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del result[key]

    return result


def main():
    """Main reconciliation entry point."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    canonical = load_yaml(os.path.join(base_dir, "canonical_config.yaml"))
    overrides = parse_overrides(os.path.join(base_dir, "overrides.md"))

    results = {{}}
    for svc in SERVICES:
        svc_config = load_yaml(os.path.join(base_dir, svc, "config.yaml"))
        results[svc] = reconcile_service(canonical, svc_config, svc, overrides)
        save_yaml(os.path.join(base_dir, svc, "config.yaml"), results[svc])
        print(f"Reconciled {{svc}}")

    return results


if __name__ == "__main__":
    main()
'''

    def _tests(self, d: dict) -> str:
        svc0, svc1, svc2 = d["services"]
        ov0 = d["overrides"][svc0]
        ov1 = d["overrides"][svc1]
        ov2 = d["overrides"][svc2]
        drift0 = d["drifts"][svc0]
        drift1 = d["drifts"][svc1]
        drift2 = d["drifts"][svc2]

        # Build expected results for each service
        # svc0: has added fields (keep) and changed field (keep one, revert others)
        # svc1: has changed fields (keep some, revert others)
        # svc2: has removed deprecated (keep removed) and changed field (revert)
        dep_fields = d["deprecated_fields"]

        # svc0 changed fields to revert
        svc0_revert = {k: d["canonical"][k] for k in drift0["changed"] if k not in ov0["keep_changed"]}
        svc0_keep_changed = {k: drift0["changed"][k] for k in ov0["keep_changed"]}
        svc0_keep_added = {k: drift0["added"][k] for k in ov0["keep_added"]}

        # svc1 changed fields to revert
        svc1_revert = {k: d["canonical"][k] for k in drift1["changed"] if k not in ov1["keep_changed"]}
        svc1_keep_changed = {k: drift1["changed"][k] for k in ov1["keep_changed"]}

        # svc2 changed fields to revert
        svc2_revert = {k: d["canonical"][k] for k in drift2["changed"] if k not in ov2["keep_changed"]}

        # Helper to generate assertion lines
        def _assert_val(varname, key, val):
            if isinstance(val, bool):
                py_val = "True" if val else "False"
                return f'    assert {varname}["{key}"] is {py_val}, f"{key} should be {py_val}, got {{{varname}[\\"{key}\\\"]}}"\n'
            elif isinstance(val, str):
                return f'    assert str({varname}["{key}"]) == "{val}", f"{key} should be {val}, got {{{varname}[\\"{key}\\\"]}}"\n'
            else:
                return f'    assert {varname}["{key}"] == {val}, f"{key} should be {val}, got {{{varname}[\\"{key}\\\"]}}"\n'

        # Type normalization test needs the service with string "true" drift
        type_norm_svc = None
        type_norm_field = None
        for svc in d["services"]:
            for k, v in d["drifts"][svc]["changed"].items():
                if isinstance(v, str) and v.lower() in ("true", "false"):
                    type_norm_svc = svc
                    type_norm_field = k

        return f'''"""
Tests for reconcile.py — validates all 4 bug fixes.
"""
import os
import sys
import pytest
import yaml

# Add parent to path so we can import reconcile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reconcile import load_yaml, parse_overrides, reconcile_service


@pytest.fixture
def base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def canonical(base_dir):
    return load_yaml(os.path.join(base_dir, "canonical_config.yaml"))


@pytest.fixture
def overrides(base_dir):
    return parse_overrides(os.path.join(base_dir, "overrides.md"))


@pytest.fixture
def svc0_config(base_dir):
    return load_yaml(os.path.join(base_dir, "{svc0}", "config.yaml"))


@pytest.fixture
def svc1_config(base_dir):
    return load_yaml(os.path.join(base_dir, "{svc1}", "config.yaml"))


@pytest.fixture
def svc2_config(base_dir):
    return load_yaml(os.path.join(base_dir, "{svc2}", "config.yaml"))


class TestBug1OverridePerService:
    """Bug 1: Override check must be per-service, not global."""

    def test_{svc1}_non_override_reverted(self, canonical, svc1_config, overrides):
        """Fields changed by {svc1} but NOT in its overrides must revert."""
        result = reconcile_service(canonical, svc1_config, "{svc1}", overrides)
        # These fields were changed by {svc1} but are NOT in its keep_changed
        # They should revert to canonical even though other services override them
{chr(10).join(_assert_val("result", k, v) for k, v in svc1_revert.items())}

    def test_{svc0}_override_preserved(self, canonical, svc0_config, overrides):
        """Fields listed in {svc0}'s overrides must be kept."""
        result = reconcile_service(canonical, svc0_config, "{svc0}", overrides)
{chr(10).join(_assert_val("result", k, v) for k, v in svc0_keep_changed.items())}


class TestBug2KeepAddedFields:
    """Bug 2: Service-specific additions listed in overrides must be kept."""

    def test_{svc0}_added_fields_kept(self, canonical, svc0_config, overrides):
        result = reconcile_service(canonical, svc0_config, "{svc0}", overrides)
{chr(10).join(_assert_val("result", k, v) for k, v in svc0_keep_added.items())}

    def test_{svc0}_added_fields_present(self, canonical, svc0_config, overrides):
        result = reconcile_service(canonical, svc0_config, "{svc0}", overrides)
        for field in {list(svc0_keep_added.keys())}:
            assert field in result, f"{{field}} should be present in {svc0} config"


class TestBug3SkipDeprecated:
    """Bug 3: Deprecated fields must not be re-added to services that removed them."""

    def test_{svc2}_deprecated_not_readded(self, canonical, svc2_config, overrides):
        result = reconcile_service(canonical, svc2_config, "{svc2}", overrides)
        for field in {dep_fields}:
            assert field not in result, (
                f"deprecated field '{{field}}' must NOT be re-added to {svc2}"
            )

    def test_{svc0}_still_has_deprecated(self, canonical, svc0_config, overrides):
        """Services that still have deprecated fields should keep them (not removed from canonical)."""
        result = reconcile_service(canonical, svc0_config, "{svc0}", overrides)
        for field in {dep_fields}:
            assert field in result, (
                f"{{field}} should still be in {svc0} (it was not removed)"
            )


class TestBug4TypeNormalization:
    """Bug 4: Type coercion — string 'true' should match boolean True."""

    def test_type_normalized_comparison(self, canonical, overrides):
        """Config with string 'true' vs canonical bool True must be treated as equal."""
        test_config = dict(canonical)
        # Simulate string vs bool drift
        bool_key = None
        for k, v in canonical.items():
            if isinstance(v, bool):
                bool_key = k
                break
        if bool_key:
            test_config[bool_key] = "true" if canonical[bool_key] else "false"
            result = reconcile_service(canonical, test_config, "test_svc", overrides)
            # After normalization, the value should be the canonical boolean
            assert result[bool_key] is canonical[bool_key] or str(result[bool_key]).lower() == str(canonical[bool_key]).lower(), (
                f"Type normalization failed: {{result[bool_key]!r}} vs {{canonical[bool_key]!r}}"
            )


class TestFullReconciliation:
    """End-to-end reconciliation tests."""

    def test_all_services_have_canonical_keys(self, canonical, svc0_config, svc1_config, svc2_config, overrides):
        """After reconciliation, all services must have all non-deprecated canonical keys."""
        deprecated = overrides.get("deprecated", [])
        for svc_name, svc_config in [("{svc0}", svc0_config), ("{svc1}", svc1_config), ("{svc2}", svc2_config)]:
            result = reconcile_service(canonical, svc_config, svc_name, overrides)
            for key in canonical:
                if key in deprecated and key not in svc_config:
                    continue  # Deprecated and already removed
                assert key in result, f"{{key}} missing from {{svc_name}} after reconciliation"

    def test_output_is_valid_yaml(self, canonical, svc0_config, overrides):
        result = reconcile_service(canonical, svc0_config, "{svc0}", overrides)
        # Should be serializable as YAML
        yaml_str = yaml.dump(result)
        loaded = yaml.safe_load(yaml_str)
        assert loaded == result
'''
