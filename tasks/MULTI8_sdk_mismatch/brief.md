# MULTI8: SDK Mismatch (Brief)

Fix 4 field mismatches in `sdk_client.py` so it matches the current `api_spec.yaml`.

The SDK was generated from an older API spec. Field names and response shapes have changed.

Run `python3 test_sdk.py` to verify all fixes. Only modify `sdk_client.py`.
