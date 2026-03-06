"""
Parameterized generator for CROSS6: gRPC-to-REST Bridge.

Each seed produces a different service domain (UserService/OrderService/ProductService)
with different method names and field names, but the same 4 type conversion bugs:
  1. int64 passed as number instead of string
  2. single-element repeated field not wrapped as array
  3. enum sent as integer instead of string name
  4. timestamp as epoch seconds instead of ISO 8601
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


DOMAINS = [
    {
        # Seed 0: User Service
        "service_name": "UserService",
        "resource": "users",
        "entity": "User",
        "id_field": "user_id",
        "name_field": "display_name",
        "list_field": "roles",
        "list_item_type": "Role",
        "status_field": "account_status",
        "status_enum": "AccountStatus",
        "status_values": ["UNKNOWN", "ACTIVE", "SUSPENDED", "DELETED"],
        "ts_field": "created_at",
        "extra_field": "email",
        "sample_id": 9007199254740993,
        "sample_name": "Alice Johnson",
        "sample_list": ["admin", "editor"],
        "sample_single": ["viewer"],
        "sample_email": "alice@example.com",
        "sample_ts": 1700000000,
        "methods": [
            ("GetUser", "get_user", "GET", "/{id}"),
            ("ListUsers", "list_users", "GET", "/"),
            ("CreateUser", "create_user", "POST", "/"),
            ("DeleteUser", "delete_user", "DELETE", "/{id}"),
        ],
    },
    {
        # Seed 1: Order Service
        "service_name": "OrderService",
        "resource": "orders",
        "entity": "Order",
        "id_field": "order_id",
        "name_field": "customer_name",
        "list_field": "items",
        "list_item_type": "OrderItem",
        "status_field": "order_status",
        "status_enum": "OrderStatus",
        "status_values": ["UNKNOWN", "PENDING", "SHIPPED", "DELIVERED"],
        "ts_field": "placed_at",
        "extra_field": "shipping_address",
        "sample_id": 8007199254740993,
        "sample_name": "Bob Smith",
        "sample_list": ["item_001", "item_002"],
        "sample_single": ["item_003"],
        "sample_email": "123 Main St",
        "sample_ts": 1700100000,
        "methods": [
            ("GetOrder", "get_order", "GET", "/{id}"),
            ("ListOrders", "list_orders", "GET", "/"),
            ("PlaceOrder", "place_order", "POST", "/"),
            ("CancelOrder", "cancel_order", "DELETE", "/{id}"),
        ],
    },
    {
        # Seed 2: Product Service
        "service_name": "ProductService",
        "resource": "products",
        "entity": "Product",
        "id_field": "product_id",
        "name_field": "product_name",
        "list_field": "tags",
        "list_item_type": "Tag",
        "status_field": "availability",
        "status_enum": "Availability",
        "status_values": ["UNKNOWN", "IN_STOCK", "OUT_OF_STOCK", "DISCONTINUED"],
        "ts_field": "listed_at",
        "extra_field": "description",
        "sample_id": 7007199254740993,
        "sample_name": "Widget Pro",
        "sample_list": ["electronics", "gadgets"],
        "sample_single": ["sale"],
        "sample_email": "A premium widget",
        "sample_ts": 1700200000,
        "methods": [
            ("GetProduct", "get_product", "GET", "/{id}"),
            ("ListProducts", "list_products", "GET", "/"),
            ("AddProduct", "add_product", "POST", "/"),
            ("RemoveProduct", "remove_product", "DELETE", "/{id}"),
        ],
    },
]


class Generator(TaskGenerator):
    task_id = "CROSS6_grpc_rest_bridge"
    domain = "Multi-language"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        d = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(d, seed)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CROSS6_grpc_rest_bridge")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CROSS6_grpc_rest_bridge",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": ["B1_int64_string", "B2_repeated_array", "B3_enum_name", "B4_timestamp_iso"],
                "seed": seed,
                "domain": d["service_name"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Multi-language"},
        )

    def _make_workspace(self, d: dict, seed: int) -> dict:
        files = {}
        files["models.py"] = self._models(d)
        files["service_impl.py"] = self._service_impl(d)
        files["gateway.py"] = self._gateway(d)
        files["service.proto"] = self._proto(d)
        files["tests/__init__.py"] = ""
        files["tests/test_gateway.py"] = self._tests(d)
        return files

    def _proto(self, d: dict) -> str:
        methods_block = ""
        for rpc_name, _, http_method, path in d["methods"]:
            methods_block += f"  rpc {rpc_name} ({d['entity']}Request) returns ({d['entity']}Response);\n"
        sv = "\n".join(f"  {v} = {i};" for i, v in enumerate(d["status_values"]))
        return f'''syntax = "proto3";

package {d["resource"]};

service {d["service_name"]} {{
{methods_block}}}

enum {d["status_enum"]} {{
{sv}
}}

message {d["entity"]}Response {{
  int64 {d["id_field"]} = 1;
  string {d["name_field"]} = 2;
  repeated string {d["list_field"]} = 3;
  {d["status_enum"]} {d["status_field"]} = 4;
  int64 {d["ts_field"]} = 5;  // Unix epoch seconds
  string {d["extra_field"]} = 6;
}}
'''

    def _models(self, d: dict) -> str:
        sv_repr = ", ".join(f'"{v}"' for v in d["status_values"])
        return f'''"""
