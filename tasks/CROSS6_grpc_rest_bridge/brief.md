# CROSS6: gRPC-to-REST Bridge (Brief)

Fix 4 type conversion bugs in the REST gateway that translates gRPC-style
service responses into JSON for REST clients. The Planner has identified
each type mismatch between the gRPC internal format and the expected JSON output.

Follow the Planner's guidance precisely. Run `pytest tests/` to verify all conversions are correct.
