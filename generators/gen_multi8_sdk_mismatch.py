"""
Parameterized generator for MULTI8: SDK Mismatch.

Each seed produces:
  - Different field name mismatches
  - Different response wrapper keys
  - Different pagination parameter names
  - Same 4 bug types but field names vary per seed

The 4 bugs are always:
  1. SDK sends wrong field name for user creation
  2. SDK reads wrong wrapper key from list response
  3. SDK reads wrong field from error response
  4. SDK sends wrong pagination query parameter
"""
from __future__ import annotations

import json
import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

FIELD_CONFIGS = [
    {"correct_name": "user_name",    "wrong_name": "username",
     "correct_list": "results",      "wrong_list": "items",
     "correct_error": "detail",      "wrong_error": "message",
     "correct_page": "limit",        "wrong_page": "page_size"},
    {"correct_name": "full_name",    "wrong_name": "name",
     "correct_list": "data",         "wrong_list": "records",
     "correct_error": "reason",      "wrong_error": "error_msg",
     "correct_page": "per_page",     "wrong_page": "count"},
    {"correct_name": "display_name", "wrong_name": "displayName",
     "correct_list": "entries",      "wrong_list": "objects",
     "correct_error": "description", "wrong_error": "msg",
     "correct_page": "max_results",  "wrong_page": "size"},
    {"correct_name": "login_name",   "wrong_name": "login",
     "correct_list": "users",        "wrong_list": "list",
     "correct_error": "info",        "wrong_error": "text",
     "correct_page": "count",        "wrong_page": "num"},
    {"correct_name": "account_name", "wrong_name": "account",
     "correct_list": "payload",      "wrong_list": "response",
     "correct_error": "error_detail","wrong_error": "err",
     "correct_page": "page_limit",   "wrong_page": "batch"},
]

PORTS = [9000, 9001, 9002, 9003, 9004]