Data models for {d["service_name"]}.
"""
from __future__ import annotations
from enum import IntEnum


class {d["status_enum"]}(IntEnum):
    """Status enum with integer codes."""
{chr(10).join(f"    {v} = {i}" for i, v in enumerate(d["status_values"]))}


# Ordered list of enum names for reverse lookup
{d["status_enum"].upper()}_NAMES = [{sv_repr}]


class {d["entity"]}:
    """Internal representation of a {d["entity"].lower()}."""

    def __init__(
        self,
        {d["id_field"]}: int,
        {d["name_field"]}: str,
        {d["list_field"]}: list[str],
        {d["status_field"]}: {d["status_enum"]},
        {d["ts_field"]}: int,
        {d["extra_field"]}: str = "",
    ):
        self.{d["id_field"]} = {d["id_field"]}
        self.{d["name_field"]} = {d["name_field"]}
        self.{d["list_field"]} = {d["list_field"]}
        self.{d["status_field"]} = {d["status_field"]}
        self.{d["ts_field"]} = {d["ts_field"]}
        self.{d["extra_field"]} = {d["extra_field"]}
'''

    def _service_impl(self, d: dict) -> str:
        list_repr = ", ".join(f'"{x}"' for x in d["sample_list"])
        single_repr = ", ".join(f'"{x}"' for x in d["sample_single"])
        return f'''"""
{d["service_name"]} — internal implementation returning gRPC-style responses.
"""
from models import {d["entity"]}, {d["status_enum"]}


# In-memory store
_STORE = {{
    1: {d["entity"]}(
        {d["id_field"]}={d["sample_id"]},
        {d["name_field"]}="{d["sample_name"]}",
        {d["list_field"]}=[{list_repr}],
        {d["status_field"]}={d["status_enum"]}.{d["status_values"][1]},
        {d["ts_field"]}={d["sample_ts"]},
        {d["extra_field"]}="{d["sample_email"]}",
    ),
    2: {d["entity"]}(
        {d["id_field"]}={d["sample_id"] + 1},
        {d["name_field"]}="Single Item Entity",
        {d["list_field"]}=[{single_repr}],
        {d["status_field"]}={d["status_enum"]}.{d["status_values"][2]},
        {d["ts_field"]}={d["sample_ts"] + 86400},
        {d["extra_field"]}="secondary@example.com",
    ),
}}


def get_entity(entity_id: int) -> {d["entity"]} | None:
    """Retrieve a single entity by numeric key."""
    return _STORE.get(entity_id)


def list_entities() -> list[{d["entity"]}]:
    """Return all entities."""
    return list(_STORE.values())
'''

    def _gateway(self, d: dict) -> str:
        return f'''"""
REST Gateway for {d["service_name"]}.

