#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"
RUN_ID="${3:-}"
mkdir -p "$REPORTS"
# Setup handled by parameterized generator
exit 0
