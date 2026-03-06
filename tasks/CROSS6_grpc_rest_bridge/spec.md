# CROSS6: gRPC-to-REST Bridge — Type Conversion Fixes

## Goal
Fix 4 type conversion bugs in the REST gateway that translates gRPC-style service
definitions into HTTP REST API calls. The gateway incorrectly handles type conversions
between the gRPC internal representation and the REST/JSON external format.

## Requirements
1. **int64 as string**: gRPC int64 fields must be serialized as JSON strings (not numbers) to prevent JavaScript precision loss for values > 2^53. The gateway currently passes them as bare integers.
2. **repeated fields as arrays**: gRPC repeated fields must always be wrapped in a JSON array, even when there is only one element. The gateway currently returns a bare object when there is exactly one element.
3. **enum as string name**: gRPC enum fields must be serialized as their string name (e.g., `"ACTIVE"`) in REST JSON responses, not as integer values. The gateway currently sends raw integers.
4. **timestamp as ISO 8601**: gRPC Timestamp fields (epoch seconds) must be converted to ISO 8601 strings (e.g., `"2023-11-14T22:13:20Z"`) in REST responses. The gateway currently passes raw epoch integers.
5. All existing tests in `tests/` must pass after fixes.

## Supporting Documents
- `service.proto` — gRPC-style service definition with 4 RPC methods
- `gateway.py` — REST-to-gRPC bridge (contains all 4 bugs)
- `service_impl.py` — Internal service implementation returning gRPC-style responses
- `models.py` — Data models shared between service and gateway
- `tests/test_gateway.py` — Tests validating correct REST JSON output

## Background

### gRPC-JSON Transcoding Rules

When exposing a gRPC service via REST/JSON, specific type conversions are required
per the [Proto3 JSON Mapping](https://protobuf.dev/programming-guides/proto3/#json):

| Proto3 Type | JSON Representation | Common Bug |
|-------------|---------------------|------------|
| int64/uint64 | string (`"12345"`) | Passed as number, loses precision |
| repeated T | array (`[...]`) | Single-element not wrapped |
| enum | string name (`"FOO"`) | Passed as integer code |
| Timestamp | ISO 8601 string | Passed as epoch seconds |

### Why This Matters

These are the 4 most common bugs in real-world gRPC-JSON transcoding gateways
(grpc-gateway, Envoy transcoder, Google Cloud Endpoints). Each one causes subtle
client-side failures:
- **int64 as number**: JavaScript `JSON.parse` silently truncates values > 2^53
- **single-element repeated**: Clients expecting arrays break on bare objects
- **enum as int**: Clients using string comparison fail; forward compatibility breaks
- **timestamp as epoch**: ISO 8601 is the canonical JSON timestamp format; epoch integers
  are ambiguous (seconds vs milliseconds) and not human-readable

## Hidden Complexity
- The gateway uses a generic `_convert_field()` method that handles all types.
  Each bug is a different branch in this method.
- The `repeated` field bug only manifests when there is exactly 1 element;
  lists with 0 or 2+ elements work correctly.
- The enum conversion must use the enum's `.name` attribute, not `.value`.
- Timestamps must be UTC (suffix `Z`), not local time.