Translates internal gRPC-style responses into REST/JSON format.
Contains 4 type conversion bugs — see spec.md for details.
"""
import json
from datetime import datetime, timezone
from models import {d["entity"]}, {d["status_enum"]}, {d["status_enum"].upper()}_NAMES
from service_impl import get_entity, list_entities


def _convert_field(field_name: str, value, field_type: str) -> object:
    """Convert a single field from internal gRPC representation to REST/JSON.

    Args:
        field_name: Name of the field being converted.
        value: The internal value to convert.
        field_type: One of 'int64', 'repeated', 'enum', 'timestamp', 'string'.

    Returns:
        JSON-safe representation of the value.
    """
    if field_type == "int64":
        # Bug 1: int64 must be serialized as JSON string to prevent JS precision loss.
        # Currently passes as bare integer.
        return int(value)

    elif field_type == "repeated":
        # Bug 2: repeated fields must always be a JSON array.
        # Currently returns bare item when list has exactly 1 element.
        if isinstance(value, list):
            if len(value) == 1:
                return value[0]  # BUG: should return [value[0]]
            return value
        return [value]

    elif field_type == "enum":
        # Bug 3: enum must be serialized as string name, not integer.
        # Currently sends the integer code.
        if isinstance(value, {d["status_enum"]}):
            return int(value)  # BUG: should return value.name or NAMES[value]
        return value

    elif field_type == "timestamp":
        # Bug 4: timestamp must be ISO 8601 string, not epoch seconds.
        # Currently passes raw epoch integer.
        return int(value)  # BUG: should convert to ISO 8601

    else:
        return value


def entity_to_json(entity: {d["entity"]}) -> dict:
    """Convert an internal entity to a REST/JSON-safe dictionary."""
    return {{
        "{d["id_field"]}": _convert_field("{d["id_field"]}", entity.{d["id_field"]}, "int64"),
        "{d["name_field"]}": _convert_field("{d["name_field"]}", entity.{d["name_field"]}, "string"),
        "{d["list_field"]}": _convert_field("{d["list_field"]}", entity.{d["list_field"]}, "repeated"),
        "{d["status_field"]}": _convert_field("{d["status_field"]}", entity.{d["status_field"]}, "enum"),
        "{d["ts_field"]}": _convert_field("{d["ts_field"]}", entity.{d["ts_field"]}, "timestamp"),
        "{d["extra_field"]}": _convert_field("{d["extra_field"]}", entity.{d["extra_field"]}, "string"),
    }}


def handle_get(entity_id: int) -> str:
    """Handle GET /{{resource}}/{{id}} — return single entity as JSON."""
    entity = get_entity(entity_id)
    if entity is None:
        return json.dumps({{"error": "not found"}})
    return json.dumps(entity_to_json(entity))


def handle_list() -> str:
    """Handle GET /{{resource}} — return all entities as JSON array."""
    entities = list_entities()
    return json.dumps([entity_to_json(e) for e in entities])
'''

    def _tests(self, d: dict) -> str:
        list_repr = ", ".join(f'"{x}"' for x in d["sample_list"])
        single_repr = ", ".join(f'"{x}"' for x in d["sample_single"])
        return f'''"""
