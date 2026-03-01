#!/usr/bin/env bash
# Re-run gemini-3-pro-preview expertise_oracle and expertise_no_analysis conditions
# (all 60 runs failed with 503 in the original run)
set -euo pipefail

cd "$(dirname "$0")/.."
source venv/bin/activate
set -a; source .env; set +a

MODEL="gemini-3-pro-preview"
TASKS="EA1_security_scan EA2_coverage_gap EA3_type_safety EA4_code_quality EA5_dependency_audit"
SEEDS="0 1 2 3 4 5"
RETRY_OUT="shared/ea_results/gemini-3-pro-preview-retry.json"
BASE_OUT="shared/ea_results/gemini-3-pro-preview.json"

echo "Re-running oracle + no_analysis conditions for ${MODEL}..."
python -m harness.ablation \
    --model "$MODEL" \
    --tasks $TASKS \
    --seeds $SEEDS \
    --conditions expertise_oracle expertise_no_analysis \
    --output "$RETRY_OUT" \
    2>&1 | tee shared/ea_results/gemini-3-pro-preview-retry.log

echo ""
echo "Merging retry results into base file..."
python scripts/retry_503_runs.py "$BASE_OUT" "$RETRY_OUT"

echo "Done. Final results in $BASE_OUT"
