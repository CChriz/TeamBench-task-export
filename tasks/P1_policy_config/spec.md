# P1: Policy-Driven Config Change

## Goal
Generate a configuration file (`output/config.json`) that complies with ALL rules
defined in the policy document.

## Hard Requirements

1. Produce `output/config.json` that satisfies every rule in `corpus/policy.txt`.
2. The config must be valid JSON with exact key names as specified in the policy.
3. The config must contain exactly the keys enumerated in the policy document — no more, no less.
4. Each key's value must satisfy the constraint specified for that key in the policy (exact values, permitted ranges, or allowed enumerations as appropriate).
5. The initial `config.json` template in the workspace has intentional policy violations that must be identified and corrected.

## Policy Source

Read `corpus/policy.txt` to obtain the authoritative rules. The Planner must derive the required values for each configuration key directly from that document.

## Deliverables
- Corrected `output/config.json` in workspace.
- Verifier must check each policy rule and produce attestation.
