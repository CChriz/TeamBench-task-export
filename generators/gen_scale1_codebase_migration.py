"""
Parameterized generator for SCALE1: Large Codebase Library Migration.

Each seed produces:
  - Different old/new library pairs (requests->httpx, urllib3->httpx, httplib2->httpx conceptually)
  - Different number of files to migrate (15-25)
  - Different service/module names drawn from pools
  - Different specific API pattern changes
  - Different false-positive files (should NOT be modified)

The migration categories stay the same:
  1. Import style
  2. Session/client pattern
  3. Empty response body handling
  4. Timeout type
  5. Basic authentication
  6. Streaming line iteration
  7. Exception types
  8. Test mocking library
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Library migration pairs — always old->httpx conceptually, but framing varies
LIBRARY_PAIRS = [
    {
        "old_lib": "requests",
        "new_lib": "httpx",
        "old_session": "requests.Session()",
        "new_client": "httpx.Client()",
        "old_auth": "HTTPBasicAuth",
        "old_auth_import": "from requests.auth import HTTPBasicAuth",
        "new_auth": "httpx.BasicAuth",
        "old_exception": "requests.exceptions.ConnectionError",
        "new_exception": "httpx.ConnectError",
        "old_mock": "requests_mock",
        "new_mock": "respx",
        "old_timeout_note": "plain int is now invalid",
        "requirements_old": ["requests==2.31.0", "requests_mock==1.11.0"],
        "requirements_new": ["httpx==0.27.0", "respx==0.20.4"],
    },
    {
        "old_lib": "requests",
        "new_lib": "httpx",
        "old_session": "requests.Session()",
        "new_client": "httpx.Client()",
        "old_auth": "HTTPBasicAuth",
        "old_auth_import": "from requests.auth import HTTPBasicAuth",
        "new_auth": "httpx.BasicAuth",
        "old_exception": "requests.exceptions.ConnectionError",
        "new_exception": "httpx.ConnectError",
        "old_mock": "requests_mock",
        "new_mock": "respx",
        "old_timeout_note": "plain int is now invalid",
        "requirements_old": ["requests==2.28.0", "requests_mock==1.10.0"],
        "requirements_new": ["httpx==0.26.0", "respx==0.20.3"],
    },
    {
        "old_lib": "requests",
        "new_lib": "httpx",
        "old_session": "requests.Session()",
        "new_client": "httpx.Client()",
        "old_auth": "HTTPBasicAuth",
        "old_auth_import": "from requests.auth import HTTPBasicAuth",
        "new_auth": "httpx.BasicAuth",
        "old_exception": "requests.exceptions.ConnectionError",
        "new_exception": "httpx.ConnectError",
        "old_mock": "requests_mock",
        "new_mock": "respx",
        "old_timeout_note": "plain int is now invalid",
        "requirements_old": ["requests==2.30.0", "requests_mock==1.11.0"],
        "requirements_new": ["httpx==0.25.0", "respx==0.20.2"],
    },
    {
        "old_lib": "requests",
        "new_lib": "httpx",
        "old_session": "requests.Session()",
        "new_client": "httpx.Client()",
        "old_auth": "HTTPBasicAuth",
        "old_auth_import": "from requests.auth import HTTPBasicAuth",
        "new_auth": "httpx.BasicAuth",
        "old_exception": "requests.exceptions.ConnectionError",
        "new_exception": "httpx.ConnectError",
        "old_mock": "requests_mock",
        "new_mock": "respx",
        "old_timeout_note": "plain int is now invalid",
        "requirements_old": ["requests==2.29.0", "requests_mock==1.11.0"],
        "requirements_new": ["httpx==0.24.0", "respx==0.20.1"],
    },
    {
        "old_lib": "requests",
        "new_lib": "httpx",
        "old_session": "requests.Session()",
        "new_client": "httpx.Client()",
        "old_auth": "HTTPBasicAuth",
        "old_auth_import": "from requests.auth import HTTPBasicAuth",
        "new_auth": "httpx.BasicAuth",
        "old_exception": "requests.exceptions.ConnectionError",
        "new_exception": "httpx.ConnectError",
        "old_mock": "requests_mock",
        "new_mock": "respx",
        "old_timeout_note": "plain int is now invalid",
        "requirements_old": ["requests==2.27.0", "requests_mock==1.9.3"],
        "requirements_new": ["httpx==0.23.0", "respx==0.19.3"],
    },
]

# Service module pools for generating file names
SERVICE_MODULES = [
    "user_service", "order_service", "payment_service", "analytics_service",
    "inventory_service", "shipping_service", "billing_service", "catalog_service",
    "search_service", "recommendation_service", "notification_service", "audit_service",
]

API_MODULES = [
    "client", "auth_client", "batch_client", "webhook_client", "stream_client",
    "retry_client", "bulk_client", "admin_client",
]

UTIL_MODULES = [
    "http_helpers", "response_parser", "retry", "request_builder",
    "error_handler", "serializer",
]

# False positive file pool: files that look like they use HTTP but must not be modified
FALSE_POSITIVE_FILES = [
    # (filename, reason)
    ("notification.py", "uses aiohttp — async notifier"),
    ("constants.py", "contains TIMEOUT constant for rate limiter"),
    ("settings.py", "contains requests_per_minute rate-limit config key"),
    ("legacy_adapter.py", "uses urllib directly — not requests library"),
    ("rate_limiter.py", "references request_count — unrelated to HTTP library"),
]


class Generator(TaskGenerator):
    task_id = "SCALE1_codebase_migration"
    domain = "migration"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        lib = LIBRARY_PAIRS[seed % len(LIBRARY_PAIRS)]
        old_lib = lib["old_lib"]
        new_lib = lib["new_lib"]

        # Pick service modules (5-8)
        n_services = rng.randint(4, 6)
        service_pool = list(SERVICE_MODULES)
        rng.shuffle(service_pool)
        chosen_services = service_pool[:n_services]

        # Pick api modules (3-4)
        n_api = rng.randint(3, 4)
        api_pool = list(API_MODULES)
        rng.shuffle(api_pool)
        chosen_apis = api_pool[:n_api]

        # Pick util modules (2-3)
        n_util = rng.randint(2, 3)
        util_pool = list(UTIL_MODULES)
        rng.shuffle(util_pool)
        chosen_utils = util_pool[:n_util]

        # Pick false positive files — vary by seed using offset into pool
        fp_pool = list(FALSE_POSITIVE_FILES)
        fp_start = seed % len(fp_pool)
        chosen_fp = [fp_pool[(fp_start + i) % len(fp_pool)] for i in range(3)]

        # Build lists for expected
        files_to_modify = []
        # client.py is always generated and always needs migration
        if "client" not in chosen_apis:
            files_to_modify.append("app/api/client.py")
        for m in chosen_apis:
            files_to_modify.append(f"app/api/{m}.py")
        for m in chosen_utils:
            files_to_modify.append(f"app/utils/{m}.py")
        for m in chosen_services:
            if m not in ("notification_service",):  # avoid false positive name collision
                files_to_modify.append(f"app/services/{m}.py")
        files_to_modify.append("app/tests/conftest.py")
        files_to_modify.append("app/tests/test_client.py")
        files_to_modify.append("requirements.txt")

        false_positive_files = [fp[0] for fp in chosen_fp]

        expected = {
            "old_lib": old_lib,
            "new_lib": new_lib,
            "files_to_modify": sorted(files_to_modify),
            "false_positive_files": false_positive_files,
            "false_positive_reasons": {fp[0]: fp[1] for fp in chosen_fp},
            "migration_changes": {
                "import": f"import {old_lib} -> import {new_lib}",
                "session": f"{lib['old_session']} -> {lib['new_client']}",
                "empty_body": "ValueError catch -> None check",
                "timeout": f"timeout=30 (int) -> timeout=httpx.Timeout(30.0)",
                "auth": f"{lib['old_auth']} -> {lib['new_auth']}",
                "streaming": "remove encoding= kwarg from iter_lines",
                "exceptions": f"{lib['old_exception']} -> {lib['new_exception']}",
                "mock": f"{lib['old_mock']} -> {lib['new_mock']}",
            },
            "requirements_old": lib["requirements_old"],
            "requirements_new": lib["requirements_new"],
        }

        workspace_files = self._build_workspace(
            lib, chosen_apis, chosen_utils, chosen_services, chosen_fp, rng,
        )

        spec_md = self._generate_spec(lib, files_to_modify, false_positive_files, chosen_fp)
        brief_md = self._generate_brief(lib)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _build_workspace(self, lib, apis, utils, services, false_positives, rng) -> dict[str, str]:
        files = {}
        old = lib["old_lib"]
        new = lib["new_lib"]
        old_auth = lib["old_auth"]
        old_auth_import = lib["old_auth_import"]
        new_auth = lib["new_auth"]
        old_exc = lib["old_exception"]
        new_exc = lib["new_exception"]
        old_mock = lib["old_mock"]
        new_mock = lib["new_mock"]

        files["app/__init__.py"] = ""
        files["app/api/__init__.py"] = ""
        files["app/services/__init__.py"] = ""
        files["app/utils/__init__.py"] = ""
        files["app/config/__init__.py"] = ""
        files["app/tests/__init__.py"] = ""

        # --- API files (all use old_lib, need migration) ---

        # Ensure "client" is always generated (grade.sh checks client.py)
        api_set = list(apis)
        if "client" not in api_set:
            api_set[0] = "client"

        for mod in api_set:
            if mod == "client":
                files[f"app/api/{mod}.py"] = f'''"""HTTP API client using {old} library."""
import {old}


class ApiClient:
    """Generic API client wrapping {old}.Session."""

    def __init__(self, base_url, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = {old}.Session()
        self.session.headers.update({{"Accept": "application/json"}})

    def get(self, path, params=None):
        """GET request."""
        url = f"{{self.base_url}}/{{path.lstrip(\'/\')}}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def post(self, path, data=None):
        """POST request."""
        url = f"{{self.base_url}}/{{path.lstrip(\'/\')}}"
        response = self.session.post(url, json=data, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def delete(self, path):
        """DELETE request — may return empty body."""
        url = f"{{self.base_url}}/{{path.lstrip(\'/\')}}"
        response = self.session.delete(url, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return None

    def close(self):
        """Close the session."""
        self.session.close()
'''
            elif mod == "auth_client":
                files[f"app/api/{mod}.py"] = f'''"""Authenticated API client."""
import {old}
{old_auth_import}


class AuthClient:
    """API client with basic authentication."""

    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.auth = {old_auth}(username, password)
        self.session = {old}.Session()
        self.session.auth = self.auth

    def get_protected(self, path):
        """GET a protected resource."""
        url = f"{{self.base_url}}/{{path.lstrip(\'/\')}}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def close(self):
        self.session.close()
'''
            elif mod == "batch_client":
                files[f"app/api/{mod}.py"] = f'''"""Batch operations client."""
import {old}


class BatchClient:
    """Client for batch API operations."""

    def __init__(self, base_url, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def send_batch(self, items):
        """Send a batch of items."""
        url = f"{{self.base_url}}/batch"
        response = {old}.post(url, json=items, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_all(self, path):
        """Fetch all records from a paginated endpoint."""
        url = f"{{self.base_url}}/{{path.lstrip(\'/\')}}"
        response = {old}.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
'''
            elif mod == "webhook_client":
                files[f"app/api/{mod}.py"] = f'''"""Webhook delivery client."""
import {old}


class WebhookClient:
    """Client for delivering webhooks."""

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.session = {old}.Session()

    def deliver(self, url, payload):
        """Deliver a webhook payload."""
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return None

    def close(self):
        self.session.close()
'''
            else:
                files[f"app/api/{mod}.py"] = f'''"""{mod.replace("_", " ").title()} client."""
import {old}


class {mod.replace("_", " ").title().replace(" ", "")}:
    """API client module for {mod.replace("_", " ")}."""

    def __init__(self, base_url, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = {old}.Session()

    def execute(self, path, data=None):
        """Execute an API operation."""
        url = f"{{self.base_url}}/{{path.lstrip(\'/\')}}"
        if data:
            response = self.session.post(url, json=data, timeout=self.timeout)
        else:
            response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return None

    def close(self):
        self.session.close()
'''

        # --- Utility files ---

        # Ensure "http_helpers", "response_parser", "retry" are all generated if possible
        util_set = list(utils)
        needed = ["http_helpers", "response_parser", "retry"]
        for n in needed:
            if n not in util_set:
                util_set.append(n)

        for mod in util_set:
            if mod == "http_helpers":
                files[f"app/utils/{mod}.py"] = f'''"""HTTP helper utilities."""
import {old}


def fetch_json(url, params=None, timeout=30):
    """Fetch JSON from a URL."""
    response = {old}.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def post_json(url, data, timeout=30):
    """POST JSON data to a URL."""
    response = {old}.post(url, json=data, timeout=timeout)
    response.raise_for_status()
    return response.json()


def stream_lines(url, timeout=30):
    """Stream response lines from a URL."""
    response = {old}.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    for line in response.iter_lines(encoding="utf-8"):
        if line:
            yield line
'''
            elif mod == "response_parser":
                files[f"app/utils/{mod}.py"] = f'''"""Response parsing utilities."""


def safe_json(response):
    """Safely parse JSON from a response, handling empty bodies.

    With {old} library, empty body raises ValueError.
    """
    try:
        return response.json()
    except ValueError:
        return None


def extract_data(response):
    """Extract data from API response."""
    body = safe_json(response)
    if body is None:
        return []
    return body.get("data", [])


def extract_error(response):
    """Extract error message from API response."""
    body = safe_json(response)
    if body is None:
        return "unknown error"
    return body.get("error", "unknown error")
'''
            elif mod == "retry":
                files[f"app/utils/{mod}.py"] = f'''"""Retry logic for HTTP requests."""
import time
import {old}
from {old}.exceptions import ConnectionError


def retry_request(method, url, max_retries=3, backoff=1.0, **kwargs):
    """Execute an HTTP request with retry logic."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = {old}.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except ConnectionError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(backoff * (2 ** attempt))
    raise last_error
