"""
Parameterized generator for SPEC7: Configuration Schema Validator.

Each seed produces a different config domain with 15 fields, 5 cross-field
constraints, and a skeleton validator to implement.
"""
from __future__ import annotations
import json
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOMAINS = [
    {
        "name": "database_cluster",
        "fields": {
            "host": {"type": "string", "description": "Database host address"},
            "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
            "mode": {"type": "string", "enum": ["standalone", "cluster", "replica"]},
            "replicas": {"type": "integer", "minimum": 0, "maximum": 100},
            "max_connections": {"type": "integer", "minimum": 1, "maximum": 10000},
            "ssl_enabled": {"type": "boolean"},
            "cert_path": {"type": "string"},
            "log_level": {"type": "string", "enum": ["debug", "info", "warn", "error"]},
            "cache_size_mb": {"type": "integer", "minimum": 16, "maximum": 4096},
            "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300},
            "retry_count": {"type": "integer", "minimum": 0, "maximum": 10},
            "backup_enabled": {"type": "boolean"},
            "backup_interval_hours": {"type": "integer", "minimum": 1, "maximum": 168},
            "compression": {"type": "string", "enum": ["none", "gzip", "lz4", "zstd"]},
            "data_dir": {"type": "string"},
        },
        "required": ["host", "port", "mode", "max_connections", "log_level", "data_dir"],
        "cross_field": [
            {"if_field": "mode", "if_value": "cluster", "then_field": "replicas", "then_min": 3,
             "desc": "cluster mode requires replicas >= 3"},
            {"if_field": "ssl_enabled", "if_value": True, "then_field": "cert_path", "then_required": True,
             "desc": "ssl requires cert_path"},
            {"if_field": "backup_enabled", "if_value": True, "then_field": "backup_interval_hours", "then_required": True,
             "desc": "backup requires backup_interval_hours"},
            {"if_field": "mode", "if_value": "replica", "then_field": "log_level", "then_enum": ["info", "warn", "error"],
             "desc": "replica mode cannot use debug log level"},
            {"if_field": "compression", "if_value": "zstd", "then_field": "cache_size_mb", "then_min": 128,
             "desc": "zstd compression requires cache >= 128MB"},
        ],
        "valid_config": {
            "host": "db.example.com", "port": 5432, "mode": "cluster", "replicas": 5,
            "max_connections": 500, "ssl_enabled": True, "cert_path": "/etc/ssl/db.pem",
            "log_level": "info", "cache_size_mb": 256, "timeout_seconds": 30,
            "retry_count": 3, "backup_enabled": True, "backup_interval_hours": 24,
            "compression": "zstd", "data_dir": "/var/lib/db",
        },
        "invalid_config": {
            "host": "db.example.com", "port": 99999, "mode": "cluster", "replicas": 1,
            "max_connections": -5, "ssl_enabled": True,
            "log_level": "trace", "cache_size_mb": 8, "timeout_seconds": 500,
            "retry_count": 3, "backup_enabled": True,
            "compression": "zstd", "data_dir": "/var/lib/db",
        },
    },
    {
        "name": "message_queue",
        "fields": {
            "broker_url": {"type": "string", "description": "Message broker URL"},
            "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
            "mode": {"type": "string", "enum": ["standalone", "cluster", "mirror"]},
            "replicas": {"type": "integer", "minimum": 0, "maximum": 50},
            "queue_max_size": {"type": "integer", "minimum": 100, "maximum": 1000000},
            "ssl_enabled": {"type": "boolean"},
            "cert_path": {"type": "string"},
            "log_level": {"type": "string", "enum": ["debug", "info", "warn", "error"]},
            "prefetch_count": {"type": "integer", "minimum": 1, "maximum": 1000},
            "ack_timeout_ms": {"type": "integer", "minimum": 100, "maximum": 60000},
            "retry_count": {"type": "integer", "minimum": 0, "maximum": 20},
            "dlq_enabled": {"type": "boolean"},
            "dlq_max_retries": {"type": "integer", "minimum": 1, "maximum": 100},
            "serialization": {"type": "string", "enum": ["json", "msgpack", "protobuf", "avro"]},
            "storage_path": {"type": "string"},
        },
        "required": ["broker_url", "port", "mode", "queue_max_size", "log_level", "storage_path"],
        "cross_field": [
            {"if_field": "mode", "if_value": "cluster", "then_field": "replicas", "then_min": 3,
             "desc": "cluster mode requires replicas >= 3"},
            {"if_field": "ssl_enabled", "if_value": True, "then_field": "cert_path", "then_required": True,
             "desc": "ssl requires cert_path"},
            {"if_field": "dlq_enabled", "if_value": True, "then_field": "dlq_max_retries", "then_required": True,
             "desc": "DLQ requires dlq_max_retries"},
            {"if_field": "mode", "if_value": "mirror", "then_field": "log_level", "then_enum": ["info", "warn", "error"],
             "desc": "mirror mode cannot use debug log level"},
            {"if_field": "serialization", "if_value": "protobuf", "then_field": "prefetch_count", "then_min": 10,
             "desc": "protobuf serialization requires prefetch >= 10"},
        ],
        "valid_config": {
            "broker_url": "amqp://mq.example.com", "port": 5672, "mode": "cluster", "replicas": 5,
            "queue_max_size": 50000, "ssl_enabled": True, "cert_path": "/etc/ssl/mq.pem",
            "log_level": "info", "prefetch_count": 50, "ack_timeout_ms": 5000,
            "retry_count": 5, "dlq_enabled": True, "dlq_max_retries": 10,
            "serialization": "protobuf", "storage_path": "/var/lib/mq",
        },
        "invalid_config": {
            "broker_url": "amqp://mq.example.com", "port": 80000, "mode": "cluster", "replicas": 1,
            "queue_max_size": 50, "ssl_enabled": True,
            "log_level": "trace", "prefetch_count": 2, "ack_timeout_ms": 100000,
            "retry_count": 5, "dlq_enabled": True,
            "serialization": "protobuf", "storage_path": "/var/lib/mq",
        },
    },
    {
        "name": "cache_server",
        "fields": {
            "bind_address": {"type": "string", "description": "Cache server bind address"},
            "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
            "mode": {"type": "string", "enum": ["standalone", "cluster", "sentinel"]},
            "replicas": {"type": "integer", "minimum": 0, "maximum": 30},
            "max_memory_mb": {"type": "integer", "minimum": 64, "maximum": 65536},
            "ssl_enabled": {"type": "boolean"},
            "cert_path": {"type": "string"},
            "log_level": {"type": "string", "enum": ["debug", "info", "warn", "error"]},
            "eviction_policy": {"type": "string", "enum": ["lru", "lfu", "random", "ttl"]},
            "ttl_seconds": {"type": "integer", "minimum": 1, "maximum": 86400},
            "retry_count": {"type": "integer", "minimum": 0, "maximum": 10},
            "persistence_enabled": {"type": "boolean"},
            "snapshot_interval_min": {"type": "integer", "minimum": 1, "maximum": 1440},
            "compression": {"type": "string", "enum": ["none", "snappy", "lz4", "zstd"]},
            "data_dir": {"type": "string"},
        },
        "required": ["bind_address", "port", "mode", "max_memory_mb", "log_level", "data_dir"],
        "cross_field": [
            {"if_field": "mode", "if_value": "cluster", "then_field": "replicas", "then_min": 3,
             "desc": "cluster mode requires replicas >= 3"},
            {"if_field": "ssl_enabled", "if_value": True, "then_field": "cert_path", "then_required": True,
             "desc": "ssl requires cert_path"},
            {"if_field": "persistence_enabled", "if_value": True, "then_field": "snapshot_interval_min", "then_required": True,
             "desc": "persistence requires snapshot_interval_min"},
            {"if_field": "mode", "if_value": "sentinel", "then_field": "log_level", "then_enum": ["info", "warn", "error"],
             "desc": "sentinel mode cannot use debug log level"},
            {"if_field": "compression", "if_value": "zstd", "then_field": "max_memory_mb", "then_min": 256,
             "desc": "zstd compression requires max_memory >= 256MB"},
        ],
        "valid_config": {
            "bind_address": "0.0.0.0", "port": 6379, "mode": "cluster", "replicas": 6,
            "max_memory_mb": 1024, "ssl_enabled": True, "cert_path": "/etc/ssl/cache.pem",
            "log_level": "warn", "eviction_policy": "lru", "ttl_seconds": 3600,
            "retry_count": 3, "persistence_enabled": True, "snapshot_interval_min": 60,
            "compression": "zstd", "data_dir": "/var/lib/cache",
        },
        "invalid_config": {
            "bind_address": "0.0.0.0", "port": 999, "mode": "cluster", "replicas": 1,
            "max_memory_mb": 32, "ssl_enabled": True,
            "log_level": "debug", "eviction_policy": "fifo", "ttl_seconds": 100000,
            "retry_count": 3, "persistence_enabled": True,
            "compression": "zstd", "data_dir": "/var/lib/cache",
        },
    },
]


