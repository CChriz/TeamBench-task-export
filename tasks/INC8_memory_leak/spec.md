# INC8: Memory Leak Triage

## Goal
Investigate memory growth across 3 components. Identify and fix only the real
production memory leak. Leave expected behavior and test-only artifacts alone.

## Requirements
1. Fix the REAL memory leak in the event processor (unbounded list growth)
2. Do NOT modify the cache manager — its growth is documented and expected
3. Do NOT fix the test helper — its accumulation only affects test runs, not production
4. The event processor must use a bounded data structure (e.g., deque with maxlen)
5. Write `INCIDENT_REPORT.md` classifying each component's memory behavior
6. All existing tests must continue to pass

## Supporting Documents
- `event_processor.py` — REAL LEAK: stores all processed events in ever-growing list
- `cache_manager.py` — EXPECTED: LRU cache grows until max_size (documented behavior)
- `test_helper.py` — TEST ARTIFACT: accumulates mock objects at module level
- `INCIDENT_TICKET.md` — OOM kill incident report with timeline
- `ARCHITECTURE.md` — Documents the cache manager design choice and memory budget
- `metrics.json` — Memory growth data for all 3 components
- `tests/test_components.py` — Tests for all 3 components

## Adversarial Element
Two of the three components showing memory growth are NOT bugs. The cache is
working as designed (see ARCHITECTURE.md). The test helper only runs in CI.
Only one component has a genuine production memory leak.

## Important
Only fix `event_processor.py`. Create `INCIDENT_REPORT.md` with your triage findings.