'''
            else:
                files[f"app/utils/{mod}.py"] = f'''"""{mod.replace("_", " ").title()} utilities."""
import {old}


def process_response(response):
    """Process an HTTP response."""
    try:
        return response.json()
    except ValueError:
        return None


def make_request(url, method="GET", data=None, timeout=30):
    """Make an HTTP request with the {old} library."""
    response = {old}.request(method, url, json=data, timeout=timeout)
    response.raise_for_status()
    return process_response(response)
'''

        # --- Service files ---
        # These use the ApiClient, so they indirectly depend on requests
        for svc in services:
            class_name = "".join(w.capitalize() for w in svc.split("_"))
            files[f"app/services/{svc}.py"] = f'''"""{class_name} — uses the API client."""


class {class_name}:
    def __init__(self, api_client):
        self.client = api_client

    def get_all(self):
        return self.client.get("/{svc.replace("_service", "s")}")

    def get_one(self, entity_id):
        return self.client.get(f"/{svc.replace("_service", "s")}/{{entity_id}}")

    def create(self, data):
        return self.client.post("/{svc.replace("_service", "s")}", data=data)

    def delete(self, entity_id):
        return self.client.delete(f"/{svc.replace("_service", "s")}/{{entity_id}}")
'''

        # --- Config files (false positives) ---
        files["app/config/constants.py"] = '''"""Application constants — DO NOT MODIFY for requests migration."""

