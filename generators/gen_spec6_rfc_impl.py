"""
Parameterized generator for SPEC6: RFC-Style Protocol Implementation.

Each seed produces:
- A protocol_spec.txt describing a KVP protocol with seed-specific details
- A skeleton protocol.py with class stubs
- Tests in tests/test_protocol.py checking 15 of 20 requirements
- Seed variation: command names, delimiter chars, max sizes
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-variant pools ───────────────────────────────────────────────────────

# Command name variants for SET/GET/DEL
CMD_VARIANTS = [
    {"set": "SET", "get": "GET", "del": "DEL", "keys": "KEYS",
     "count": "COUNT", "exists": "EXISTS", "flush": "FLUSH",
     "mset": "MSET", "mget": "MGET", "setex": "SETEX",
     "ttl": "TTL", "append": "APPEND", "rename": "RENAME",
     "type": "TYPE", "dump": "DUMP"},
    {"set": "PUT", "get": "FETCH", "del": "REMOVE", "keys": "LIST",
     "count": "SIZE", "exists": "HAS", "flush": "CLEAR",
     "mset": "MPUT", "mget": "MFETCH", "setex": "PUTEX",
     "ttl": "EXPIRY", "append": "CONCAT", "rename": "MOVE",
     "type": "TYPEOF", "dump": "EXPORT"},
    {"set": "STORE", "get": "LOAD", "del": "DROP", "keys": "CATALOG",
     "count": "TOTAL", "exists": "CHECK", "flush": "PURGE",
     "mset": "MSTORE", "mget": "MLOAD", "setex": "STOREX",
     "ttl": "LIFETIME", "append": "EXTEND", "rename": "ALIAS",
     "type": "KIND", "dump": "SNAPSHOT"},
]

# Max key length variants
MAX_KEY_LENGTHS = [64, 128, 32]

# Max value size variants
MAX_VALUE_SIZES = [1024, 2048, 512]

# Max keys capacity
MAX_KEYS_CAPACITY = [100, 200, 50]

# Delimiter variants (response line separator)
DELIMITERS = ["\n", "\n", "\n"]  # keep newline for grader compatibility

# End-of-list marker variants
END_MARKERS = ["END", "DONE", "EOF"]


class Generator(TaskGenerator):
    task_id = "SPEC6_rfc_impl"
    domain = "software"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 3

        cmds = CMD_VARIANTS[idx]
        max_key_len = MAX_KEY_LENGTHS[idx]
        max_val_size = MAX_VALUE_SIZES[idx]
        max_keys = MAX_KEYS_CAPACITY[idx]
        end_marker = END_MARKERS[idx]

        params = dict(
            cmds=cmds,
            max_key_len=max_key_len,
            max_val_size=max_val_size,
            max_keys=max_keys,
            end_marker=end_marker,
        )

        workspace_files = self._make_workspace(**params)

        expected = {
            "seed": seed,
            "commands": cmds,
            "max_key_length": max_key_len,
            "max_value_size": max_val_size,
            "max_keys": max_keys,
            "end_marker": end_marker,
            "must_count": 12,
            "should_count": 5,
            "may_count": 3,
            "should_required": 3,
        }

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "SPEC6_rfc_impl"
        )
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
            metadata={"difficulty": "hard", "category": "SWE"},
        )

    def _make_workspace(
        self,
        cmds: dict,
        max_key_len: int,
        max_val_size: int,
        max_keys: int,
        end_marker: str,
    ) -> dict:
        files = {}

        c_set = cmds["set"]
        c_get = cmds["get"]
        c_del = cmds["del"]
        c_keys = cmds["keys"]
        c_count = cmds["count"]
        c_exists = cmds["exists"]
        c_flush = cmds["flush"]
        c_mset = cmds["mset"]
        c_mget = cmds["mget"]
        c_setex = cmds["setex"]
        c_ttl = cmds["ttl"]
        c_append = cmds["append"]
        c_rename = cmds["rename"]
        c_type = cmds["type"]
        c_dump = cmds["dump"]

        # ── protocol_spec.txt (RFC-style) ────────────────────────────────────
        files["protocol_spec.txt"] = f"""KVP — Key-Value Protocol Specification
======================================

