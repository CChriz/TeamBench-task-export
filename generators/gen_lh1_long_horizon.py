"""
Parameterized generator for LH1: Long-Horizon Workflow with Failure Injection.

Each seed produces:
- Different number of pipeline steps (10-15)
- Different step names drawn from a pool of realistic stage names
- Different failing step indices
- Different marker file names
- Different pipeline_config.json values (max_total_executions scales with step count)
- Different expected checksum
"""
from __future__ import annotations

import hashlib
import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Pool of realistic pipeline stage names
STAGE_NAME_POOL = [
    ("init", "create_workspace"),
    ("load_data", "load"),
    ("validate_schema", "validate"),
    ("normalize", "transform"),
    ("enrich", "transform"),
    ("filter", "transform"),
    ("deduplicate", "transform"),
    ("aggregate", "transform"),
    ("compute_stats", "analyze"),
    ("detect_anomalies", "analyze"),
    ("format_output", "transform"),
    ("generate_report", "report"),
    ("compress", "package"),
    ("encrypt", "package"),
    ("checksum", "verify"),
    ("sign", "verify"),
    ("archive", "store"),
    ("replicate", "store"),
    ("notify", "notify"),
    ("publish", "notify"),
    ("finalize", "finalize"),
    ("cleanup", "finalize"),
    ("audit_log", "audit"),
    ("index", "transform"),
    ("merge", "transform"),
]