class Generator(TaskGenerator):
    task_id = "SPEC7_config_schema"
    domain = "SWE"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        d = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(d, rng)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "SPEC7_config_schema")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="SPEC7_config_schema",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": d["name"],
                "field_count": 15,
                "cross_field_count": 5,
                "required_count": len(d["required"]),
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "SWE"},
        )

    def _make_workspace(self, d: dict, rng: SeededRandom) -> dict:
        files = {}

        files["config_schema.json"] = self._schema_json(d)
        files["validator.py"] = self._validator_skeleton(d)
        files["sample_configs/valid.json"] = json.dumps(d["valid_config"], indent=2)
        files["sample_configs/invalid.json"] = json.dumps(d["invalid_config"], indent=2)
        files["tests/__init__.py"] = ""
        files["tests/test_validator.py"] = self._test_validator(d)

        return files

    def _schema_json(self, d: dict) -> str:
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"{d['name']} configuration",
            "type": "object",
            "properties": d["fields"],
            "required": d["required"],
            "allOf": [],
        }
        for cf in d["cross_field"]:
            condition = {"if": {"properties": {cf["if_field"]: {"const": cf["if_value"]}}}}
            then_props = {}
            then_required = []
            if "then_min" in cf:
                then_props[cf["then_field"]] = {"minimum": cf["then_min"]}
            if "then_required" in cf:
                then_required.append(cf["then_field"])
            if "then_enum" in cf:
                then_props[cf["then_field"]] = {"enum": cf["then_enum"]}
            then_clause = {}
            if then_props:
                then_clause["properties"] = then_props
            if then_required:
                then_clause["required"] = then_required
            condition["then"] = then_clause
            schema["allOf"].append(condition)
        return json.dumps(schema, indent=2)

    def _validator_skeleton(self, d: dict) -> str:
        fields_list = list(d["fields"].keys())
        return f'''"""Configuration validator for {d["name"]}.

Implement validate_config() to enforce the JSON schema defined in config_schema.json.
"""
import json
from typing import List


def load_schema(path: str = "config_schema.json") -> dict:
    """Load the JSON schema from disk."""
    with open(path) as f:
        return json.load(f)


def validate_config(config: dict, schema_path: str = "config_schema.json") -> List[str]:
    """Validate a configuration dictionary against the schema.

    Args:
        config: The configuration dictionary to validate.
        schema_path: Path to the JSON schema file.

    Returns:
        A list of error messages. Empty list means the config is valid.
    """
    errors = []
    schema = load_schema(schema_path)

    # TODO: Implement field validation
    # Fields to validate: {", ".join(fields_list[:5])} ... and {len(fields_list) - 5} more

    # TODO: Implement type checking

    # TODO: Implement range validation (minimum/maximum)

    # TODO: Implement enum validation

    # TODO: Implement required field checking

    # TODO: Implement cross-field constraints (allOf conditions)

    return errors
'''

    def _test_validator(self, d: dict) -> str:
        fields = list(d["fields"].keys())
        # Test 10 of 15 fields + 3 of 5 cross-field constraints
        tested_fields = fields[:10]
        lines = [
            '"""Tests for config validator."""',
            'import json',
            'import pytest',
            'from validator import validate_config',
            '',
            '',
            f'VALID_CONFIG = json.load(open("sample_configs/valid.json"))',
            '',
            '',
            'def _fresh_valid():',
            '    """Return a fresh copy of the valid config."""',
            '    return dict(VALID_CONFIG)',
            '',
            '',
        ]

        # Test valid config
        lines.append('def test_valid_config_passes():')
        lines.append('    errors = validate_config(_fresh_valid())')
        lines.append('    assert errors == [], f"Valid config should pass: {errors}"')
        lines.append('')
        lines.append('')

        # Test invalid config
        lines.append('def test_invalid_config_fails():')
        lines.append('    config = json.load(open("sample_configs/invalid.json"))')
        lines.append('    errors = validate_config(config)')
        lines.append('    assert len(errors) > 0, "Invalid config should fail"')
        lines.append('')
        lines.append('')

        # Test required fields
        lines.append('def test_missing_required_field():')
        lines.append('    config = _fresh_valid()')
        lines.append(f'    del config["{d["required"][0]}"]')
        lines.append('    errors = validate_config(config)')
        lines.append('    assert len(errors) > 0, "Missing required field should fail"')
        lines.append('')
        lines.append('')

        # Test type validation for port (integer)
        lines.append('def test_wrong_type_port():')
        lines.append('    config = _fresh_valid()')
        lines.append('    config["port"] = "not_a_number"')
        lines.append('    errors = validate_config(config)')
        lines.append('    assert len(errors) > 0, "Wrong type should fail"')
        lines.append('')
        lines.append('')

        # Test range validation
        lines.append('def test_port_out_of_range():')
        lines.append('    config = _fresh_valid()')
        lines.append('    config["port"] = 99999')
        lines.append('    errors = validate_config(config)')
        lines.append('    assert len(errors) > 0, "Port out of range should fail"')
        lines.append('')
        lines.append('')

        # Test enum validation
        enum_field = None
        for f, spec in d["fields"].items():
            if "enum" in spec:
                enum_field = f
                break
        if enum_field:
            lines.append(f'def test_invalid_enum_{enum_field}():')
            lines.append('    config = _fresh_valid()')
            lines.append(f'    config["{enum_field}"] = "INVALID_VALUE"')
            lines.append('    errors = validate_config(config)')
            lines.append('    assert len(errors) > 0, "Invalid enum should fail"')
            lines.append('')
            lines.append('')

        # Test cross-field constraints (3 of 5)
        for i, cf in enumerate(d["cross_field"][:3]):
            lines.append(f'def test_cross_field_{i + 1}():')
            lines.append(f'    """Test: {cf["desc"]}"""')
            lines.append('    config = _fresh_valid()')
            lines.append(f'    config["{cf["if_field"]}"] = {json.dumps(cf["if_value"])}')
            if "then_min" in cf:
                lines.append(f'    config["{cf["then_field"]}"] = {cf["then_min"] - 1}')
            elif "then_required" in cf:
                lines.append(f'    config.pop("{cf["then_field"]}", None)')
            elif "then_enum" in cf:
                lines.append(f'    config["{cf["then_field"]}"] = "debug"')
            lines.append('    errors = validate_config(config)')
            lines.append('    assert len(errors) > 0, f"Cross-field constraint should fail: {errors}"')
            lines.append('')
            lines.append('')

        # Test boolean field
        lines.append('def test_boolean_field_type():')
        lines.append('    config = _fresh_valid()')
        lines.append(f'    config["ssl_enabled"] = "yes"  # Should be bool')
        lines.append('    errors = validate_config(config)')
        lines.append('    assert len(errors) > 0, "Non-boolean for boolean field should fail"')
        lines.append('')

        return '\n'.join(lines)