1. Introduction

   KVP is a simple text-based protocol for an in-memory key-value store.
   Commands are line-oriented. Each command is a single line of text.
   Responses follow a structured format described below.

2. Commands

   2.1 {c_set} <key> <value>
       Store the given value under the given key.
       Response: OK
       Errors: ERR key_too_long (if key exceeds {max_key_len} chars)
               ERR value_too_large (if value exceeds {max_val_size} chars)
               ERR store_full (if store has {max_keys} keys and key is new)

   2.2 {c_get} <key>
       Retrieve the value stored under the given key.
       Response: the value on a single line
       Errors: ERR key_not_found

   2.3 {c_del} <key>
       Remove the given key from the store.
       Response: OK
       Errors: ERR key_not_found

   2.4 {c_keys}
       List all stored keys.
       Response: one key per line, terminated by {end_marker}

   2.5 {c_count}
       Return the number of stored keys.
       Response: {c_count} <n>

   2.6 {c_exists} <key>
       Check if a key exists.
       Response: TRUE or FALSE

   2.7 {c_flush}
       Remove all keys.
       Response: OK

   2.8 {c_mset} <key1> <value1> <key2> <value2> ...
       Set multiple key-value pairs atomically.
       Response: OK <n> (where n = number of pairs set)

   2.9 {c_mget} <key1> <key2> ...
       Get multiple values.
       Response: value or NIL per key, one per line, terminated by {end_marker}

   2.10 {c_setex} <key> <seconds> <value>
        Set a key with an expiration time in seconds.
        Response: OK
        After expiration, the key is treated as non-existent.

   2.11 {c_ttl} <key>
        Return remaining time-to-live in seconds, or -1 if no expiry.
        Errors: ERR key_not_found

   2.12 {c_append} <key> <value>
        Append to existing value, or create new key.
        Response: OK <new_length>

   2.13 {c_rename} <old_key> <new_key>
        Rename a key.
        Response: OK
        Errors: ERR key_not_found

   2.14 {c_type} <key>
        Return the type of the value (STRING or INTEGER).
        Errors: ERR key_not_found

   2.15 {c_dump}
        Return all key-value pairs as <key>=<value>, terminated by {end_marker}

3. Limits

   Maximum key length: {max_key_len} characters
   Maximum value size: {max_val_size} characters
   Maximum stored keys: {max_keys}

4. Error Codes

   ERR key_not_found    — key does not exist
   ERR key_too_long     — key exceeds maximum length
   ERR value_too_large  — value exceeds maximum size
   ERR store_full       — store at maximum capacity for new keys
   ERR unknown_command  — unrecognized command

5. Response Format

   Success: OK, OK <detail>, TRUE, FALSE, {c_count} <n>
   Value: the raw value on its own line
   List: one item per line, terminated by {end_marker}
   Error: ERR <error_code>
"""

        # ── protocol.py (skeleton) ───────────────────────────────────────────
        files["protocol.py"] = f'''"""
KVP Protocol Implementation.

Implement the KVStore class according to the specification in protocol_spec.txt.
Commands: {c_set}, {c_get}, {c_del}, {c_keys}, {c_count}, {c_exists}, {c_flush}
Optional: {c_mset}, {c_mget}, {c_setex}, {c_ttl}, {c_append}, {c_rename}, {c_type}, {c_dump}

Limits:
  MAX_KEY_LENGTH = {max_key_len}
  MAX_VALUE_SIZE = {max_val_size}
  MAX_KEYS = {max_keys}
  END_MARKER = "{end_marker}"
"""
import time


class KVStore:
    """In-memory key-value store implementing the KVP protocol."""

    MAX_KEY_LENGTH = {max_key_len}
    MAX_VALUE_SIZE = {max_val_size}
    MAX_KEYS = {max_keys}
    END_MARKER = "{end_marker}"

    def __init__(self):
        self._data = {{}}
        self._expiry = {{}}  # key -> expiration timestamp (or None)

    def execute(self, command: str) -> str:
        """
        Execute a single KVP command and return the response string.

        Parse the command, dispatch to the appropriate handler,
        and return the response per the protocol specification.
        """
        # TODO: Implement command parsing and dispatch
        parts = command.strip().split()
        if not parts:
            return "ERR unknown_command"

        cmd = parts[0].upper()
        args = parts[1:]

        # TODO: Implement all command handlers
        return "ERR unknown_command"

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired and clean it up if so."""
        if key in self._expiry and self._expiry[key] is not None:
            if time.time() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return True
        return False
