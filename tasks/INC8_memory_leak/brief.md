# INC8: Memory Leak Triage (Brief)

Investigate memory growth in 3 components. Only 1 is a real production leak — fix it.
The cache manager growth is expected (see ARCHITECTURE.md). The test helper is test-only.

Fix only `event_processor.py` (use bounded data structure). Write `INCIDENT_REPORT.md`.
