"""
Parameterized generator for CROSS5: Event Schema Reconciliation.

Each seed produces a Python event producer + Java event consumer with 5 field name
mismatches and 2 encoding bugs. The schema is the source of truth.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized event domain pools ────────────────────────────────

EVENT_DOMAINS = [
    {
        "event_type": "user_created",
        "event_type_camel": "UserCreated",
        "service_name": "user-service",
        "payload_desc": "user profile data",
        "sample_payload_fields": [
            ("username", "String", '"alice"'),
            ("email", "String", '"alice@example.com"'),
            ("role", "String", '"admin"'),
        ],
    },
    {
        "event_type": "order_placed",
        "event_type_camel": "OrderPlaced",
        "service_name": "order-service",
        "payload_desc": "order details",
        "sample_payload_fields": [
            ("orderId", "String", '"ORD-12345"'),
            ("amount", "double", "99.99"),
            ("currency", "String", '"USD"'),
        ],
    },
    {
        "event_type": "payment_processed",
        "event_type_camel": "PaymentProcessed",
        "service_name": "payment-service",
        "payload_desc": "payment transaction data",
        "sample_payload_fields": [
            ("transactionId", "String", '"TXN-98765"'),
            ("amount", "double", "150.00"),
            ("status", "String", '"completed"'),
        ],
    },
    {
        "event_type": "inventory_updated",
        "event_type_camel": "InventoryUpdated",
        "service_name": "inventory-service",
        "payload_desc": "stock level changes",
        "sample_payload_fields": [
            ("sku", "String", '"SKU-ABC123"'),
            ("quantity", "int", "42"),
            ("warehouse", "String", '"west-1"'),
        ],
    },
    {
        "event_type": "notification_sent",
        "event_type_camel": "NotificationSent",
        "service_name": "notification-service",
        "payload_desc": "notification delivery data",
        "sample_payload_fields": [
            ("recipient", "String", '"user@example.com"'),
            ("channel", "String", '"email"'),
            ("templateId", "String", '"TMPL-001"'),
        ],
    },
]

SCHEMA_VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0"]

JAVA_PACKAGES = [
    "com.events.consumer",
    "com.platform.events",
    "com.messaging.handler",
    "io.events.processor",
    "org.eventbus.consumer",
]


class Generator(TaskGenerator):
    task_id = "CROSS5_event_schema"
    domain = "Cross-System"
    difficulty = "hard"
    languages = ["python", "java"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        domain = EVENT_DOMAINS[seed % len(EVENT_DOMAINS)]
        schema_version = SCHEMA_VERSIONS[seed % len(SCHEMA_VERSIONS)]
        java_package = JAVA_PACKAGES[seed % len(JAVA_PACKAGES)]

        workspace_files = self._make_workspace(domain, schema_version, java_package)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CROSS5_event_schema")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CROSS5_event_schema",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "field_mismatches_fixed": 5,
                "encoding_bugs_fixed": 2,
                "event_type": domain["event_type"],
                "service_name": domain["service_name"],
                "schema_version": schema_version,
                "correct_timestamp_format": "epoch_millis",
                "correct_binary_encoding": "base64",
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Cross-System"},
        )

    def _make_workspace(self, domain: dict, schema_version: str, java_package: str) -> dict:
        files = {}
        evt_type = domain["event_type"]
        evt_camel = domain["event_type_camel"]
        svc_name = domain["service_name"]
        payload_desc = domain["payload_desc"]
        payload_fields = domain["sample_payload_fields"]
        pkg_path = java_package.replace(".", "/")

        # ── schema/event_schema.json (source of truth, DO NOT MODIFY) ────
        payload_props = ""
        for fname, ftype, _ in payload_fields:
            jtype = "string" if ftype == "String" else ("number" if ftype in ("double", "int") else "string")
            payload_props += f'        "{fname}": {{"type": "{jtype}"}},\n'
        payload_props = payload_props.rstrip(",\n") + "\n"

        files["schema/event_schema.json"] = (
            '{\n'
            f'  "schemaVersion": "{schema_version}",\n'
            f'  "eventType": "{evt_type}",\n'
            '  "description": "Canonical event schema. This is the source of truth.",\n'
            '  "properties": {\n'
            '    "eventId": {"type": "string", "format": "uuid"},\n'
            '    "timestamp": {"type": "integer", "description": "Epoch milliseconds since Unix epoch"},\n'
            '    "payload": {\n'
            '      "type": "object",\n'
            f'      "description": "{payload_desc}",\n'
            '      "properties": {\n'
            f'{payload_props}'
            '      }\n'
            '    },\n'
            '    "sourceService": {"type": "string"},\n'
            '    "correlationId": {"type": "string", "format": "uuid"},\n'
            '    "binaryAttachment": {"type": "string", "encoding": "base64", "description": "Base64-encoded binary data"}\n'
            '  },\n'
            '  "required": ["eventId", "timestamp", "payload", "sourceService", "correlationId"]\n'
            '}\n'
        )

        # ── producer/event_producer.py (BUGGY: 5 field names + 1 encoding) ──
        files["producer/__init__.py"] = ""
        files["producer/event_producer.py"] = (
            '"""\n'
            f'Event producer for {svc_name}.\n'
            f'Publishes {evt_type} events.\n'
            '"""\n'
            'import json\n'
            'import uuid\n'
            'import base64\n'
            'from datetime import datetime, timezone\n'
            '\n'
            '\n'
            'class EventProducer:\n'
            f'    """Produces {evt_type} events for the message bus."""\n'
            '\n'
            '    def __init__(self, service_name: str = "' + svc_name + '"):\n'
            '        self.service_name = service_name\n'
            '\n'
            '    def create_event(self, payload: dict, binary_data: bytes = None) -> dict:\n'
            '        """\n'
            '        Create an event envelope.\n'
            '\n'
            '        BUG 1: Uses "event_id" instead of "eventId"\n'
            '        BUG 2: Uses "created_at" instead of "timestamp"\n'
            '        BUG 3: Uses "data" instead of "payload"\n'
            '        BUG 4: Uses "source_service" instead of "sourceService"\n'
            '        BUG 5: Uses "correlation_id" instead of "correlationId"\n'
            '        BUG 6: Sends ISO-8601 string instead of epoch milliseconds\n'
            '        """\n'
            '        event = {\n'
            '            "event_id": str(uuid.uuid4()),\n'
            '            "created_at": datetime.now(timezone.utc).isoformat(),\n'
            '            "data": payload,\n'
            '            "source_service": self.service_name,\n'
            '            "correlation_id": str(uuid.uuid4()),\n'
            '        }\n'
            '        if binary_data is not None:\n'
            '            event["binaryAttachment"] = base64.b64encode(binary_data).decode("utf-8")\n'
            '        return event\n'
            '\n'
            '    def serialize(self, event: dict) -> str:\n'
            '        """Serialize event to JSON string."""\n'
            '        return json.dumps(event)\n'
            '\n'
            '    def publish(self, payload: dict, binary_data: bytes = None) -> str:\n'
            '        """Create and serialize an event."""\n'
            '        event = self.create_event(payload, binary_data)\n'
            '        return self.serialize(event)\n'
        )

        # ── consumer/src/main/java/EventConsumer.java (BUGGY: hex decoding) ──
        field_declarations = ""
        field_assignments = ""
        for fname, ftype, _ in payload_fields:
            field_declarations += f"    private {ftype} {fname};\n"
            if ftype == "String":
                field_assignments += f'        this.{fname} = payload.has("{fname}") ? payload.getString("{fname}") : "";\n'
            elif ftype == "double":
                field_assignments += f'        this.{fname} = payload.has("{fname}") ? payload.getDouble("{fname}") : 0.0;\n'
            elif ftype == "int":
                field_assignments += f'        this.{fname} = payload.has("{fname}") ? payload.getInt("{fname}") : 0;\n'

        files[f"consumer/src/main/java/EventConsumer.java"] = (
            f'package {java_package};\n'
            '\n'
            'import org.json.JSONObject;\n'
            'import java.nio.charset.StandardCharsets;\n'
            'import java.util.Base64;\n'
            '\n'
            '/**\n'
            f' * Consumes {evt_type} events from the message bus.\n'
            ' * \n'
            ' * Uses camelCase field names as defined in the schema.\n'
            ' * BUG: Uses hex decoding for binary attachments instead of Base64.\n'
            ' */\n'
            'public class EventConsumer {\n'
            '    private String eventId;\n'
            '    private long timestamp;\n'
            '    private JSONObject payload;\n'
            '    private String sourceService;\n'
            '    private String correlationId;\n'
            '    private byte[] binaryAttachment;\n'
            '\n'
            f'{field_declarations}'
            '\n'
            '    public void consume(String jsonMessage) {\n'
            '        JSONObject event = new JSONObject(jsonMessage);\n'
            '\n'
            '        this.eventId = event.getString("eventId");\n'
            '        this.timestamp = event.getLong("timestamp");\n'
            '        this.payload = event.getJSONObject("payload");\n'
            '        this.sourceService = event.getString("sourceService");\n'
            '        this.correlationId = event.getString("correlationId");\n'
            '\n'
            '        // Parse payload fields\n'
            f'{field_assignments}'
            '\n'
            '        // BUG: Uses hex decoding instead of Base64\n'
            '        if (event.has("binaryAttachment")) {\n'
            '            String encoded = event.getString("binaryAttachment");\n'
            '            this.binaryAttachment = hexStringToByteArray(encoded);\n'
            '        }\n'
            '    }\n'
            '\n'
            '    /**\n'
            '     * Hex decoding utility — WRONG for this use case.\n'
            '     * The schema specifies Base64 encoding, not hex.\n'
            '     */\n'
            '    private static byte[] hexStringToByteArray(String s) {\n'
            '        int len = s.length();\n'
            '        byte[] data = new byte[len / 2];\n'
            '        for (int i = 0; i < len; i += 2) {\n'
            '            data[i / 2] = (byte) ((Character.digit(s.charAt(i), 16) << 4)\n'
            '                    + Character.digit(s.charAt(i + 1), 16));\n'
            '        }\n'
            '        return data;\n'
            '    }\n'
            '\n'
            '    public String getEventId() { return eventId; }\n'
            '    public long getTimestamp() { return timestamp; }\n'
            '    public JSONObject getPayload() { return payload; }\n'
            '    public String getSourceService() { return sourceService; }\n'
            '    public String getCorrelationId() { return correlationId; }\n'
            '    public byte[] getBinaryAttachment() { return binaryAttachment; }\n'
            '}\n'
        )

        # ── consumer/pom.xml (minimal, for structure) ────────────────────
        files["consumer/pom.xml"] = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
            '  <modelVersion>4.0.0</modelVersion>\n'
            f'  <groupId>{java_package}</groupId>\n'
            '  <artifactId>event-consumer</artifactId>\n'
            '  <version>1.0.0</version>\n'
            '  <dependencies>\n'
            '    <dependency>\n'
            '      <groupId>org.json</groupId>\n'
            '      <artifactId>json</artifactId>\n'
            '      <version>20231013</version>\n'
            '    </dependency>\n'
            '  </dependencies>\n'
            '</project>\n'
        )

        # ── tests/test_roundtrip.py ──────────────────────────────────────
        files["tests/__init__.py"] = ""
        files["tests/test_roundtrip.py"] = (
            '"""\n'
            'End-to-end roundtrip tests: producer -> JSON -> consumer field expectations.\n'
            '"""\n'
            'import json\n'
            'import sys\n'
            'import os\n'
            'import pytest\n'
            '\n'
            'sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))\n'
            'from producer.event_producer import EventProducer\n'
            '\n'
            '\n'
            '@pytest.fixture\n'
            'def producer():\n'
            f'    return EventProducer("{svc_name}")\n'
            '\n'
            '\n'
            'def test_event_has_eventId(producer):\n'
            '    """Event must use camelCase eventId, not snake_case."""\n'
            f'    event = producer.create_event({{"test": "data"}})\n'
            '    assert "eventId" in event, f"Missing eventId, got keys: {list(event.keys())}"\n'
            '    assert "event_id" not in event, "Should not have snake_case event_id"\n'
            '\n'
            '\n'
            'def test_event_has_timestamp_as_epoch(producer):\n'
            '    """Timestamp must be epoch milliseconds (integer), not ISO string."""\n'
            f'    event = producer.create_event({{"test": "data"}})\n'
            '    assert "timestamp" in event, f"Missing timestamp, got keys: {list(event.keys())}"\n'
            '    assert isinstance(event["timestamp"], (int, float)), \\\n'
            '        f"timestamp must be a number (epoch ms), got {type(event.get(\'timestamp\')).__name__}"\n'
            '\n'
            '\n'
            'def test_event_has_payload(producer):\n'
            '    """Event must use payload, not data."""\n'
            f'    event = producer.create_event({{"key": "value"}})\n'
            '    assert "payload" in event, f"Missing payload, got keys: {list(event.keys())}"\n'
            '    assert "data" not in event, "Should not have \'data\' key"\n'
            '\n'
            '\n'
            'def test_event_has_sourceService(producer):\n'
            '    """Event must use camelCase sourceService."""\n'
            f'    event = producer.create_event({{"test": "data"}})\n'
            '    assert "sourceService" in event, f"Missing sourceService, got keys: {list(event.keys())}"\n'
            '    assert "source_service" not in event\n'
            '\n'
            '\n'
            'def test_event_has_correlationId(producer):\n'
            '    """Event must use camelCase correlationId."""\n'
            f'    event = producer.create_event({{"test": "data"}})\n'
            '    assert "correlationId" in event, f"Missing correlationId, got keys: {list(event.keys())}"\n'
            '    assert "correlation_id" not in event\n'
            '\n'
            '\n'
            'def test_binary_attachment_is_base64(producer):\n'
            '    """Binary attachment must be base64-encoded."""\n'
            '    import base64\n'
            '    test_data = b"Hello, World!"\n'
            '    event = producer.create_event({"test": "data"}, binary_data=test_data)\n'
            '    assert "binaryAttachment" in event\n'
            '    # Verify it is valid base64\n'
            '    decoded = base64.b64decode(event["binaryAttachment"])\n'
            '    assert decoded == test_data\n'
            '\n'
            '\n'
            'def test_event_serializes_to_valid_json(producer):\n'
            '    """Serialized event must be valid JSON."""\n'
            f'    json_str = producer.publish({{"key": "value"}})\n'
            '    event = json.loads(json_str)\n'
            '    assert isinstance(event, dict)\n'
            '    required = {"eventId", "timestamp", "payload", "sourceService", "correlationId"}\n'
            '    assert required.issubset(set(event.keys())), \\\n'
            '        f"Missing required fields: {required - set(event.keys())}"\n'
        )

        # ── tests/EventConsumerTest.java ─────────────────────────────────
        files["tests/EventConsumerTest.java"] = (
            f'package {java_package};\n'
            '\n'
            'import org.json.JSONObject;\n'
            'import java.util.Base64;\n'
            '\n'
            '/**\n'
            ' * Unit tests for EventConsumer.\n'
            ' * These verify the consumer correctly parses schema-compliant events.\n'
            ' */\n'
            'public class EventConsumerTest {\n'
            '\n'
            '    public static void main(String[] args) {\n'
            '        testBasicConsume();\n'
            '        testBinaryAttachment();\n'
            '        System.out.println("All tests passed!");\n'
            '    }\n'
            '\n'
            '    static void testBasicConsume() {\n'
            '        JSONObject event = new JSONObject();\n'
            '        event.put("eventId", "test-uuid-123");\n'
            '        event.put("timestamp", 1705312200000L);\n'
            '        event.put("payload", new JSONObject().put("test", "data"));\n'
            f'        event.put("sourceService", "{svc_name}");\n'
            '        event.put("correlationId", "corr-uuid-456");\n'
            '\n'
            '        EventConsumer consumer = new EventConsumer();\n'
            '        consumer.consume(event.toString());\n'
            '\n'
            '        assert consumer.getEventId().equals("test-uuid-123") : "eventId mismatch";\n'
            '        assert consumer.getTimestamp() == 1705312200000L : "timestamp mismatch";\n'
            f'        assert consumer.getSourceService().equals("{svc_name}") : "sourceService mismatch";\n'
            '        assert consumer.getCorrelationId().equals("corr-uuid-456") : "correlationId mismatch";\n'
            '    }\n'
            '\n'
            '    static void testBinaryAttachment() {\n'
            '        byte[] original = "Hello, World!".getBytes();\n'
            '        String encoded = Base64.getEncoder().encodeToString(original);\n'
            '\n'
            '        JSONObject event = new JSONObject();\n'
            '        event.put("eventId", "test-uuid-789");\n'
            '        event.put("timestamp", 1705312200000L);\n'
            '        event.put("payload", new JSONObject().put("test", "data"));\n'
            f'        event.put("sourceService", "{svc_name}");\n'
            '        event.put("correlationId", "corr-uuid-012");\n'
            '        event.put("binaryAttachment", encoded);\n'
            '\n'
            '        EventConsumer consumer = new EventConsumer();\n'
            '        consumer.consume(event.toString());\n'
            '\n'
            '        byte[] decoded = consumer.getBinaryAttachment();\n'
            '        assert java.util.Arrays.equals(decoded, original) : \n'
            '            "Binary attachment decoded incorrectly — should use Base64, not hex";\n'
            '    }\n'
            '}\n'
        )

        files["producer/requirements.txt"] = "pytest\n"

        return files
