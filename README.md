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
├── scripts/
│   ├── evaluate_one.py
│   └── evaluate_all.py
└── README.md
```

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