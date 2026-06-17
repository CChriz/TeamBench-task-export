# P2_spec_arbitration

Seed: 0

# P2: Spec Arbitration (Conflicting Requirements)

## Goal
Resolve conflicting requirements using the priority rules defined in the corpus,
then produce a configuration that satisfies the highest-priority rules.

## Context
This deployment involves 8 configuration keys: `backup_enabled`, `backup_interval_hours`, `cache_ttl`, `compression`, `compression_enabled`, `log_retention_days`, `max_payload_mb`, `metrics_window_sec`.
The highest priority class is "security". Note that the field `compression` has
a documented exception in the priority rules that overrides normal resolution.

## Hard Requirements

1. Produce `output/resolved_config.json`.
2. Read the source documents in `corpus/` to identify all requirements and any conflicts between them.
3. Apply the priority rules from `corpus/priority_rules.txt` to resolve each conflict. Where two specs disagree on a value, the higher-priority spec's value wins.
4. Note that priority rules may have documented exceptions or special cases — these must be respected when resolving specific fields.
5. Non-conflicting values from any spec must be included as-is.
6. Output must have exactly 8 keys covering all fields from across the specs.

## Requirements Sources

Read the documents in `corpus/` to obtain all requirements and priority rules. The Planner must derive the resolved values for each key by applying the priority rules to the conflicting specs — the resolution must not be assumed.

## Deliverables
- `output/resolved_config.json` in workspace.
- Verifier must confirm each resolved value traces to the correct priority rule and produce attestation.

