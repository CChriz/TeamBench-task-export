# MULTI3: Polyglot Interface Bug Fix (Brief)

The Config Sync data pipeline is broken. The backend processor and
frontend handler disagree on the wire format, causing data to be lost or
corrupted at the interface boundary.

Fix the bugs so that `python3 tests/test_contract.py` passes all tests.

Files to investigate:
- `backend/processor.py` — Python data serializer
- `frontend/handler.py` — Python data consumer
- `shared/schema.json` — shared interface schema (may also be wrong)

Do NOT modify `tests/test_contract.py`.
