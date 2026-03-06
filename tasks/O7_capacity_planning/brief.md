# O7: Service Capacity Planning (Brief)

Fix performance issues in 3 services: N+1 queries, unbounded cache, and blocking API call.

All services must meet SLA: p99 < 100ms, error rate < 0.1%, memory < 512MB.

Only fix `service_a.py`, `service_b.py`, `service_c.py`. Run `python run_benchmark.py` to verify.
