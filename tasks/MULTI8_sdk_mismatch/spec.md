# MULTI8: SDK Mismatch — Full Specification (Planner Only)

## Overview

A Python SDK client was generated from an OpenAPI spec, but the spec has since been updated. The SDK client has **4 field mismatches** between what it sends/expects and what the actual API requires. Fix the SDK client to match the current API spec.

---

## Application Architecture

```
workspace/
  sdk_client.py        # Auto-generated SDK client (buggy — out of date)
  api_spec.yaml        # Current OpenAPI spec (source of truth)
  mock_server.py       # Mock server implementing current spec
  test_sdk.py          # Test suite (do not modify)
```

The `api_spec.yaml` is the source of truth. The `sdk_client.py` was generated from an older version of the spec and has stale field names and response shapes.

---

## Bug Inventory

### Bug 1: User creation sends wrong field name
- **Symptom**: SDK sends `username` but the current API expects `user_name`
- **Expected**: Update `create_user()` to send the field name from the current spec

### Bug 2: List response parses wrong wrapper key
- **Symptom**: SDK expects response `{"items": [...]}` but API now returns `{"results": [...]}`
- **Expected**: Update `list_users()` to read from the correct key

### Bug 3: Error response reads wrong field
- **Symptom**: SDK reads `error.message` but API now returns `error.detail`
- **Expected**: Update error handling to read the correct field

### Bug 4: Pagination parameter renamed
- **Symptom**: SDK sends `page_size` query parameter but API now expects `limit`
- **Expected**: Update `list_users()` to use the correct parameter name

---

## Expected Outcome

After all 4 fixes: `python3 test_sdk.py` passes all 8 tests.

---

## Constraints

- Do not modify `test_sdk.py`, `mock_server.py`, or `api_spec.yaml`
- The `api_spec.yaml` is always the source of truth
- Only fix `sdk_client.py`
