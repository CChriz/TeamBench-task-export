"""
Parameterized generator for PIPE3: Stream Processing Pipeline.

Each seed produces a different event domain (user analytics, IoT sensors, financial
transactions) with different field names and schemas, but the same 3 serialization
mismatch bugs:
  1. Producer uses json.dumps(default=str) for datetime (produces space-separated format)
  2. Processor wraps output in {"data": ...} envelope but sink expects bare objects
  3. Processor writes with latin-1 encoding but sink reads UTF-8
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


DOMAINS = [
    {
        # Seed 0: User analytics
        "name": "user_analytics",
        "event_class": "UserEvent",
        "id_field": "event_id",
        "ts_field": "timestamp",
        "user_field": "user_name",
        "action_field": "action",
        "value_field": "page_url",
        "sample_user": "M\u00fcller",
        "sample_action": "page_view",
        "sample_value": "https://example.com/caf\u00e9",
        "output_ext": "jsonl",
        "actions": ["page_view", "click", "scroll", "purchase"],
    },
    {
        # Seed 1: IoT sensors
        "name": "iot_sensors",
        "event_class": "SensorReading",
        "id_field": "reading_id",
        "ts_field": "measured_at",
        "user_field": "sensor_name",
        "action_field": "metric_type",
        "value_field": "location",
        "sample_user": "Stra\u00dfe-Sensor-01",
        "sample_action": "temperature",
        "sample_value": "B\u00fcro Geb\u00e4ude A",
        "output_ext": "jsonl",
        "actions": ["temperature", "humidity", "pressure", "vibration"],
    },
    {
        # Seed 2: Financial transactions
        "name": "financial_txn",
        "event_class": "Transaction",
        "id_field": "txn_id",
        "ts_field": "executed_at",
        "user_field": "account_holder",
        "action_field": "txn_type",
        "value_field": "description",
        "sample_user": "Ren\u00e9 Fran\u00e7ois",
        "sample_action": "transfer",
        "sample_value": "Paiement \u00e0 l'\u00e9tranger \u20ac500",
        "output_ext": "jsonl",
        "actions": ["deposit", "withdrawal", "transfer", "fee"],
    },
]


class Generator(TaskGenerator):
    task_id = "PIPE3_stream_processing"
    domain = "Data Engineering"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        d = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(d, seed)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "PIPE3_stream_processing")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="PIPE3_stream_processing",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": [
                    "B1_datetime_isoformat",
                    "B2_no_envelope",
                    "B3_utf8_encoding",
                ],
                "seed": seed,
                "domain": d["name"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Data Engineering"},
        )

    def _make_workspace(self, d: dict, seed: int) -> dict:
        files = {}
        files["models.py"] = self._models(d)
        files["producer.py"] = self._producer(d)
        files["processor.py"] = self._processor(d)
        files["sink.py"] = self._sink(d)
        files["tests/__init__.py"] = ""
        files["tests/test_pipeline.py"] = self._test_pipeline(d)
        files["tests/test_serialization.py"] = self._test_serialization(d)
        return files

    def _models(self, d: dict) -> str:
        actions_repr = ", ".join(f'"{a}"' for a in d["actions"])
        return f'''"""
Shared event schema for {d["name"]} pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


VALID_ACTIONS = [{actions_repr}]


@dataclass
class {d["event_class"]}:
    """{d["event_class"]} data model."""
    {d["id_field"]}: str
    {d["ts_field"]}: datetime
    {d["user_field"]}: str
    {d["action_field"]}: str
    {d["value_field"]}: str

    def validate(self) -> bool:
        """Check that the event has valid fields."""
        if not self.{d["id_field"]}:
            raise ValueError("{d["id_field"]} is required")
        if self.{d["action_field"]} not in VALID_ACTIONS:
            raise ValueError(f"Invalid action: {{self.{d["action_field"]}}}")
        return True
