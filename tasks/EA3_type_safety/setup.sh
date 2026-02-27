#!/usr/bin/env bash
set -euo pipefail
cd /workspace
pip install mypy 2>/dev/null || true