class Generator(TaskGenerator):
    task_id = "MULTI8_sdk_mismatch"
    domain = "api"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = FIELD_CONFIGS[seed % len(FIELD_CONFIGS)]
        port = PORTS[seed % len(PORTS)]

        workspace_files = {
            "sdk_client.py": self._gen_sdk_buggy(cfg, port),
            "api_spec.yaml": self._gen_spec_yaml(cfg, port),
            "mock_server.py": self._gen_mock_server(cfg, port),
            "test_sdk.py": self._gen_tests(cfg, port),
        }

        expected = {
            "seed": seed,
            "correct_name_field": cfg["correct_name"],
            "wrong_name_field": cfg["wrong_name"],
            "correct_list_key": cfg["correct_list"],
            "wrong_list_key": cfg["wrong_list"],
            "correct_error_field": cfg["correct_error"],
            "wrong_error_field": cfg["wrong_error"],
            "correct_page_param": cfg["correct_page"],
            "wrong_page_param": cfg["wrong_page"],
            "port": port,
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
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "medium", "category": "Multi-language"},
        )

    def _gen_sdk_buggy(self, cfg, port):
        return f'''"""Auto-generated SDK client — OUT OF DATE with current API spec."""
import json
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "http://localhost:{port}"


class APIError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(f"API Error {{status}}: {{message}}")


class UserClient:
    """Client for the Users API."""

    def __init__(self, base_url=None):
        self.base_url = base_url or BASE_URL

    def create_user(self, name, email):
        """Create a new user."""
        payload = json.dumps({{
            "{cfg["wrong_name"]}": name,
            "email": email,
        }}).encode()
        req = urllib.request.Request(
            f"{{self.base_url}}/api/users",
            data=payload,
            headers={{"Content-Type": "application/json"}},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
            raise APIError(e.code, body.get("{cfg["wrong_error"]}", "Unknown error"))

    def list_users(self, page=1, page_size=10):
        """List users with pagination."""
        params = urllib.parse.urlencode({{
            "page": page,
            "{cfg["wrong_page"]}": page_size,
        }})
        req = urllib.request.Request(
            f"{{self.base_url}}/api/users?{{params}}",
            method="GET",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return data.get("{cfg["wrong_list"]}", [])

    def get_user(self, user_id):
        """Get a single user by ID."""
        req = urllib.request.Request(
            f"{{self.base_url}}/api/users/{{user_id}}",
            method="GET",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
            raise APIError(e.code, body.get("{cfg["wrong_error"]}", "Unknown error"))
'''

    def _gen_spec_yaml(self, cfg, port):
        return f'''openapi: "3.0.3"
info:
  title: Users API
  version: "2.0.0"
servers:
  - url: http://localhost:{port}
paths:
  /api/users:
    get:
      summary: List users
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: {cfg["correct_page"]}
          in: query
          schema:
            type: integer
            default: 10
      responses:
        "200":
          description: List of users
          content:
            application/json:
              schema:
                type: object
                properties:
                  {cfg["correct_list"]}:
                    type: array
                    items:
                      $ref: "#/components/schemas/User"
                  total:
                    type: integer
    post:
      summary: Create user
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required:
                - {cfg["correct_name"]}
                - email
              properties:
                {cfg["correct_name"]}:
                  type: string
                email:
                  type: string
                  format: email
      responses:
        "201":
          description: User created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
        "400":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
  /api/users/{{id}}:
    get:
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        "200":
          description: User details
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
        "404":
          description: Not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        {cfg["correct_name"]}:
          type: string
        email:
          type: string
        created_at:
          type: string
          format: date-time
    Error:
      type: object
      properties:
        {cfg["correct_error"]}:
          type: string
'''

    def _gen_mock_server(self, cfg, port):
        return f'''"""Mock server implementing the current API spec. Do NOT modify."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

USERS = []
NEXT_ID = 1


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        global USERS
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/api/users":
            page = int(qs.get("page", [1])[0])
            limit = int(qs.get("{cfg["correct_page"]}", [10])[0])
            start = (page - 1) * limit
            end = start + limit
            self._send(200, {{
                "{cfg["correct_list"]}": USERS[start:end],
                "total": len(USERS),
            }})
        elif parsed.path.startswith("/api/users/"):
            uid = int(parsed.path.split("/")[-1])
            user = next((u for u in USERS if u["id"] == uid), None)
            if user:
                self._send(200, user)
            else:
                self._send(404, {{"{cfg["correct_error"]}": "User not found"}})
        else:
            self._send(404, {{"{cfg["correct_error"]}": "Not found"}})

    def do_POST(self):
        global USERS, NEXT_ID
        if self.path == "/api/users":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            name = body.get("{cfg["correct_name"]}")
            email = body.get("email")
            if not name or not email:
                self._send(400, {{
                    "{cfg["correct_error"]}": "{cfg["correct_name"]} and email are required"
                }})
                return
            user = {{
                "id": NEXT_ID,
                "{cfg["correct_name"]}": name,
                "email": email,
                "created_at": "2024-01-01T00:00:00Z",
            }}
            NEXT_ID += 1
            USERS.append(user)
            self._send(201, user)
        else:
            self._send(404, {{"{cfg["correct_error"]}": "Not found"}})


def run(port={port}):
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.serve_forever()


def reset():
    global USERS, NEXT_ID
    USERS = []
    NEXT_ID = 1


if __name__ == "__main__":
    print(f"Mock server on :{port}")
    run()
'''

    def _gen_tests(self, cfg, port):
        return f'''"""
Test suite for MULTI8_sdk_mismatch. Do NOT modify.
"""
import json
import threading
import time
import unittest
from http.server import HTTPServer

import mock_server


class SDKTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        mock_server.reset()
        cls.server = HTTPServer(("127.0.0.1", {port}), mock_server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        mock_server.reset()

    def test_create_user_sends_correct_field(self):
        from sdk_client import UserClient
        client = UserClient()
        user = client.create_user("Alice", "alice@example.com")
        self.assertEqual(user["{cfg["correct_name"]}"], "Alice")

    def test_create_user_returns_id(self):
        from sdk_client import UserClient
        client = UserClient()
        user = client.create_user("Bob", "bob@example.com")
        self.assertIn("id", user)

    def test_list_users_returns_list(self):
        from sdk_client import UserClient
        client = UserClient()
        client.create_user("Charlie", "charlie@example.com")
        users = client.list_users()
        self.assertIsInstance(users, list)
        self.assertGreater(len(users), 0)

    def test_list_users_pagination(self):
        from sdk_client import UserClient
        client = UserClient()
        for i in range(5):
            client.create_user(f"User{{i}}", f"u{{i}}@example.com")
        users = client.list_users(page=1, page_size=2)
        self.assertEqual(len(users), 2)

    def test_get_user(self):
        from sdk_client import UserClient
        client = UserClient()
        created = client.create_user("Diana", "diana@example.com")
        fetched = client.get_user(created["id"])
        self.assertEqual(fetched["{cfg["correct_name"]}"], "Diana")

    def test_error_handling_not_found(self):
        from sdk_client import UserClient, APIError
        client = UserClient()
        with self.assertRaises(APIError) as ctx:
            client.get_user(99999)
        self.assertEqual(ctx.exception.status, 404)

    def test_error_message_parsed(self):
        from sdk_client import UserClient, APIError
        client = UserClient()
        with self.assertRaises(APIError) as ctx:
            client.get_user(99999)
        self.assertIn("not found", ctx.exception.message.lower())

    def test_create_user_validation_error(self):
        from sdk_client import UserClient, APIError
        client = UserClient()
        with self.assertRaises(APIError) as ctx:
            client.create_user("", "")
        self.assertEqual(ctx.exception.status, 400)


if __name__ == "__main__":
    unittest.main()
'''
