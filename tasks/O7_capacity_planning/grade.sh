#!/usr/bin/env bash
# O7 grader: verify service performance fixes meet SLA
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
# C1: service_a.py is valid Python
# -------------------------------------------------------------------
if python3 -c "import ast; ast.parse(open('service_a.py').read())" 2>/dev/null; then
    check "C1" "service_a.py is valid Python" "pass"
else
    check "C1" "service_a.py missing or invalid" "fail"
fi

# -------------------------------------------------------------------
# C2: service_a.py eliminates N+1 query (uses batch/join, not loop)
# -------------------------------------------------------------------
if python3 -c "
import ast, sys
src = open('service_a.py').read()
tree = ast.parse(src)
# Look for loop-based query pattern (N+1 indicator)
for node in ast.walk(tree):
    if isinstance(node, ast.For):
        for_src = ast.unparse(node)
        # If there is a query/fetch call inside a for loop, it is N+1
        if 'query(' in for_src or 'fetch(' in for_src or 'execute(' in for_src or 'get_item(' in for_src:
            sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C2" "service_a.py no longer has N+1 query in loop" "pass"
else
    check "C2" "service_a.py still has N+1 query pattern" "fail"
fi

# -------------------------------------------------------------------
# C3: service_a.py uses batch query (IN clause or JOIN)
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('service_a.py').read()
if 'batch' in src.lower() or 'IN (' in src or 'in (' in src or 'JOIN' in src.upper() or 'join' in src or 'bulk' in src.lower() or 'WHERE' in src and ('IN' in src or 'ids' in src):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C3" "service_a.py uses batch/bulk query" "pass"
else
    check "C3" "service_a.py missing batch query pattern" "fail"
fi

# -------------------------------------------------------------------
# C4: service_b.py is valid Python
# -------------------------------------------------------------------
if python3 -c "import ast; ast.parse(open('service_b.py').read())" 2>/dev/null; then
    check "C4" "service_b.py is valid Python" "pass"
else
    check "C4" "service_b.py missing or invalid" "fail"
fi

# -------------------------------------------------------------------
# C5: service_b.py has bounded cache (maxsize, max_size, or LRU)
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('service_b.py').read()
if 'maxsize' in src or 'max_size' in src or 'lru_cache' in src or 'OrderedDict' in src or 'maxlen' in src or 'TTLCache' in src or 'cachetools' in src or 'capacity' in src:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C5" "service_b.py cache is bounded" "pass"
else
    check "C5" "service_b.py cache still unbounded" "fail"
fi

# -------------------------------------------------------------------
# C6: service_b.py evicts old entries
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('service_b.py').read()
if 'pop' in src or 'del ' in src or 'evict' in src or 'lru_cache' in src or 'popitem' in src or 'remove' in src or 'discard' in src or 'TTLCache' in src:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C6" "service_b.py implements eviction" "pass"
else
    check "C6" "service_b.py no eviction logic" "fail"
fi

# -------------------------------------------------------------------
# C7: service_c.py is valid Python
# -------------------------------------------------------------------
if python3 -c "import ast; ast.parse(open('service_c.py').read())" 2>/dev/null; then
    check "C7" "service_c.py is valid Python" "pass"
else
    check "C7" "service_c.py missing or invalid" "fail"
fi

# -------------------------------------------------------------------
# C8: service_c.py uses async/non-blocking pattern
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('service_c.py').read()
if 'async' in src or 'await' in src or 'threading' in src or 'concurrent' in src or 'asyncio' in src or 'ThreadPool' in src or 'run_in_executor' in src or 'gather' in src:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C8" "service_c.py uses async/non-blocking pattern" "pass"
else
    check "C8" "service_c.py still uses synchronous blocking call" "fail"
fi

# -------------------------------------------------------------------
# C9: benchmark passes SLA
# -------------------------------------------------------------------
if python3 run_benchmark.py 2>/dev/null; then
    check "C9" "Benchmark passes SLA constraints" "pass"
else
    check "C9" "Benchmark SLA violation" "fail"
fi

# -------------------------------------------------------------------
# C10: No functionality removed (all public functions still exist)
# -------------------------------------------------------------------
if python3 -c "
import ast, sys
for fname in ['service_a.py', 'service_b.py', 'service_c.py']:
    src = open(fname).read()
    tree = ast.parse(src)
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    # Each service must have at least 2 functions (handler + helper)
    if len(funcs) < 2:
        print(f'{fname} has only {len(funcs)} functions', file=sys.stderr)
        sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C10" "All service functions preserved" "pass"
else
    check "C10" "Service functions removed" "fail"
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
