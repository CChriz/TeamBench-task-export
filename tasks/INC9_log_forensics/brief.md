# INC9: Log Forensics (Brief)

Three services experienced a cascading failure. Analyse the logs to find the root cause.

**Logs available**:
- `api_gateway.log` — entry-point service
- `user_service.log` — business logic service
- `db_proxy.log` — data proxy service

**Supporting files**:
- `topology.yaml` — service topology
- `known_scheduled_jobs.json` — scheduled batch job registry
- `ntp_status.txt` — NTP clock synchronisation status
- `alert_history.json` — alert timeline

**Goal**: Produce `root_cause_report.json` identifying the root cause service,
cause type, a timeline of events, and all affected services.

The Planner has the full incident analysis including identification of red
herrings. Coordinate with the Planner before writing your report.