# Rate limiting
TIMEOUT = 60  # seconds — general timeout for rate limiter, NOT requests library config
MAX_RETRIES = 3
BATCH_SIZE = 100
PAGE_SIZE = 50

# API versioning
API_VERSION = "v2"
API_PREFIX = f"/api/{API_VERSION}"
'''

        files["app/config/settings.py"] = '''"""Application settings."""

SETTINGS = {
    "api_base_url": "https://api.example.com",
    "requests_per_minute": 60,
    "max_concurrent_requests": 10,
    "default_timeout": 30,
    "retry_max_attempts": 3,
    "retry_backoff_factor": 1.5,
}


def get_setting(key, default=None):
    return SETTINGS.get(key, default)
'''

        # --- False positive files ---
        for fp_name, fp_reason in false_positives:
            if fp_name == "notification.py":
                files["app/services/notification.py"] = '''"""Notification service using aiohttp — DO NOT MODIFY for requests migration."""
import asyncio

try:
    import aiohttp
except ImportError:
    aiohttp = None


class NotificationService:
    """Async notification sender using aiohttp."""

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    async def send_notification(self, message):
        """Send a notification via webhook."""
        if aiohttp is None:
            return {"status": "skipped", "reason": "aiohttp not installed"}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json={"text": message}) as resp:
                return {"status": resp.status}

    def send_sync(self, message):
        """Synchronous wrapper."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.send_notification(message))
        finally:
            loop.close()
'''
            elif fp_name == "constants.py":
                pass  # already generated above
            elif fp_name == "settings.py":
                pass  # already generated above
            elif fp_name == "legacy_adapter.py":
                files["app/utils/legacy_adapter.py"] = '''"""Legacy adapter using urllib directly — DO NOT MODIFY."""
import urllib.request
import urllib.error
import json


def legacy_fetch(url, timeout=30):
    """Fetch data using urllib (legacy code — not requests library)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return {"error": str(e)}
