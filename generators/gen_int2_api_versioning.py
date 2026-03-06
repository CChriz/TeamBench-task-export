"""
Parameterized generator for INT2: API Version Migration.

Each seed produces a Flask API with v1 and v2 routes. The migration has 5 breaking
changes, but MIGRATION_NOTES.md reveals 2 must keep backward-compatible shims.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized domain pools ──────────────────────────────────────

DOMAINS = [
    {
        "name": "users",
        "entity": "User",
        "entity_lower": "user",
        "entity_plural": "users",
        "old_name_field": "user_name",
        "new_name_field": "display_name",
        "id_field": "user_id",
        "sample_items": [
            {"user_id": 1, "user_name": "Alice", "email": "alice@example.com", "role": "admin"},
            {"user_id": 2, "user_name": "Bob", "email": "bob@example.com", "role": "member"},
            {"user_id": 3, "user_name": "Charlie", "email": "charlie@example.com", "role": "viewer"},
        ],
        "extra_fields": ["email", "role"],
        "mobile_version": "3.2",
    },
    {
        "name": "products",
        "entity": "Product",
        "entity_lower": "product",
        "entity_plural": "products",
        "old_name_field": "product_name",
        "new_name_field": "display_name",
        "id_field": "product_id",
        "sample_items": [
            {"product_id": 1, "product_name": "Widget", "price": 9.99, "category": "electronics"},
            {"product_id": 2, "product_name": "Gadget", "price": 19.99, "category": "electronics"},
            {"product_id": 3, "product_name": "Tool", "price": 4.99, "category": "hardware"},
        ],
        "extra_fields": ["price", "category"],
        "mobile_version": "3.2",
    },
    {
        "name": "orders",
        "entity": "Order",
        "entity_lower": "order",
        "entity_plural": "orders",
        "old_name_field": "order_name",
        "new_name_field": "display_name",
        "id_field": "order_id",
        "sample_items": [
            {"order_id": 1, "order_name": "ORD-001", "amount": 150.00, "status": "pending"},
            {"order_id": 2, "order_name": "ORD-002", "amount": 250.00, "status": "shipped"},
            {"order_id": 3, "order_name": "ORD-003", "amount": 75.00, "status": "delivered"},
        ],
        "extra_fields": ["amount", "status"],
        "mobile_version": "3.2",
    },
]

API_KEY_NAMES = ["X-API-Key", "X-Api-Key", "X-API-KEY"]
APP_NAMES = ["marketplace-api", "platform-api", "service-api", "hub-api", "gateway-api"]


class Generator(TaskGenerator):
    task_id = "INT2_api_versioning"
    domain = "SWE"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        domain = DOMAINS[seed % len(DOMAINS)]
        api_key_header = API_KEY_NAMES[seed % len(API_KEY_NAMES)]
        app_name = APP_NAMES[seed % len(APP_NAMES)]

        workspace_files = self._make_workspace(domain, api_key_header, app_name)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "INT2_api_versioning")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="INT2_api_versioning",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "domain": domain["name"],
                "old_name_field": domain["old_name_field"],
                "new_name_field": domain["new_name_field"],
                "api_key_header": api_key_header,
                "shimmed_changes": ["field_rename", "auth_header"],
                "clean_breaks": ["response_wrapping", "pagination", "error_format"],
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "SWE"},
        )

    def _make_workspace(self, domain: dict, api_key_header: str, app_name: str) -> dict:
        files = {}

        entity = domain["entity"]
        entity_lower = domain["entity_lower"]
        entity_plural = domain["entity_plural"]
        old_name = domain["old_name_field"]
        new_name = domain["new_name_field"]
        id_field = domain["id_field"]
        sample_items = domain["sample_items"]
        extra_fields = domain["extra_fields"]
        mobile_ver = domain["mobile_version"]

        # Build sample items as Python repr
        items_repr = repr(sample_items)

        # ── MIGRATION_SPEC.md (says break ALL 5 cleanly) ────────────────
        files["MIGRATION_SPEC.md"] = (
            f"# {app_name} Migration Spec: v1 -> v2\n\n"
            f"## Overview\n\n"
            f"Migrate the {entity_plural} API from v1 to v2. All 5 changes should be\n"
            f"implemented as clean breaks with no backward compatibility.\n\n"
            f"## Breaking Changes\n\n"
            f"### Change 1: Field Rename\n"
            f"- v1: `{old_name}` field in {entity_lower} responses\n"
            f"- v2: `{new_name}` field (rename, drop old field)\n\n"
            f"### Change 2: Response Wrapping\n"
            f"- v1: Bare object `{{{id_field}: 1, ...}}`\n"
            f'- v2: Wrapped `{{"data": {{{id_field}: 1, ...}}, "meta": {{"version": "v2"}}}}`\n\n'
            f"### Change 3: Auth Header\n"
            f"- v1: `{api_key_header}: <key>`\n"
            f"- v2: `Authorization: Bearer <token>`\n\n"
            f"### Change 4: Pagination\n"
            f"- v1: `?page=N&per_page=M` with `page`/`total_pages` in response\n"
            f"- v2: `?cursor=<token>&limit=M` with `next_cursor` in response\n\n"
            f"### Change 5: Error Format\n"
            f'- v1: `{{"error": "<message>"}}`\n'
            f'- v2: `{{"errors": [{{"code": "<CODE>", "message": "<message>"}}]}}`\n\n'
            f"## Implementation\n\n"
            f"Implement all 5 changes as clean breaks. Remove all v1 behavior from v2 endpoints.\n"
        )

        # ── MIGRATION_NOTES.md (overrides: 2 need shims) ────────────────
        files["MIGRATION_NOTES.md"] = (
            f"# Migration Notes (Post-Spec Addendum)\n\n"
            f"**IMPORTANT: This document overrides MIGRATION_SPEC.md where they conflict.**\n\n"
            f"## Production Constraints Discovered After Spec Was Written\n\n"
            f"### Change 1 (Field Rename): NEEDS SHIM\n\n"
            f"The mobile app v{mobile_ver} (still in production with 40% of users) reads\n"
            f"`{old_name}` from {entity_lower} responses. We cannot break these users.\n\n"
            f"**Required behavior**: v2 {entity_lower} responses must include BOTH\n"
            f"`{old_name}` AND `{new_name}` with the same value. This is a temporary\n"
            f"shim until mobile v4.0 ships (ETA: 3 months).\n\n"
            f"### Change 2 (Response Wrapping): CLEAN BREAK OK\n\n"
            f"No existing clients depend on the bare format. Break cleanly.\n\n"
            f"### Change 3 (Auth Header): NEEDS SHIM\n\n"
            f"The mobile app v{mobile_ver} sends `{api_key_header}` headers. The v2\n"
            f"auth middleware must accept BOTH `{api_key_header}` AND\n"
            f"`Authorization: Bearer <token>`. If both are present, prefer Bearer.\n\n"
            f"### Change 4 (Pagination): CLEAN BREAK OK\n\n"
            f"The mobile app v{mobile_ver} only lists {entity_plural} in a non-paginated\n"
            f"view. No impact. Break cleanly.\n\n"
            f"### Change 5 (Error Format): CLEAN BREAK OK\n\n"
            f"Error handling in mobile v{mobile_ver} already uses a generic fallback.\n"
            f"Break cleanly.\n"
        )

        # ── api/models.py ────────────────────────────────────────────────
        extra_field_defs = ""
        for ef in extra_fields:
            extra_field_defs += f"    {ef}: Any\n"

        files["api/__init__.py"] = ""
        files["api/models.py"] = (
            f'"""\n'
            f'Data models for {app_name}.\n'
            f'"""\n'
            f'from typing import Any\n'
            f'\n'
            f'\n'
            f'# Sample data store\n'
            f'ITEMS = {items_repr}\n'
            f'\n'
            f'\n'
            f'def get_{entity_lower}(item_id: int) -> dict | None:\n'
            f'    """Get a {entity_lower} by ID."""\n'
            f'    for item in ITEMS:\n'
            f'        if item["{id_field}"] == item_id:\n'
            f'            return dict(item)\n'
            f'    return None\n'
            f'\n'
            f'\n'
            f'def list_{entity_plural}(page: int = 1, per_page: int = 10) -> list[dict]:\n'
            f'    """List {entity_plural} with pagination."""\n'
            f'    start = (page - 1) * per_page\n'
            f'    end = start + per_page\n'
            f'    return [dict(item) for item in ITEMS[start:end]]\n'
        )

        # ── api/app.py (BUGGY: v2 endpoints not yet implemented) ────────
        api_key_lower = api_key_header.lower()
        files["api/app.py"] = (
            f'"""\n'
            f'{app_name} — Flask API with v1 and v2 routes.\n'
            f'\n'
            f'v1 routes are complete and working.\n'
            f'v2 routes need to be implemented per MIGRATION_SPEC.md and MIGRATION_NOTES.md.\n'
            f'"""\n'
            f'from flask import Flask, request, jsonify\n'
            f'from api.models import get_{entity_lower}, list_{entity_plural}, ITEMS\n'
            f'\n'
            f'app = Flask(__name__)\n'
            f'\n'
            f'\n'
            f'# ── Auth helpers ────────────────────────────────────────────────────\n'
            f'\n'
            f'def check_v1_auth():\n'
            f'    """v1 auth: requires {api_key_header} header."""\n'
            f'    key = request.headers.get("{api_key_header}")\n'
            f'    if not key:\n'
            f'        return False\n'
            f'    return True  # In production, validate against key store\n'
            f'\n'
            f'\n'
            f'def check_v2_auth():\n'
            f'    """\n'
            f'    v2 auth: requires Authorization: Bearer <token>.\n'
            f'\n'
            f'    TODO: Per MIGRATION_NOTES.md, this must also accept {api_key_header}\n'
            f'    as a backward-compatible shim for mobile v{mobile_ver}.\n'
            f'    Currently ONLY checks Bearer token (missing shim).\n'
            f'    """\n'
            f'    auth = request.headers.get("Authorization", "")\n'
            f'    if auth.startswith("Bearer "):\n'
            f'        return True\n'
            f'    return False\n'
            f'\n'
            f'\n'
            f'# ── V1 Routes (complete, working) ──────────────────────────────────\n'
            f'\n'
            f'@app.route("/v1/{entity_plural}/<int:item_id>")\n'
            f'def v1_get_{entity_lower}(item_id):\n'
            f'    if not check_v1_auth():\n'
            f'        return jsonify({{"error": "Unauthorized"}}), 401\n'
            f'    item = get_{entity_lower}(item_id)\n'
            f'    if not item:\n'
            f'        return jsonify({{"error": "{entity} not found"}}), 404\n'
            f'    return jsonify(item), 200\n'
            f'\n'
            f'\n'
            f'@app.route("/v1/{entity_plural}")\n'
            f'def v1_list_{entity_plural}():\n'
            f'    if not check_v1_auth():\n'
            f'        return jsonify({{"error": "Unauthorized"}}), 401\n'
            f'    page = request.args.get("page", 1, type=int)\n'
            f'    per_page = request.args.get("per_page", 10, type=int)\n'
            f'    items = list_{entity_plural}(page, per_page)\n'
            f'    return jsonify(items), 200\n'
            f'\n'
            f'\n'
            f'# ── V2 Routes (TODO: implement all 5 breaking changes) ─────────────\n'
            f'# Currently these are just copies of v1 routes — they need to be\n'
            f'# updated per MIGRATION_SPEC.md and MIGRATION_NOTES.md.\n'
            f'\n'
            f'@app.route("/v2/{entity_plural}/<int:item_id>")\n'
            f'def v2_get_{entity_lower}(item_id):\n'
            f'    """TODO: Implement v2 get with all 5 breaking changes + shims."""\n'
            f'    if not check_v2_auth():\n'
            f'        # BUG: Uses v1 error format, should use v2 format\n'
            f'        return jsonify({{"error": "Unauthorized"}}), 401\n'
            f'    item = get_{entity_lower}(item_id)\n'
            f'    if not item:\n'
            f'        # BUG: Uses v1 error format\n'
            f'        return jsonify({{"error": "{entity} not found"}}), 404\n'
            f'    # BUG: Returns bare object (v1 format), not wrapped\n'
            f'    # BUG: Uses {old_name} only, should have both {old_name} and {new_name}\n'
            f'    return jsonify(item), 200\n'
            f'\n'
            f'\n'
            f'@app.route("/v2/{entity_plural}")\n'
            f'def v2_list_{entity_plural}():\n'
            f'    """TODO: Implement v2 list with cursor pagination."""\n'
            f'    if not check_v2_auth():\n'
            f'        return jsonify({{"error": "Unauthorized"}}), 401\n'
            f'    # BUG: Uses v1 page-based pagination, should use cursor\n'
            f'    page = request.args.get("page", 1, type=int)\n'
            f'    per_page = request.args.get("per_page", 10, type=int)\n'
            f'    items = list_{entity_plural}(page, per_page)\n'
            f'    # BUG: Returns bare list, should wrap in data/meta envelope\n'
            f'    return jsonify(items), 200\n'
            f'\n'
            f'\n'
            f'if __name__ == "__main__":\n'
            f'    app.run(port=5000)\n'
        )

        # ── tests/test_v2_api.py ─────────────────────────────────────────
        files["tests/__init__.py"] = ""
        files["tests/test_v2_api.py"] = (
            f'"""\n'
            f'Tests for v2 API endpoints — all 5 breaking changes.\n'
            f'"""\n'
            f'import sys\n'
            f'import os\n'
            f'import pytest\n'
            f'\n'
            f'sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))\n'
            f'from api.app import app\n'
            f'\n'
            f'\n'
            f'@pytest.fixture\n'
            f'def client():\n'
            f'    app.config["TESTING"] = True\n'
            f'    with app.test_client() as c:\n'
            f'        yield c\n'
            f'\n'
            f'\n'
            f'def test_v2_uses_display_name(client):\n'
            f'    """v2 response must include {new_name} field."""\n'
            f'    r = client.get("/v2/{entity_plural}/1", headers={{"Authorization": "Bearer test"}})\n'
            f'    assert r.status_code == 200\n'
            f'    data = r.get_json()\n'
            f'    inner = data.get("data", data)\n'
            f'    assert "{new_name}" in inner, f"Missing {new_name} in response"\n'
            f'\n'
            f'\n'
            f'def test_v2_wraps_response(client):\n'
            f'    """v2 response must be wrapped in data/meta envelope."""\n'
            f'    r = client.get("/v2/{entity_plural}/1", headers={{"Authorization": "Bearer test"}})\n'
            f'    assert r.status_code == 200\n'
            f'    data = r.get_json()\n'
            f'    assert "data" in data, "Response must be wrapped with data key"\n'
            f'    assert "meta" in data, "Response must be wrapped with meta key"\n'
            f'\n'
            f'\n'
            f'def test_v2_accepts_bearer_auth(client):\n'
            f'    """v2 must accept Authorization: Bearer token."""\n'
            f'    r = client.get("/v2/{entity_plural}/1", headers={{"Authorization": "Bearer test-token"}})\n'
            f'    assert r.status_code == 200\n'
            f'\n'
            f'\n'
            f'def test_v2_cursor_pagination(client):\n'
            f'    """v2 list must use cursor-based pagination."""\n'
            f'    r = client.get("/v2/{entity_plural}?cursor=start&limit=10", headers={{"Authorization": "Bearer test"}})\n'
            f'    assert r.status_code == 200\n'
            f'    data = r.get_json()\n'
            f'    assert "data" in data, "List response must have data key"\n'
            f'    meta = data.get("meta", {{}})\n'
            f'    assert "next_cursor" in meta or "cursor" in str(meta), "Must have cursor in meta"\n'
            f'\n'
            f'\n'
            f'def test_v2_error_format(client):\n'
            f'    """v2 errors must use new format with errors array."""\n'
            f'    r = client.get("/v2/{entity_plural}/99999", headers={{"Authorization": "Bearer test"}})\n'
            f'    assert r.status_code in (404, 400)\n'
            f'    data = r.get_json()\n'
            f'    assert "errors" in data, "Error must use errors array format"\n'
            f'    assert isinstance(data["errors"], list)\n'
            f'    assert "error" not in data, "Must not have old-style error field"\n'
        )

        # ── tests/test_v1_compat.py ──────────────────────────────────────
        files["tests/test_v1_compat.py"] = (
            f'"""\n'
            f'Tests for v1 backward compatibility and v2 shims.\n'
            f'"""\n'
            f'import sys\n'
            f'import os\n'
            f'import pytest\n'
            f'\n'
            f'sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))\n'
            f'from api.app import app\n'
            f'\n'
            f'\n'
            f'@pytest.fixture\n'
            f'def client():\n'
            f'    app.config["TESTING"] = True\n'
            f'    with app.test_client() as c:\n'
            f'        yield c\n'
            f'\n'
            f'\n'
            f'def test_v1_still_works(client):\n'
            f'    """v1 endpoints must still respond."""\n'
            f'    r = client.get("/v1/{entity_plural}/1", headers={{"{api_key_header}": "test-key"}})\n'
            f'    assert r.status_code == 200\n'
            f'\n'
            f'\n'
            f'def test_v1_uses_old_name_field(client):\n'
            f'    """v1 must still use {old_name} field."""\n'
            f'    r = client.get("/v1/{entity_plural}/1", headers={{"{api_key_header}": "test-key"}})\n'
            f'    data = r.get_json()\n'
            f'    assert "{old_name}" in data\n'
            f'\n'
            f'\n'
            f'def test_v2_shim_field_rename(client):\n'
            f'    """v2 must include BOTH {old_name} and {new_name} (shim for mobile v{mobile_ver})."""\n'
            f'    r = client.get("/v2/{entity_plural}/1", headers={{"Authorization": "Bearer test"}})\n'
            f'    assert r.status_code == 200\n'
            f'    data = r.get_json()\n'
            f'    inner = data.get("data", data)\n'
            f'    assert "{old_name}" in inner, "Shim: v2 must still include {old_name}"\n'
            f'    assert "{new_name}" in inner, "v2 must include {new_name}"\n'
            f'\n'
            f'\n'
            f'def test_v2_shim_auth_accepts_api_key(client):\n'
            f'    """v2 must accept {api_key_header} header (shim for mobile v{mobile_ver})."""\n'
            f'    r = client.get("/v2/{entity_plural}/1", headers={{"{api_key_header}": "test-key"}})\n'
            f'    assert r.status_code == 200, \\\n'
            f'        f"v2 must accept {api_key_header} (got {{r.status_code}})"\n'
            f'\n'
            f'\n'
            f'def test_v2_shim_auth_prefers_bearer(client):\n'
            f'    """When both headers present, Bearer should be preferred."""\n'
            f'    r = client.get("/v2/{entity_plural}/1", headers={{\n'
            f'        "Authorization": "Bearer test-token",\n'
            f'        "{api_key_header}": "test-key",\n'
            f'    }})\n'
            f'    assert r.status_code == 200\n'
        )

        files["requirements.txt"] = "flask\npytest\n"

        return files