class Generator(TaskGenerator):
    task_id = "LH1_long_horizon"
    domain = "operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Vary number of steps (10-15)
        num_steps = rng.randint(10, 15)

        # Pick distinct step entries from the pool
        pool_indices = rng.sample(list(range(len(STAGE_NAME_POOL))), num_steps)
        steps = []
        for step_num, pool_idx in enumerate(pool_indices, start=1):
            name, action = STAGE_NAME_POOL[pool_idx]
            steps.append({"id": step_num, "name": name, "action": action})

        # Pick 2 failing steps (not the first or last step)
        middle_ids = list(range(2, num_steps))  # excludes step 1 and last step
        failing_indices = rng.sample(middle_ids, 2)
        failing_indices.sort()
        fail_step_a, fail_step_b = failing_indices[0], failing_indices[1]

        # max_total_executions = num_steps + 2 failures + 2 retries
        max_execs = num_steps + 4

        # Compute expected checksum deterministically (same logic as workflow.py)
        all_outputs = []
        for step in steps:
            content = f"step_{step['id']}_{step['name']}_output_{step['action']}"
            all_outputs.append(content)
        combined = "".join(all_outputs)
        expected_checksum = hashlib.sha256(combined.encode()).hexdigest()

        expected = {
            "steps_completed": num_steps,
            "recovered_failures": 2,
            "checksum": expected_checksum,
            "failing_steps": [fail_step_a, fail_step_b],
            "max_total_executions": max_execs,
        }

        # Generate workspace files
        workflow_py = self._generate_workflow(fail_step_a, fail_step_b)
        config_json = json.dumps({
            "steps": steps,
            "max_total_executions": max_execs,
        }, indent=2)

        workspace_files = {
            "workflow.py": workflow_py,
            "pipeline_config.json": config_json,
        }

        spec_md = self._generate_spec(num_steps, fail_step_a, fail_step_b, max_execs)
        brief_md = self._generate_brief(num_steps)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_workflow(self, fail_step_a: int, fail_step_b: int) -> str:
        return f'''"""
Long-horizon workflow with failure injection.
Some steps may fail on first attempt; agent must detect and recover.
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_config():
    with open("pipeline_config.json", "r") as f:
        return json.load(f)


def append_log(log_path, entry):
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\\n")


# Steps that fail on first attempt — hidden in code logic
_FRAGILE_STEPS = {{{fail_step_a}, {fail_step_b}}}


def execute_step(step, intermediates_dir, attempt_tracker):
    step_id = step["id"]
    marker = os.path.join(intermediates_dir, f"step{{step_id}}_fail")
    output_file = os.path.join(intermediates_dir, f"step{{step_id}}_output.txt")

    # Failure injection: check internal counter file
    counter_file = os.path.join(intermediates_dir, f".step{{step_id}}_attempts")
    attempt_count = 0
    if os.path.exists(counter_file):
        attempt_count = int(open(counter_file).read().strip())
    attempt_count += 1
    with open(counter_file, "w") as f:
        f.write(str(attempt_count))

    if step_id in _FRAGILE_STEPS and attempt_count == 1:
        # Create failure marker
        with open(marker, "w") as f:
            f.write("FAILED")
        raise RuntimeError(f"Step {{step_id}} ({{step['name']}}) failed (transient error)")

    # Check if previous failure marker exists (agent must clean it up)
    if os.path.exists(marker):
        raise RuntimeError(f"Step {{step_id}}: failure marker exists. Remove {{marker}} to retry.")

    # Normal execution: produce output
    content = f"step_{{step_id}}_{{step['name']}}_output_{{step.get('action', 'default')}}"
    with open(output_file, "w") as f:
        f.write(content)

    return content


def main():
    config = load_config()
    steps = config["steps"]
    max_execs = config["max_total_executions"]

    os.makedirs("output", exist_ok=True)
    os.makedirs("intermediates", exist_ok=True)

    log_path = "output/workflow_log.jsonl"
    # Clear log
    open(log_path, "w").close()

    total_executions = 0
    recovered = 0
    all_outputs = []

    for step in steps:
        retries = 0
        while retries < 2:
            total_executions += 1
            if total_executions > max_execs:
                append_log(log_path, {{"step": step["id"], "status": "budget_exceeded", "ts": now_iso()}})
                print(f"ERROR: Exceeded max executions ({{max_execs}})")
                sys.exit(1)

            try:
                output = execute_step(step, "intermediates", set())
                all_outputs.append(output)
                append_log(log_path, {{"step": step["id"], "name": step["name"],
                                       "status": "pass", "attempt": retries + 1, "ts": now_iso()}})
                break
            except RuntimeError as e:
                append_log(log_path, {{"step": step["id"], "name": step["name"],
                                       "status": "fail", "error": str(e),
                                       "attempt": retries + 1, "ts": now_iso()}})
                # Attempt cleanup before retry
                cleanup_dir = os.path.join("intermediates", "temp")
                if os.path.exists(cleanup_dir):
                    shutil.rmtree(cleanup_dir)
                retries += 1
                if retries >= 2:
                    print(f"FATAL: Step {{step['id']}} failed after 2 attempts")
                    sys.exit(1)
                recovered += 1

    # Compute checksum
    combined = "".join(all_outputs)
    checksum = hashlib.sha256(combined.encode()).hexdigest()

    result = {{
        "steps_completed": len(all_outputs),
        "recovered_failures": recovered,
        "checksum": checksum,
    }}

    with open("output/final_result.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Workflow complete: {{json.dumps(result)}}")


if __name__ == "__main__":
    main()
'''

    def _generate_spec(
        self, num_steps: int, fail_a: int, fail_b: int, max_execs: int,
    ) -> str:
        return f"""# LH1: Long-Horizon Workflow with Failure Injection

## Goal
Execute a {num_steps}-step data processing pipeline. Two steps will fail on first attempt
and must be retried/recovered.

## Hard Requirements

1. Run `python workflow.py` which executes steps 1-{num_steps} sequentially.
2. The workflow reads `pipeline_config.json` for step definitions.
3. **Step {fail_a}** will fail on first attempt due to a transient error condition.
   - The error condition is indicated by a marker file written to the `intermediates/` directory.
   - Recovery requires clearing the error condition and re-running the step.
4. **Step {fail_b}** will fail on first attempt due to a transient error condition.
   - The error condition is indicated by a marker file written to the `intermediates/` directory.
   - Recovery requires clearing the error condition, ensuring the step's input is valid (derived from the previous step's output), and re-running the step.
5. Final output: `output/final_result.json` must contain:
   - `{{"steps_completed": {num_steps}, "recovered_failures": 2, "checksum": "<sha256>"}}`
6. The `checksum` is SHA-256 of concatenated step outputs.
7. A `output/workflow_log.jsonl` must record every step execution (pass/fail/retry).
8. Total step executions must be <= {max_execs} ({num_steps} normal + 2 failures + 2 retries).

## Deliverables
- Fixed workflow producing correct `final_result.json` and `workflow_log.jsonl`.
- Verifier must confirm step count, recovery, and checksum.
"""

    def _generate_brief(self, num_steps: int) -> str:
        return f"""# LH1: Long-Horizon Workflow (Brief)

Execute the {num_steps}-step pipeline. Some steps may fail; find and apply the correct recovery strategy.
Run: `python workflow.py`
Output goes to `output/final_result.json` and `output/workflow_log.jsonl`.
The Planner has details about which steps fail and how to recover.
"""
