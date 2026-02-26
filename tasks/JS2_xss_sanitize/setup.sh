#!/usr/bin/env bash
# setup.sh — prepare workspace for JS2_xss_sanitize
# Args: WORKSPACE REPORTS RUN_ID
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"
RUN_ID="${3:-0}"

mkdir -p "$WORKSPACE/views"
mkdir -p "$WORKSPACE/tests"
mkdir -p "$REPORTS"

# Install Node.js dependencies if package.json present
if [ -f "$WORKSPACE/package.json" ]; then
  cd "$WORKSPACE"
  npm install --silent 2>/dev/null || true
fi
