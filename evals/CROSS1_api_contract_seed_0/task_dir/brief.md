# CROSS1: API Contract Fix (Brief)

Fix the Python client to correctly communicate with the Go HTTP server.
The Planner has read both codebases and identified 3 contract mismatches.

Fix only the Python client files and api_spec.yaml.
Do NOT modify the Go server.

Run `pytest tests/` to verify. The grader also checks `go build ./...`.