'''

    def _producer(self, d: dict) -> str:
        return f'''"""
Event producer for {d["name"]} pipeline.

Generates JSON-serialized events and writes them to an output file.

Bug 1: Uses json.dumps(default=str) for datetime serialization, which produces
       "2023-11-14 22:13:20" format instead of ISO 8601 "2023-11-14T22:13:20".
"""
import json
import os
from datetime import datetime
from models import {d["event_class"]}


def serialize_event(event: {d["event_class"]}) -> str:
    """Serialize an event to JSON string.

    Bug: default=str converts datetime to "YYYY-MM-DD HH:MM:SS" (space-separated).
    The processor expects ISO 8601 format "YYYY-MM-DDTHH:MM:SS" (T-separated).
    Fix: use .isoformat() for datetime fields.
    """
    data = {{
        "{d["id_field"]}": event.{d["id_field"]},
        "{d["ts_field"]}": event.{d["ts_field"]},
        "{d["user_field"]}": event.{d["user_field"]},
        "{d["action_field"]}": event.{d["action_field"]},
        "{d["value_field"]}": event.{d["value_field"]},
    }}
    # Bug 1: default=str produces "2023-11-14 22:13:20" not ISO 8601
    return json.dumps(data, default=str)


def produce_events(events: list[{d["event_class"]}], output_path: str) -> None:
    """Write events to output file, one JSON object per line."""
    with open(output_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(serialize_event(event) + "\\n")
'''

    def _processor(self, d: dict) -> str:
        return f'''"""
Event processor for {d["name"]} pipeline.

Reads JSON events from producer, transforms them, and writes processed output.

Bug 2: Wraps output in {{"data": ...}} envelope, but sink expects bare objects.
Bug 3: Writes output with latin-1 encoding, but sink reads UTF-8.
"""
import json
import os
from datetime import datetime


def parse_timestamp(ts_str: str) -> datetime:
    """Parse a timestamp string into a datetime object.

    Expects ISO 8601 format: "YYYY-MM-DDTHH:MM:SS"
    Will fail on "YYYY-MM-DD HH:MM:SS" (space instead of T).
    """
    return datetime.fromisoformat(ts_str)


def transform_event(event_data: dict) -> dict:
    """Transform a raw event dict into processed output.

    Adds a processed_at timestamp and normalizes fields.
    """
    processed = dict(event_data)
    # Parse and re-format the timestamp to ensure consistency
    ts = parse_timestamp(event_data["{d["ts_field"]}"])
    processed["{d["ts_field"]}"] = ts.isoformat()
    processed["processed_at"] = datetime.utcnow().isoformat()
    processed["{d["action_field"]}"] = event_data["{d["action_field"]}"].upper()
    return processed


def process_events(input_path: str, output_path: str) -> int:
    """Read events, transform, and write to output.

    Bug 2: Wraps each output line in {{"data": ...}} envelope.
    Bug 3: Opens output file with latin-1 encoding.

    Returns number of events processed.
    """
    count = 0
    # Bug 3: latin-1 encoding — will corrupt non-ASCII characters for UTF-8 reader
    with open(input_path, "r", encoding="utf-8") as fin, \\
         open(output_path, "w", encoding="latin-1") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            event_data = json.loads(line)
            processed = transform_event(event_data)
            # Bug 2: wrapping in envelope — sink expects bare objects
            envelope = {{"data": processed}}
            fout.write(json.dumps(envelope, ensure_ascii=False) + "\\n")
            count += 1
    return count
'''

    def _sink(self, d: dict) -> str:
        return f'''"""
Output sink for {d["name"]} pipeline.

Reads processed events and writes final output. Expects:
  - Bare JSON objects (no envelope wrapping)
  - UTF-8 encoded input
  - ISO 8601 timestamps
"""
import json
import os
from datetime import datetime


def load_processed_events(input_path: str) -> list[dict]:
    """Load processed events from a JSONL file.

    Expects:
      - Each line is a bare JSON object (NOT wrapped in {{"data": ...}})
      - File is UTF-8 encoded
      - Timestamps are ISO 8601
    """
    events = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            # Expect bare object with direct field access
            _ = event["{d["id_field"]}"]  # Will KeyError if wrapped in envelope
            _ = event["{d["ts_field"]}"]
            events.append(event)
    return events


def write_summary(events: list[dict], output_path: str) -> dict:
    """Write a summary of processed events."""
    summary = {{
        "total_events": len(events),
        "actions": {{}},
        "users": set(),
    }}
    for evt in events:
        action = evt["{d["action_field"]}"]
        summary["actions"][action] = summary["actions"].get(action, 0) + 1
        summary["users"].add(evt["{d["user_field"]}"])

    summary["unique_users"] = len(summary["users"])
    summary["users"] = sorted(summary["users"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary
'''

    def _test_pipeline(self, d: dict) -> str:
        return f'''"""
End-to-end pipeline tests for {d["name"]}.
"""
import json
import os
import tempfile
import pytest
from datetime import datetime
from models import {d["event_class"]}
from producer import serialize_event, produce_events
from processor import process_events
from sink import load_processed_events, write_summary


def _make_event(**overrides):
    defaults = {{
        "{d["id_field"]}": "evt-001",
        "{d["ts_field"]}": datetime(2023, 11, 14, 22, 13, 20),
        "{d["user_field"]}": "{d["sample_user"]}",
        "{d["action_field"]}": "{d["sample_action"]}",
        "{d["value_field"]}": "{d["sample_value"]}",
    }}
    defaults.update(overrides)
    return {d["event_class"]}(**defaults)


class TestEndToEnd:
    """Full pipeline: produce -> process -> sink."""

    def test_full_pipeline(self, tmp_path):
        """Events flow through all 3 stages without error."""
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"
        summary = tmp_path / "summary.json"

        events = [
            _make_event({d["id_field"]}="evt-001"),
            _make_event(
                {d["id_field"]}="evt-002",
                {d["user_field"]}="{d["sample_user"]}",
                {d["action_field"]}="{d["actions"][1]}",
            ),
        ]

        produce_events(events, str(produced))
        count = process_events(str(produced), str(processed))
        assert count == 2

        loaded = load_processed_events(str(processed))
        assert len(loaded) == 2

        result = write_summary(loaded, str(summary))
        assert result["total_events"] == 2

    def test_non_ascii_survives_pipeline(self, tmp_path):
        """Non-ASCII characters (accents, euro sign) must survive the full pipeline."""
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"

        events = [_make_event(
            {d["user_field"]}="{d["sample_user"]}",
            {d["value_field"]}="{d["sample_value"]}",
        )]

        produce_events(events, str(produced))
        process_events(str(produced), str(processed))
        loaded = load_processed_events(str(processed))

        assert loaded[0]["{d["user_field"]}"] == "{d["sample_user"]}"
        assert loaded[0]["{d["value_field"]}"] == "{d["sample_value"]}"

    def test_multiple_events_correct_count(self, tmp_path):
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"
        summary = tmp_path / "summary.json"

        events = [
            _make_event({d["id_field"]}=f"evt-{{i:03d}}")
            for i in range(5)
        ]

        produce_events(events, str(produced))
        process_events(str(produced), str(processed))
        loaded = load_processed_events(str(processed))
        result = write_summary(loaded, str(summary))

        assert result["total_events"] == 5
'''

    def _test_serialization(self, d: dict) -> str:
        return f'''"""
Targeted serialization tests for each of the 3 bugs.
"""
import json
import os
import tempfile
import pytest
from datetime import datetime
from models import {d["event_class"]}
from producer import serialize_event
from processor import parse_timestamp, transform_event, process_events
from sink import load_processed_events


def _make_event(**overrides):
    defaults = {{
        "{d["id_field"]}": "evt-001",
        "{d["ts_field"]}": datetime(2023, 11, 14, 22, 13, 20),
        "{d["user_field"]}": "TestUser",
        "{d["action_field"]}": "{d["sample_action"]}",
        "{d["value_field"]}": "test-value",
    }}
    defaults.update(overrides)
    return {d["event_class"]}(**defaults)


class TestBug1DatetimeFormat:
    """Bug 1: Producer must use ISO 8601 (T-separated), not space-separated."""

    def test_serialized_timestamp_has_T_separator(self):
        event = _make_event()
        serialized = serialize_event(event)
        data = json.loads(serialized)
        ts = data["{d["ts_field"]}"]
        assert "T" in ts, (
            f"Timestamp must use ISO 8601 T separator, got: {{ts!r}}. "
            "Use .isoformat() instead of default=str."
        )

    def test_serialized_timestamp_parseable_by_fromisoformat(self):
        event = _make_event()
        serialized = serialize_event(event)
        data = json.loads(serialized)
        ts = data["{d["ts_field"]}"]
        # This must not raise
        parsed = datetime.fromisoformat(ts)
        assert parsed.year == 2023
        assert parsed.month == 11

    def test_processor_can_parse_producer_output(self):
        """The processor's parse_timestamp must work on producer output."""
        event = _make_event()
        serialized = serialize_event(event)
        data = json.loads(serialized)
        # Must not raise ValueError
        parsed = parse_timestamp(data["{d["ts_field"]}"])
        assert isinstance(parsed, datetime)


class TestBug2NoEnvelope:
    """Bug 2: Processor must emit bare objects, not wrapped in {{"data": ...}}."""

    def test_processed_output_is_bare_object(self, tmp_path):
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"

        event = _make_event({d["user_field"]}="SimpleUser")
        with open(produced, "w") as f:
            f.write(serialize_event(event) + "\\n")

        process_events(str(produced), str(processed))

        with open(processed, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        data = json.loads(line)

        assert "data" not in data or isinstance(data.get("data"), str), (
            f"Processor output must be bare object, not envelope. "
            f"Got key 'data' wrapping: {{list(data.keys())}}"
        )
        assert "{d["id_field"]}" in data, (
            f"Bare object must have '{d["id_field"]}' at top level, got: {{list(data.keys())}}"
        )

    def test_sink_can_load_processed(self, tmp_path):
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"

        event = _make_event({d["user_field"]}="SimpleUser")
        with open(produced, "w") as f:
            f.write(serialize_event(event) + "\\n")

        process_events(str(produced), str(processed))
        loaded = load_processed_events(str(processed))
        assert len(loaded) == 1
        assert loaded[0]["{d["id_field"]}"] == "evt-001"


class TestBug3Utf8Encoding:
    """Bug 3: Processor must write UTF-8, not latin-1."""

    def test_non_ascii_roundtrip(self, tmp_path):
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"

        event = _make_event(
            {d["user_field"]}="{d["sample_user"]}",
            {d["value_field"]}="{d["sample_value"]}",
        )
        with open(produced, "w", encoding="utf-8") as f:
            f.write(serialize_event(event) + "\\n")

        process_events(str(produced), str(processed))

        # Sink reads UTF-8 — must not raise UnicodeDecodeError
        loaded = load_processed_events(str(processed))
        assert loaded[0]["{d["user_field"]}"] == "{d["sample_user"]}"

    def test_euro_sign_preserved(self, tmp_path):
        """Euro sign and other non-latin1 chars must survive."""
        produced = tmp_path / "produced.jsonl"
        processed = tmp_path / "processed.jsonl"

        event = _make_event({d["value_field"]}="Price: \\u20ac99.99")
        with open(produced, "w", encoding="utf-8") as f:
            f.write(serialize_event(event) + "\\n")

        process_events(str(produced), str(processed))
        loaded = load_processed_events(str(processed))
        assert "\\u20ac" in loaded[0]["{d["value_field"]}"]
'''
