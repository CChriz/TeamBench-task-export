# S2: Dependency Conflict Trap

## Goal
Fix the Python project so that `make test` passes.

## Hard Requirements

1. The project has a `Makefile` with a `test` target that runs `python -m pytest tests/ -q`.
2. The project depends on two libraries (provided as local packages in `vendor/`):
   - `libfoo==1.2.0` requires `utils>=2.0,<3.0`
   - `libbar==0.9.1` requires `utils>=1.0,<2.0`
3. The version conflict must be resolved such that both `libfoo` and `libbar` function correctly at runtime. Simply pinning `utils` to the version range demanded by one library will break the other — the resolution requires both a version pin and a compatibility adjustment.
4. `requirements.txt` must list exact pinned versions.
5. No additional packages may be introduced.
6. All 4 test cases in `tests/test_integration.py` must pass.

## Deliverables
- Fixed code + `requirements.txt` in workspace.
- Verifier must confirm all constraints and produce attestation.
