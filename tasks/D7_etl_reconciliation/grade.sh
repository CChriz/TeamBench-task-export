#!/usr/bin/env bash
# D7 grader: verify ETL transform fixes and data quality handling
set -euo pipefail

WORKSPACE="${1:-${WORKSPACE_DIR:-/workspace}}"
REPORTS="${2:-${REPORTS_DIR:-/reports}}"

cd "$WORKSPACE"

pass=true
partial=0
total=10
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
# C1: etl/transform.py is valid Python
# -------------------------------------------------------------------
if python3 -c "import ast; ast.parse(open('etl/transform.py').read())" 2>/dev/null; then
    check "C1" "etl/transform.py is valid Python" "pass"
else
    check "C1" "etl/transform.py missing or invalid" "fail"
fi

# -------------------------------------------------------------------
# C2: ETL pipeline runs without error
# -------------------------------------------------------------------
if python3 -c "
from etl.extract import extract
from etl.transform import load_exchange_rates, transform
records = extract('data/source.csv')
rates = load_exchange_rates('data/exchange_rates.csv')
" 2>/dev/null; then
    check "C2" "ETL pipeline runs without error" "pass"
else
    check "C2" "ETL pipeline crashes" "fail"
fi

# -------------------------------------------------------------------
# C3: Exchange rate uses correct column (rate_usd not rate_v1)
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('etl/transform.py').read()
# Should use rate_usd column, not rate_v1
if 'rate_v1' in src and 'rate_usd' not in src:
    sys.exit(1)
if 'rate_usd' in src:
    sys.exit(0)
# Also accept 'rate' as correct column name (varies by seed)
if 'inverse_rate' in src and 'rate' not in src.replace('inverse_rate','').replace('exchange_rate',''):
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C3" "Uses correct exchange rate column" "pass"
else
    check "C3" "Still uses wrong exchange rate column" "fail"
fi

# -------------------------------------------------------------------
# C4: Date filter is inclusive of last day (no off-by-one)
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('etl/transform.py').read()
# Bug was using < instead of <= for end date
# The fix should use <= or fix the comparison
if '<=' in src:
    sys.exit(0)
# Also check that the < date_end pattern is removed
import re
# Look for the buggy pattern: < date_end (without =)
if re.search(r'<\s*date_end', src) and not re.search(r'<=\s*date_end', src):
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C4" "Date filter inclusive of last day" "pass"
else
    check "C4" "Date filter has off-by-one error" "fail"
fi

# -------------------------------------------------------------------
# C5: Refunded orders excluded
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('etl/transform.py').read()
# Should filter or exclude refunded orders
if 'refund' in src.lower() and ('continue' in src or 'skip' in src.lower() or 'exclude' in src.lower() or '!=' in src):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C5" "Refunded orders excluded" "pass"
else
    check "C5" "Refunded orders still included" "fail"
fi

# -------------------------------------------------------------------
# C6: Negative quantities filtered out
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('etl/transform.py').read()
if 'quantity' in src.lower() and ('< 0' in src or '<= 0' in src or '> 0' in src or '>= 0' in src or 'negative' in src.lower()):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C6" "Negative quantities filtered" "pass"
else
    check "C6" "Negative quantities not handled" "fail"
fi

# -------------------------------------------------------------------
# C7: Future dates flagged (not filtered)
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('etl/transform.py').read()
if 'flag' in src.lower() and 'future' in src.lower():
    sys.exit(0)
if 'flagged' in src.lower() and ('future_date' in src.lower() or 'proc_date' in src.lower() or 'date_end' in src.lower()):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C7" "Future dates flagged" "pass"
else
    check "C7" "Future dates not flagged" "fail"
fi

# -------------------------------------------------------------------
# C8: Output matches expected (row count)
# -------------------------------------------------------------------
if python3 -c "
import csv, sys
with open('data/expected_output.csv') as f:
    expected = list(csv.DictReader(f))
# Run the ETL
try:
    from etl.extract import extract
    from etl.transform import load_exchange_rates, transform
    from etl.load import load
    records = extract('data/source.csv')
    rates = load_exchange_rates('data/exchange_rates.csv')
    # Try to call transform with various signatures
    import inspect
    sig = inspect.signature(transform)
    params = list(sig.parameters.keys())
    if len(params) >= 5:
        # Generator-style: transform(records, rates, date_start, date_end, proc_date)
        import json
        spec = open('RECONCILIATION_SPEC.md').read()
        # Extract proc_date from spec
        import re
        pd_match = re.search(r'\x60(\d{4}-\d{2}-\d{2})\x60', spec)
        proc_date = pd_match.group(1) if pd_match else '2025-01-31'
        # Determine date_start from spec or use month before
        parts = proc_date.split('-')
        y, m = int(parts[0]), int(parts[1])
        sm = m - 2
        sy = y
        if sm < 1:
            sm += 12
            sy -= 1
        date_start = f'{sy}-{sm:02d}-01'
        transformed = transform(records, rates, date_start, proc_date, proc_date)
    else:
        transformed = transform(records, rates)
    load(transformed, 'data/test_output.csv')
    with open('data/test_output.csv') as f:
        actual = list(csv.DictReader(f))
    if len(expected) != len(actual):
        print(f'Row count: expected {len(expected)}, got {len(actual)}', file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
    check "C8" "Output row count matches expected" "pass"
else
    check "C8" "Output row count does not match expected" "fail"
fi

# -------------------------------------------------------------------
# C9: RECONCILIATION_REPORT.md exists
# -------------------------------------------------------------------
if [ -f "RECONCILIATION_REPORT.md" ]; then
    check "C9" "RECONCILIATION_REPORT.md created" "pass"
else
    check "C9" "RECONCILIATION_REPORT.md not found" "fail"
fi

# -------------------------------------------------------------------
# C10: Source data not modified
# -------------------------------------------------------------------
if python3 -c "
import hashlib, sys, os
src = open('data/source.csv', 'rb').read()
expected = os.environ.get('SOURCE_CSV_HASH', '')
if expected and hashlib.sha256(src).hexdigest() != expected:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C10" "Source data not modified" "pass"
else
    check "C10" "Source data was modified" "fail"
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