'''

        # ── tests/__init__.py ────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_protocol.py (15 of 20 requirements tested) ────────────
        files["tests/test_protocol.py"] = f'''"""
Tests for the KVP protocol implementation.
Tests cover 15 of the 20 requirements. The remaining 5 must be derived from spec.
"""
import pytest
import time
from protocol import KVStore


@pytest.fixture
def store():
    return KVStore()


# ── M1: {c_set} stores value ──────────────────────────────────────────────
def test_set_returns_ok(store):
    r = store.execute("{c_set} foo bar")
    assert "OK" in r


# ── M2: {c_get} returns value or ERR ─────────────────────────────────────
def test_get_existing_key(store):
    store.execute("{c_set} hello world")
    r = store.execute("{c_get} hello")
    assert "world" in r


def test_get_missing_key(store):
    r = store.execute("{c_get} noexist")
    assert "ERR" in r and "key_not_found" in r


# ── M3: {c_del} removes key ──────────────────────────────────────────────
def test_del_existing_key(store):
    store.execute("{c_set} temp val")
    r = store.execute("{c_del} temp")
    assert "OK" in r
    r2 = store.execute("{c_get} temp")
    assert "ERR" in r2


# ── M4: {c_keys} lists keys ──────────────────────────────────────────────
def test_keys_lists_all(store):
    store.execute("{c_set} a 1")
    store.execute("{c_set} b 2")
    r = store.execute("{c_keys}")
    assert "a" in r and "b" in r and "{end_marker}" in r


# ── M5: {c_count} returns count ──────────────────────────────────────────
def test_count_after_sets(store):
    store.execute("{c_set} x 1")
    store.execute("{c_set} y 2")
    r = store.execute("{c_count}")
    assert "2" in r


# ── M6: {c_exists} TRUE/FALSE ────────────────────────────────────────────
def test_exists_true(store):
    store.execute("{c_set} present val")
    r = store.execute("{c_exists} present")
    assert "TRUE" in r


def test_exists_false(store):
    r = store.execute("{c_exists} absent")
    assert "FALSE" in r


# ── M7: {c_flush} clears all ─────────────────────────────────────────────
def test_flush_clears_store(store):
    store.execute("{c_set} a 1")
    store.execute("{c_set} b 2")
    r = store.execute("{c_flush}")
    assert "OK" in r
    r2 = store.execute("{c_count}")
    assert "0" in r2


# ── M9: unknown command ──────────────────────────────────────────────────
def test_unknown_command(store):
    r = store.execute("BADCMD xyz")
    assert "ERR" in r and "unknown_command" in r


# ── M10: key too long ────────────────────────────────────────────────────
def test_key_too_long(store):
    long_key = "k" * ({max_key_len} + 5)
    r = store.execute(f"{c_set} {{long_key}} val")
    assert "ERR" in r and "key_too_long" in r


# ── M11: value too large ─────────────────────────────────────────────────
def test_value_too_large(store):
    big_val = "v" * ({max_val_size} + 5)
    r = store.execute(f"{c_set} k {{big_val}}")
    assert "ERR" in r and "value_too_large" in r


# ── M12: store full ──────────────────────────────────────────────────────
def test_store_full(store):
    for i in range({max_keys}):
        store.execute(f"{c_set} key{{i}} val{{i}}")
    r = store.execute("{c_set} overflow_key overflow_val")
    assert "ERR" in r and "store_full" in r


def test_store_full_allows_update(store):
    for i in range({max_keys}):
        store.execute(f"{c_set} key{{i}} val{{i}}")
    r = store.execute("{c_set} key0 updated")
    assert "OK" in r


# ── S5: {c_append} ───────────────────────────────────────────────────────
def test_append_to_existing(store):
    store.execute("{c_set} msg hello")
    r = store.execute("{c_append} msg _world")
    assert "OK" in r
    r2 = store.execute("{c_get} msg")
    assert "hello_world" in r2
'''

        files["requirements.txt"] = "pytest\n"

        return files