Tests for the REST gateway type conversions.
Each test targets one of the 4 conversion bugs.
"""
import json
import pytest
from datetime import datetime, timezone
from gateway import entity_to_json, handle_get, handle_list, _convert_field
from models import {d["entity"]}, {d["status_enum"]}


def _make_entity(**overrides):
    """Create a test entity with defaults."""
    defaults = {{
        "{d["id_field"]}": {d["sample_id"]},
        "{d["name_field"]}": "{d["sample_name"]}",
        "{d["list_field"]}": [{list_repr}],
        "{d["status_field"]}": {d["status_enum"]}.{d["status_values"][1]},
        "{d["ts_field"]}": {d["sample_ts"]},
        "{d["extra_field"]}": "{d["sample_email"]}",
    }}
    defaults.update(overrides)
    return {d["entity"]}(**defaults)


class TestInt64AsString:
    """Bug 1: int64 fields must be JSON strings to prevent JS precision loss."""

    def test_large_id_is_string(self):
        entity = _make_entity()
        result = entity_to_json(entity)
        assert isinstance(result["{d["id_field"]}"], str), (
            f"int64 field must be a string, got {{type(result['{d['id_field']}'])}}: "
            f"{{result['{d['id_field']}']!r}}"
        )

    def test_large_id_value_preserved(self):
        entity = _make_entity()
        result = entity_to_json(entity)
        assert result["{d["id_field"]}"] == str({d["sample_id"]}), (
            f"int64 value mismatch: got {{result['{d['id_field']}']!r}}"
        )

    def test_convert_field_int64(self):
        result = _convert_field("{d["id_field"]}", {d["sample_id"]}, "int64")
        assert isinstance(result, str), f"_convert_field int64 must return str, got {{type(result)}}"


class TestRepeatedAsArray:
    """Bug 2: repeated fields must always be JSON arrays."""

    def test_multi_element_is_array(self):
        entity = _make_entity({d["list_field"]}=[{list_repr}])
        result = entity_to_json(entity)
        assert isinstance(result["{d["list_field"]}"], list), (
            f"repeated field with 2 elements must be list, got {{type(result['{d['list_field']}'])}}"
        )

    def test_single_element_is_still_array(self):
        entity = _make_entity({d["list_field"]}=[{single_repr}])
        result = entity_to_json(entity)
        assert isinstance(result["{d["list_field"]}"], list), (
            f"repeated field with 1 element must still be list, got "
            f"{{type(result['{d['list_field']}'])}}: {{result['{d['list_field']}']!r}}"
        )
        assert len(result["{d["list_field"]}"]) == 1

    def test_empty_is_array(self):
        entity = _make_entity({d["list_field"]}=[])
        result = entity_to_json(entity)
        assert isinstance(result["{d["list_field"]}"], list), (
            f"repeated field with 0 elements must be list"
        )


class TestEnumAsString:
    """Bug 3: enum fields must use string name, not integer code."""

    def test_enum_is_string_name(self):
        entity = _make_entity({d["status_field"]}={d["status_enum"]}.{d["status_values"][1]})
        result = entity_to_json(entity)
        assert isinstance(result["{d["status_field"]}"], str), (
            f"enum must be string, got {{type(result['{d['status_field']}'])}}: "
            f"{{result['{d['status_field']}']!r}}"
        )
        assert result["{d["status_field"]}"] == "{d["status_values"][1]}", (
            f"enum name mismatch: got {{result['{d['status_field']}']!r}}"
        )

    def test_all_enum_values(self):
        for val in {d["status_enum"]}:
            entity = _make_entity({d["status_field"]}=val)
            result = entity_to_json(entity)
            assert result["{d["status_field"]}"] == val.name, (
                f"{{val}} -> expected '{{val.name}}', got {{result['{d['status_field']}']!r}}"
            )


class TestTimestampAsISO:
    """Bug 4: timestamp fields must be ISO 8601 strings."""

    def test_timestamp_is_iso_string(self):
        entity = _make_entity()
        result = entity_to_json(entity)
        assert isinstance(result["{d["ts_field"]}"], str), (
            f"timestamp must be string, got {{type(result['{d['ts_field']}'])}}: "
            f"{{result['{d['ts_field']}']!r}}"
        )

    def test_timestamp_is_valid_iso(self):
        entity = _make_entity()
        result = entity_to_json(entity)
        ts = result["{d["ts_field"]}"]
        # Must parse as ISO 8601
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        expected = datetime.fromtimestamp({d["sample_ts"]}, tz=timezone.utc)
        assert parsed == expected, f"timestamp mismatch: {{parsed}} != {{expected}}"

    def test_timestamp_has_utc_suffix(self):
        entity = _make_entity()
        result = entity_to_json(entity)
        ts = result["{d["ts_field"]}"]
        assert ts.endswith("Z") or "+00:00" in ts, (
            f"timestamp must be UTC: {{ts!r}}"
        )


class TestEndToEnd:
    """Full pipeline tests."""

    def test_handle_get_json_valid(self):
        raw = handle_get(1)
        data = json.loads(raw)
        assert isinstance(data["{d["id_field"]}"], str)
        assert isinstance(data["{d["list_field"]}"], list)
        assert isinstance(data["{d["status_field"]}"], str)
        assert isinstance(data["{d["ts_field"]}"], str)

    def test_handle_list_json_valid(self):
        raw = handle_list()
        data = json.loads(raw)
        assert isinstance(data, list)
        assert len(data) >= 2
        for item in data:
            assert isinstance(item["{d["id_field"]}"], str)
            assert isinstance(item["{d["list_field"]}"], list)
'''