'''
            elif fp_name == "rate_limiter.py":
                files["app/utils/rate_limiter.py"] = '''"""Rate limiter — DO NOT MODIFY for requests migration."""
import time


class RateLimiter:
    """Token-bucket rate limiter.

    The request_count variable counts API calls for rate limiting,
    not HTTP library requests.
    """

    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.request_count = 0
        self._start = time.time()

    def check(self):
        """Check if rate limit allows a new request."""
        elapsed = time.time() - self._start
        if elapsed > 60:
            self.request_count = 0
            self._start = time.time()
        if self.request_count >= self.requests_per_minute:
            return False
        self.request_count += 1
        return True
'''

        # --- Test files ---
        files["app/tests/conftest.py"] = f'''"""Test fixtures using {old_mock}."""
import pytest

try:
    import {old_mock} as rm
    @pytest.fixture
    def mock_api():
        with rm.Mocker() as m:
            yield m
except ImportError:
    pass
'''

        # Generate a test file that uses old_mock
        files["app/tests/test_client.py"] = f'''"""Integration tests using {old_mock}."""
import json
import pytest
import {old}
import {old_mock}


def test_get_users():
    """Test fetching users."""
    from app.api.client import ApiClient
    with {old_mock}.Mocker() as m:
        m.get("https://api.example.com/users", json=[{{"id": 1, "name": "Alice"}}])
        client = ApiClient("https://api.example.com")
        users = client.get("/users")
        assert len(users) == 1
        assert users[0]["name"] == "Alice"
        client.close()


