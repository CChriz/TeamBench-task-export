#!/usr/bin/env bash
# EA1 setup: install dependencies
set -euo pipefail

cd /workspace

# Install app dependencies
pip install flask defusedxml 2>/dev/null || true

# Install test dependencies
pip install pytest 2>/dev/null || true
