## TeamBench Task Export

Export TeamBench tasks into a standalone, evaluation-ready format for custom agent frameworks.

This repository restructures TeamBench tasks into portable bundles that support both single-task execution and batch evaluation workflows.


[Task Export Doc TBU]

## Repository Structure

```text
.
├── task_team/          # Original TeamBench task exports
├── agent_modified/     # Example agent-modified workspaces
├── evals/              # Evaluation-ready task bundles
├── exported_tasks/
├── scripts/
│   ├── export_standalone_tasks.py
│   ├── evaluate_one.py
│   └── evaluate_all.py
└── README.md
```

### Export Standalone Tasks

export_standalone_tasks.py packages selected TeamBench tasks into self-contained bundles that can be passed directly to an agentic team.

Run it from the TeamBench repository root:

```text
python scripts/export_standalone_tasks.py \
  --tasks DIST1_queue_race GH10_retry_backoff D2_data_quality \
  --seeds 0 \
  --out exported_tasks
```

Each exported bundle is written as:
exported_tasks/<task_id>__seed_<seed>/

The script supports both generated and static tasks. For generated tasks, it calls the registered task generator and writes the generated workspace, spec.md, brief.md, and expected reports. For static tasks, it copies the existing workspace and runs setup.sh when present.

Each bundle includes:

TASK.md
workspace/
metadata.json
_eval/

TASK.md is the agent-facing task prompt. workspace/ is the editable working directory. _eval/ contains hidden grading assets such as grade.sh, task metadata, copied task files, submission/, and reports/.

After exporting, the script writes:

exported_tasks/export_manifest.json

The manifest records how many bundles were exported and the paths to each bundle.


### Evaluation Bundle Format

Each task under evals/ follows the same structure:

```text
evals/<task_id>/
├── task.yaml
├── brief.md
├── spec.md
├── grade.sh
├── task_dir/
│   ├── workspace/
│   ├── setup.sh                # Optional
│   ├── brief.md
│   ├── spec.md
│   ├── grade.sh
│   └── task.yaml
├── submission/
│   └── attestation.json
└── reports/
    ├── expected.json
    ├── score.json
    └── standalone_eval_record.json
```

### Reports

Evaluation outputs are written to the reports/ directory.

File	Description
score.json	Canonical evaluation result produced by the deterministic grader
expected.json	Reference outputs or expected evaluation artifacts
standalone_eval_record.json	Execution metadata, evaluation context, and standalone run details

The score.json file contains the final evaluation outcome, including:

* passed: true or false
* score: normalized score between 0.0 and 1.0


### Running Evaluations

#### Evaluate a Single Task

python scripts/evaluate_one.py \
  --task evals/CROSS1_api_contract_seed_0

#### Evaluate All Exported Tasks

python scripts/evaluate_all.py

Batch evaluation enables automated benchmarking across the full exported dataset.

Each exported task bundle (may) contain:

* Task specifications (spec.md)
* User-facing briefs (brief.md)
* Workspace files
* (Optional) Setup scripts
* Deterministic Grading scripts
* Submission templates
* Reference outputs
* Evaluation reports


Source

* Original benchmark: https://github.com/ybkim95/TeamBench
* TeamBench paper: https://arxiv.org/abs/2605.07073