def test_post_user():
    """Test creating a user."""
    from app.api.client import ApiClient
    with {old_mock}.Mocker() as m:
        m.post("https://api.example.com/users", json={{"id": 2, "name": "Bob"}})
        client = ApiClient("https://api.example.com")
        result = client.post("/users", data={{"name": "Bob"}})
        assert result["name"] == "Bob"
        client.close()


def test_delete_user_empty_body():
    """Test deleting a user returns None for empty body."""
    from app.api.client import ApiClient
    with {old_mock}.Mocker() as m:
        m.delete("https://api.example.com/users/1", text="", status_code=204)
        client = ApiClient("https://api.example.com")
        result = client.delete("/users/1")
        assert result is None
        client.close()


def test_auth_client():
    """Test authenticated client."""
    from app.api.auth_client import AuthClient
    with {old_mock}.Mocker() as m:
        m.get("https://api.example.com/protected", json={{"secret": "data"}})
        client = AuthClient("https://api.example.com", "user", "pass")
        result = client.get_protected("/protected")
        assert result["secret"] == "data"
        client.close()


def test_fetch_json_helper():
    """Test fetch_json helper."""
    from app.utils.http_helpers import fetch_json
    with {old_mock}.Mocker() as m:
        m.get("https://example.com/data", json={{"key": "value"}})
        result = fetch_json("https://example.com/data")
        assert result["key"] == "value"


