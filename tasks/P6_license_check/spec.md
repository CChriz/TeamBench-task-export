# P6: License Compatibility Check

## Goal
A Python project uses an MIT license but has dependencies with incompatible licenses.
Identify and replace the incompatible dependencies.

## Hard Requirements

1. **Project license**: The project is MIT-licensed (see `LICENSE` file).
2. **Dependency audit**: Review `requirements.txt` — it lists 5 dependencies with their license comments.
3. **Incompatible licenses**: 2 of the 5 dependencies use GPL-3.0, which is incompatible with MIT for distribution.
4. **Replace incompatible deps**: For each GPL dependency, replace it with the MIT/BSD-licensed alternative specified in `alternatives.md`.
5. **Update requirements.txt**: Replace the incompatible entries. Keep all other deps unchanged.

## Deliverables
- Updated `requirements.txt` with compatible replacements
- A `compliance_report.txt` listing: which deps were incompatible, why, and what they were replaced with
- Verifier confirms no GPL dependencies remain and report is accurate.
