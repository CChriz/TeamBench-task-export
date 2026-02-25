# LH1: Long-Horizon Workflow with Failure Injection

## Goal
Execute a 15-step data processing pipeline. Two steps will fail on first attempt
and must be retried/recovered.

## Hard Requirements

1. Run `python workflow.py` which executes steps 1-15 sequentially.
2. The workflow reads `pipeline_config.json` for step definitions.
3. **Step 5** will fail on first attempt due to a transient error condition.
   - The error condition is indicated by a marker file written to the `intermediates/` directory.
   - Recovery requires clearing the error condition and re-running the step.
4. **Step 11** will fail on first attempt due to a transient error condition.
   - The error condition is indicated by a marker file written to the `intermediates/` directory.
   - Recovery requires clearing the error condition, ensuring the step's input is valid (derived from the previous step's output), and re-running the step.
5. Final output: `output/final_result.json` must contain:
   - `{"steps_completed": 15, "recovered_failures": 2, "checksum": "<sha256>"}`
6. The `checksum` is SHA-256 of concatenated step outputs.
7. A `output/workflow_log.jsonl` must record every step execution (pass/fail/retry).
8. Total step executions must be <= 19 (15 normal + 2 failures + 2 retries).

## Deliverables
- Fixed workflow producing correct `final_result.json` and `workflow_log.jsonl`.
- Verifier must confirm step count, recovery, and checksum.
