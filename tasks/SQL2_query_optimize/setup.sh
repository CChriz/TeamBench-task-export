#!/usr/bin/env bash
# Setup for SQL2: Query Optimize
# Copies seed-generated workspace files into the agent workspace.
#
# Args: $1=WORKSPACE $2=REPORTS $3=RUN_ID
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"

mkdir -p "$WORKSPACE" "$REPORTS"

# Workspace files are written by the harness from the generator output.
# This script performs any additional environment preparation needed.

# Ensure Python 3 is available (sqlite3 is in stdlib)
python3 -c "import sqlite3; print('sqlite3 version:', sqlite3.sqlite_version)"

echo "SQL2_query_optimize workspace ready at $WORKSPACE"
