#!/usr/bin/env bash
# Analyze cross-model ablation results once all runs complete.
# Usage: bash scripts/analyze_crossmodel.sh
set -euo pipefail

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "=== Cross-Model Analysis ==="
echo "Checking result files..."

FILES=""
for f in shared/ablation_results/crossmodel_*.json; do
    if [ -f "$f" ]; then
        scored=$(python3 -c "import json; d=json.load(open('$f')); runs=d.get('runs',[]); print(sum(1 for r in runs if r.get('score') is not None))")
        total=$(python3 -c "import json; d=json.load(open('$f')); runs=d.get('runs',[]); print(len(runs))")
        errors=$(python3 -c "import json; d=json.load(open('$f')); runs=d.get('runs',[]); print(sum(1 for r in runs if r.get('error')))")
        echo "  $(basename $f): $scored/$total scored, $errors errors"
        if [ "$errors" -eq 0 ] && [ "$scored" -gt 0 ]; then
            FILES="$FILES $f"
        fi
    fi
done

if [ -z "$FILES" ]; then
    echo "No valid result files found yet. Wait for runs to complete."
    exit 1
fi

echo ""
echo "Running cross-model analysis on:$FILES"
python3 scripts/cross_model_analysis.py --files $FILES --output-dir shared/paper

echo ""
echo "Regenerating paper tables..."
bash scripts/generate_paper.sh

echo ""
echo "=== Done ==="
echo "Outputs in shared/paper/"
