# O7: Service Capacity Planning

## Goal
Fix performance issues in 3 services to bring them within SLA constraints.

## Requirements
1. Fix `service_a.py`: eliminate N+1 query pattern causing latency spikes
2. Fix `service_b.py`: bound the in-memory cache to prevent OOM
3. Fix `service_c.py`: make the synchronous external API call non-blocking
4. All services must meet SLA: p99 latency < 100ms, error rate < 0.1%
5. Do NOT remove functionality — optimize, do not delete features
6. Run `python run_benchmark.py` to verify SLA compliance

## Supporting Documents
- `service_a.py` — Service with N+1 query bug (fetches related items in a loop)
- `service_b.py` — Service with unbounded cache (grows until OOM)
- `service_c.py` — Service with blocking external API call
- `load_test_results.json` — Current load testing metrics showing SLA violations
- `SLA.md` — SLA definitions (p99 < 100ms, error rate < 0.1%, memory < 512MB)
- `CAPACITY_REPORT.md` — Current metrics showing violations per service
- `run_benchmark.py` — Benchmark runner that validates SLA compliance

## Performance Patterns
Each service has a well-known performance anti-pattern. The fix must address
the root cause, not just the symptoms.

## Important
Do NOT modify `SLA.md`, `run_benchmark.py`, or `load_test_results.json`.
Only fix the service files.
