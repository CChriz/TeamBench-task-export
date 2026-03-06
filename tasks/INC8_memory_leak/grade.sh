#!/usr/bin/env bash
# INC8 grader: verify memory leak triage — only real leak fixed, others untouched
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
# C1: event_processor.py is valid Python
# -------------------------------------------------------------------
if python3 -c "import ast; ast.parse(open('event_processor.py').read())" 2>/dev/null; then
    check "C1" "event_processor.py is valid Python" "pass"
else
    check "C1" "event_processor.py missing or invalid" "fail"
fi

# -------------------------------------------------------------------
# C2: event_processor.py uses bounded data structure (deque with maxlen)
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('event_processor.py').read()
if 'deque' in src and 'maxlen' in src:
    sys.exit(0)
if 'maxlen' in src or 'max_size' in src or 'bounded' in src:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C2" "event_processor.py uses bounded data structure" "pass"
else
    check "C2" "event_processor.py still uses unbounded list" "fail"
fi

# -------------------------------------------------------------------
# C3: event_processor.py no longer has unbounded append-only list
# -------------------------------------------------------------------
if python3 -c "
import ast, sys
src = open('event_processor.py').read()
tree = ast.parse(src)
# Check for the pattern: self.events = [] and self.events.append()
# with no trimming/maxlen
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr in ('events', 'processed_events', 'event_history'):
                if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                    # Found bare list init — this is the bug
                    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C3" "event_processor.py no unbounded list initialization" "pass"
else
    check "C3" "event_processor.py still initializes unbounded list" "fail"
fi

# -------------------------------------------------------------------
# C4: cache_manager.py NOT modified (expected behavior)
# -------------------------------------------------------------------
if python3 -c "
import hashlib, sys, os
src = open('cache_manager.py', 'rb').read()
expected = os.environ.get('CACHE_MANAGER_HASH', '')
if expected and hashlib.sha256(src).hexdigest() != expected:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C4" "cache_manager.py not modified (correct — expected growth)" "pass"
else
    check "C4" "cache_manager.py was modified (should not be)" "fail"
fi

# -------------------------------------------------------------------
# C5: test_helper.py NOT modified (test-only artifact)
# -------------------------------------------------------------------
if python3 -c "
import hashlib, sys, os
src = open('test_helper.py', 'rb').read()
expected = os.environ.get('TEST_HELPER_HASH', '')
if expected and hashlib.sha256(src).hexdigest() != expected:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C5" "test_helper.py not modified (correct — test-only artifact)" "pass"
else
    check "C5" "test_helper.py was modified (should not be)" "fail"
fi

# -------------------------------------------------------------------
# C6: INCIDENT_REPORT.md exists
# -------------------------------------------------------------------
if [ -f "INCIDENT_REPORT.md" ]; then
    check "C6" "INCIDENT_REPORT.md created" "pass"
else
    check "C6" "INCIDENT_REPORT.md not found" "fail"
fi

# -------------------------------------------------------------------
# C7: INCIDENT_REPORT.md classifies event_processor as real leak
# -------------------------------------------------------------------
if python3 -c "
import sys
content = open('INCIDENT_REPORT.md').read().lower()
if ('event_processor' in content or 'event processor' in content) and ('leak' in content or 'unbounded' in content or 'fix' in content):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C7" "Report identifies event_processor as real leak" "pass"
else
    check "C7" "Report does not identify event_processor as leak" "fail"
fi

# -------------------------------------------------------------------
# C8: INCIDENT_REPORT.md classifies cache_manager as expected
# -------------------------------------------------------------------
if python3 -c "
import sys
content = open('INCIDENT_REPORT.md').read().lower()
if ('cache_manager' in content or 'cache manager' in content) and ('expected' in content or 'design' in content or 'intentional' in content or 'not a leak' in content or 'by design' in content):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C8" "Report classifies cache_manager as expected behavior" "pass"
else
    check "C8" "Report does not classify cache_manager correctly" "fail"
fi

# -------------------------------------------------------------------
# C9: INCIDENT_REPORT.md classifies test_helper as test-only
# -------------------------------------------------------------------
if python3 -c "
import sys
content = open('INCIDENT_REPORT.md').read().lower()
if ('test_helper' in content or 'test helper' in content) and ('test' in content and ('artifact' in content or 'only' in content or 'not production' in content or 'ci' in content)):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    check "C9" "Report classifies test_helper as test-only artifact" "pass"
else
    check "C9" "Report does not classify test_helper correctly" "fail"
fi

# -------------------------------------------------------------------
# C10: Tests still pass
# -------------------------------------------------------------------
if python3 -m pytest tests/ -q --tb=no 2>/dev/null | grep -q "passed"; then
    check "C10" "All tests pass" "pass"
else
    check "C10" "Tests fail" "fail"
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
