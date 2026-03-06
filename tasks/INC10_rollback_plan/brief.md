# INC10: Rollback Plan (Brief)

Three services failed after a coordinated deployment:
- `api_gateway` — entry-point service
- `user_service` — business logic service
- `auth_service` — data layer service

Review `deployment_log.json`, `service_deps.yaml`, and `rollback_procedures.md`
to understand what happened and how to roll back.

**Goal**: Produce `rollback_plan.json` that describes the rollback steps in the
correct order, includes health checks between steps, and captures both a
pre-rollback snapshot and a post-rollback verification step.

The Planner has the full incident report including dependency graph and required
rollback ordering. Coordinate with the Planner before writing the plan.
