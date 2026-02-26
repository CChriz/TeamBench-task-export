#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"
RUN_ID="$3"
SEED="${4:-0}"
mkdir -p "$REPORTS"
echo "GO2_race_condition setup complete (seed=$SEED)"
