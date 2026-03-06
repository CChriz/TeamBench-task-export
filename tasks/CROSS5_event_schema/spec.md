# CROSS5: Event Schema Reconciliation

## Goal

A Python event producer and a Java event consumer are failing to communicate because of
field name mismatches and encoding inconsistencies. Fix both sides to agree on a common
event schema.

## Architecture

- **Python Producer** (`producer/event_producer.py`): Publishes events with snake_case fields
  and ISO-8601 timestamps
- **Java Consumer** (`consumer/src/main/java/EventConsumer.java`): Consumes events expecting
  camelCase fields and epoch millisecond timestamps
- **Event Schema** (`schema/event_schema.json`): The canonical schema definition (source of truth)

## Requirements

### Field Name Mismatches (fix 5)

The producer and consumer must agree on the field names defined in `event_schema.json`.
The schema is the source of truth. Fix whichever side is wrong for each field.

1. The event ID field: schema says `eventId`, producer sends `event_id`, consumer expects `eventId`
2. The timestamp field: schema says `timestamp`, producer sends `created_at`, consumer expects `timestamp`
3. The payload field: schema says `payload`, producer sends `data`, consumer expects `payload`
4. The source field: schema says `sourceService`, producer sends `source_service`, consumer expects `sourceService`
5. The correlation ID: schema says `correlationId`, producer sends `correlation_id`, consumer expects `correlationId`

### Encoding Bugs (fix 2)

6. **Timestamp encoding**: Producer sends ISO-8601 strings (`"2024-01-15T10:30:00Z"`).
   Consumer expects epoch milliseconds (`1705312200000`). The schema specifies epoch
   milliseconds. Fix the producer to send epoch milliseconds.

7. **Binary payload encoding**: Producer base64-encodes binary payloads. Consumer
   hex-decodes them. The schema specifies base64 encoding. Fix the consumer to
   base64-decode.

## Supporting Documents

- `schema/event_schema.json` — Canonical event schema (source of truth)
- `tests/test_roundtrip.py` — End-to-end serialization/deserialization tests
- `tests/EventConsumerTest.java` — Java consumer unit tests

## Important

- The schema is the source of truth for field names and encoding
- Some fixes go in the producer, some in the consumer — read the schema carefully
- Do NOT change `event_schema.json`
- All tests must pass after fixes
