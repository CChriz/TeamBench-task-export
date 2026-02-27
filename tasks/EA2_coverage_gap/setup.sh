#!/usr/bin/env bash
set -euo pipefail
cd /workspace
pip install pytest pytest-cov coverage 2>/dev/null || true