def test_response_parser():
    """Test response parser safe_json."""
    from app.utils.response_parser import safe_json, extract_data

    class MockResponse:
        def json(self):
            raise ValueError("No JSON")

    result = safe_json(MockResponse())
    assert result is None

    class MockResponse2:
        def json(self):
            return {{"data": [1, 2, 3]}}

    data = extract_data(MockResponse2())
    assert data == [1, 2, 3]


def test_notification_service_untouched():
    """Test that notification service still uses aiohttp (not migrated)."""
    import inspect
    from app.services.notification import NotificationService
    source = inspect.getsource(NotificationService)
    assert "aiohttp" in source, "NotificationService should still use aiohttp"
'''

        # --- requirements.txt ---
        old_reqs = lib["requirements_old"]
        files["requirements.txt"] = "\n".join(old_reqs + ["aiohttp==3.9.0", "pytest==7.4.0"]) + "\n"

        # --- app/main.py ---
        files["app/main.py"] = f'''"""Application entry point."""
import {old}
from app.api.client import ApiClient
from app.config.settings import get_setting


def create_client():
    """Create and configure the API client."""
    base_url = get_setting("api_base_url", "https://api.example.com")
    timeout = get_setting("default_timeout", 30)
    return ApiClient(base_url, timeout=timeout)


if __name__ == "__main__":
    client = create_client()
    print("Client created:", client)
'''

        return files

    def _generate_spec(self, lib, files_to_modify, false_positive_files, fp_with_reasons) -> str:
        old = lib["old_lib"]
        new = lib["new_lib"]
        old_auth = lib["old_auth"]
        new_auth = lib["new_auth"]
        old_exc = lib["old_exception"]
        new_exc = lib["new_exception"]
        old_mock = lib["old_mock"]
        new_mock = lib["new_mock"]

        fp_list = "\n".join(
            f"{i+1}. `{fp[0]}` — {fp[1]}; must not be modified"
            for i, fp in enumerate(fp_with_reasons)
        )
        modify_list = "\n".join(f"- `{f}`" for f in sorted(files_to_modify))

        return f"""# SCALE1: Large Codebase Library Migration ({old} → {new})

## Goal
Migrate a multi-file Python codebase from the `{old}` library to `{new}`.

## 8 Breaking Changes to Address

1. **Import style**: The top-level import and function calls must use the `{new}` namespace instead of `{old}`
2. **Session / client**: The session object type has changed; the new client must be used with a context manager pattern
3. **Empty response body**: When a response has no body, the JSON parsing behavior differs — the new library returns a different sentinel value that callers must handle
4. **Timeout type**: The timeout argument accepts a different type in the new library; passing a plain integer is no longer valid
5. **Basic authentication**: The authentication helper class has a different name and import path in the new library (`{new_auth}` instead of `{old_auth}`)
6. **Streaming line iteration**: The streaming iterator no longer accepts an `encoding` keyword argument; any such argument must be removed
7. **Exception types**: Network error exceptions have been renamed; catch clauses must reference `{new_exc}` instead of `{old_exc}`
8. **Test mocking**: The HTTP mocking library used in tests is incompatible with the new HTTP client; tests must use `{new_mock}` instead of `{old_mock}`

## 3 False-Positive Patterns (DO NOT CHANGE)

{fp_list}

## Files to Migrate

{modify_list}

## Deliverables
- All files migrated from `{old}` to `{new}`
- `requirements.txt` updated (`{old}` → `{new}`, `{old_mock}` → `{new_mock}`)
- False-positive files left untouched
- All tests pass
"""

    def _generate_brief(self, lib) -> str:
        old = lib["old_lib"]
        new = lib["new_lib"]
        return f"""# SCALE1: Large Codebase Library Migration (Brief)

Migrate the codebase from `{old}` to `{new}`.
Watch out for false-positive files that must NOT be modified.
Update `requirements.txt` as well.
"""
