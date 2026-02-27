# EA3: Type Safety (Brief)

The codebase has type errors. The Planner will run mypy to identify them.

Fix the type errors so that `mypy app/ --ignore-missing-imports --strict` reports 0 errors.

Some errors may require `# type: ignore` comments rather than code changes — the Planner's analysis will specify which.
