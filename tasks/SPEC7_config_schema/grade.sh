#!/usr/bin/env bash
# SPEC7 grader: verify config validator implementation
set -euo pipefail

WORKSPACE="${1:-${WORKSPACE_DIR:-/workspace}}"
REPORTS="${2:-${REPORTS_DIR:-/reports}}"

cd "$WORKSPACE"

pass=true
partial=0
total=12
findings=""

check() {
    local id="$1"
    local desc="$2"
    local result="$3"
    if [ "$result" = "pass" ]; then
        partial=$((partial + 1))
        findings="${findings}{\"id\":\"${id}\",\"ok\":true,\"note\":\"${desc}\"},"
    else
        pass=false
        findings="${findings}{\"id\":\"${id}\",\"ok\":false,\"note\":\"${desc}\"},"
    fi
}

# -------------------------------------------------------------------
# C1: validator.py exists and is valid Python
# -------------------------------------------------------------------
if python3 -c "import ast; ast.parse(open('validator.py').read())" 2>/dev/null; then
    check "C1" "validator.py is valid Python" "pass"
else
    check "C1" "validator.py missing or invalid" "fail"
fi

# -------------------------------------------------------------------
# C2: validator.py has validate_config function
# -------------------------------------------------------------------
if python3 -c "from validator import validate_config" 2>/dev/null; then
    check "C2" "validate_config function importable" "pass"
else
    check "C2" "validate_config function not found" "fail"
fi

# -------------------------------------------------------------------
# C3: Valid config returns no errors
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
errors = validate_config(config)
sys.exit(0 if len(errors) == 0 else 1)
" 2>/dev/null; then
    check "C3" "Valid config returns no errors" "pass"
else
    check "C3" "Valid config incorrectly flagged" "fail"
fi

# -------------------------------------------------------------------
# C4: Invalid config returns errors
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/invalid.json'))
errors = validate_config(config)
sys.exit(0 if len(errors) > 0 else 1)
" 2>/dev/null; then
    check "C4" "Invalid config returns errors" "pass"
else
    check "C4" "Invalid config not caught" "fail"
fi

# -------------------------------------------------------------------
# C5: Type validation works (string where int expected)
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
# Corrupt a numeric field to string
for k, v in config.items():
    if isinstance(v, int):
        config[k] = 'not_a_number'
        break
errors = validate_config(config)
sys.exit(0 if any('type' in str(e).lower() or 'int' in str(e).lower() or 'number' in str(e).lower() for e in errors) else 1)
" 2>/dev/null; then
    check "C5" "Type validation catches wrong types" "pass"
else
    check "C5" "Type validation not working" "fail"
fi

# -------------------------------------------------------------------
# C6: Range validation works (value out of bounds)
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
schema = json.load(open('config_schema.json'))
# Find a field with minimum/maximum and set it out of range
props = schema.get('properties', {})
for k, v in props.items():
    if 'minimum' in v and k in config:
        config[k] = v['minimum'] - 100
        break
errors = validate_config(config)
sys.exit(0 if len(errors) > 0 else 1)
" 2>/dev/null; then
    check "C6" "Range validation catches out-of-bounds values" "pass"
else
    check "C6" "Range validation not working" "fail"
fi

# -------------------------------------------------------------------
# C7: Enum validation works
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
schema = json.load(open('config_schema.json'))
props = schema.get('properties', {})
for k, v in props.items():
    if 'enum' in v and k in config:
        config[k] = 'INVALID_ENUM_VALUE_XYZ'
        break
errors = validate_config(config)
sys.exit(0 if len(errors) > 0 else 1)
" 2>/dev/null; then
    check "C7" "Enum validation catches invalid values" "pass"
else
    check "C7" "Enum validation not working" "fail"
fi

# -------------------------------------------------------------------
# C8: Cross-field constraint 1 (mode=cluster -> replicas >= 3)
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
config['mode'] = 'cluster'
config['replicas'] = 1
errors = validate_config(config)
sys.exit(0 if len(errors) > 0 else 1)
" 2>/dev/null; then
    check "C8" "Cross-field: cluster mode requires replicas >= 3" "pass"
else
    check "C8" "Cross-field: cluster/replicas constraint not enforced" "fail"
fi

# -------------------------------------------------------------------
# C9: Cross-field constraint 2 (ssl=true -> cert_path required)
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
config['ssl_enabled'] = True
config.pop('cert_path', None)
errors = validate_config(config)
sys.exit(0 if len(errors) > 0 else 1)
" 2>/dev/null; then
    check "C9" "Cross-field: ssl requires cert_path" "pass"
else
    check "C9" "Cross-field: ssl/cert_path constraint not enforced" "fail"
fi

# -------------------------------------------------------------------
# C10: Missing required field detected
# -------------------------------------------------------------------
if python3 -c "
import json, sys
from validator import validate_config
config = json.load(open('sample_configs/valid.json'))
schema = json.load(open('config_schema.json'))
required = schema.get('required', [])
if required:
    config.pop(required[0], None)
errors = validate_config(config)
sys.exit(0 if len(errors) > 0 else 1)
" 2>/dev/null; then
    check "C10" "Missing required field detected" "pass"
else
    check "C10" "Missing required field not caught" "fail"
fi

# -------------------------------------------------------------------
# C11: pytest tests pass
# -------------------------------------------------------------------
if python3 -m pytest tests/ -q --tb=no 2>/dev/null | grep -q "passed"; then
    check "C11" "pytest tests pass" "pass"
else
    check "C11" "pytest tests fail" "fail"
fi

# -------------------------------------------------------------------
# C12: config_schema.json not modified
# -------------------------------------------------------------------
if python3 -c "
import hashlib, sys, os
src = open('config_schema.json', 'rb').read()
expected = os.environ.get('SCHEMA_HASH', '')
if expected and hashlib.sha256(src).hexdigest() != expected:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C12" "config_schema.json not modified" "pass"
else
    check "C12" "config_schema.json was modified" "fail"
fi

partial_score=$(awk "BEGIN {printf \"%.4f\", $partial / $total}")
findings="${findings%,}"

mkdir -p "${REPORTS}"
cat > "${REPORTS}/score.json" <<EOF
{
  "pass": $( [ "$pass" = "true" ] && echo "true" || echo "false" ),
  "secondary": {
    "partial_score": $partial_score,
    "checks_passed": $partial,
    "total_checks": $total
  },
  "failure_modes": [],
  "checklist": [$findings]
}
EOF
