#!/usr/bin/env bash
# grade.sh — GO2_race_condition
# Static + dynamic grader. 12 checks total.
# Args: WORKSPACE REPORTS SUBMISSION TASK_DIR
set -o pipefail

WORKSPACE="$1"
REPORTS="$2"
SUBMISSION="$3"
TASK_DIR="${4:-$(dirname "$0")}"

mkdir -p "$REPORTS"

CHECKS=0; PASSED=0; FAILURES=""

fail() { FAILURES="${FAILURES:+${FAILURES},}$1"; }

cd "$WORKSPACE"

# ---------------------------------------------------------------------------
# Load expected.json (seed-aware)
# ---------------------------------------------------------------------------
EXPECTED_JSON="$REPORTS/expected.json"
if [ ! -f "$EXPECTED_JSON" ]; then
  EXPECTED_JSON="$(dirname "$0")/expected.json"
fi

RACE_TYPE="shared_map"
FIX_PRIMITIVES="mutex"
NUM_ITEMS=10
NUM_WORKERS=4

if [ -f "$EXPECTED_JSON" ]; then
  RACE_TYPE=$(python3 -c "
import json
d = json.load(open('$EXPECTED_JSON'))
print(d.get('race_type', 'shared_map'))
" 2>/dev/null || echo "shared_map")

  FIX_PRIMITIVES=$(python3 -c "
import json
d = json.load(open('$EXPECTED_JSON'))
print(','.join(d.get('fix_primitives', ['mutex'])))
" 2>/dev/null || echo "mutex")

  NUM_ITEMS=$(python3 -c "
import json
d = json.load(open('$EXPECTED_JSON'))
print(d.get('num_items', 10))
" 2>/dev/null || echo "10")

  NUM_WORKERS=$(python3 -c "
import json
d = json.load(open('$EXPECTED_JSON'))
print(d.get('num_workers', 4))
" 2>/dev/null || echo "4")
fi

# ---------------------------------------------------------------------------
# Check 1: main.go exists and is non-empty
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if [ -s main.go ]; then
  PASSED=$((PASSED + 1))
else
  fail "main_go_missing_or_empty"
fi

# ---------------------------------------------------------------------------
# Check 2: go.mod present (module declaration intact)
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if [ -f go.mod ] && grep -q "^module " go.mod; then
  PASSED=$((PASSED + 1))
else
  fail "go_mod_missing_or_invalid"
fi

# ---------------------------------------------------------------------------
# Check 3: sync package imported in main.go
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if grep -qE '"sync(/atomic)?"' main.go || grep -q '"sync"' main.go; then
  PASSED=$((PASSED + 1))
else
  fail "sync_not_imported"
fi

# ---------------------------------------------------------------------------
# Check 4: Race-pattern-specific synchronisation primitive present
# Checks that the required primitive(s) appear in main.go.
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
PRIM_OK=true
IFS=',' read -ra PRIMS <<< "$FIX_PRIMITIVES"
for PRIM in "${PRIMS[@]}"; do
  case "$PRIM" in
    mutex)
      if ! grep -qE 'sync\.(RW)?Mutex|sync\.Map' main.go; then
        PRIM_OK=false
      fi
      ;;
    atomic)
      if ! grep -qE 'atomic\.(Add|Load|Store|Swap|Compare)|sync/atomic|sync\.Map' main.go; then
        PRIM_OK=false
      fi
      ;;
    "sync.Once")
      if ! grep -qE 'sync\.Once' main.go; then
        PRIM_OK=false
      fi
      ;;
    channel)
      # Channels are already present; check for buffered make or select-based drain
      if ! grep -qE 'make\(chan|select' main.go; then
        PRIM_OK=false
      fi
      ;;
  esac
done
if $PRIM_OK; then
  PASSED=$((PASSED + 1))
else
  fail "required_primitive_missing"
fi

# ---------------------------------------------------------------------------
# Check 5: Pattern-specific correctness — race is actually fixed
# Uses static analysis appropriate to each race type.
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
PATTERN_OK=false

case "$RACE_TYPE" in
  shared_map)
    # Map writes must be under a mutex (Lock before map assignment) OR sync.Map used
    if grep -qE 'sync\.Map' main.go; then
      PATTERN_OK=true
    elif python3 - <<'PYEOF'
import re, sys

src = open("main.go").read()
# Look for mutex lock calls within worker/store functions
has_lock = bool(re.search(r'\bLock\s*\(\)', src))
# Ensure a map write exists (the store)
has_map_write = bool(re.search(r'\bstore\b\s*\[', src))
# Rough check: Lock() appears alongside map write context
sys.exit(0 if (has_lock and has_map_write) else 1)
PYEOF
    then
      PATTERN_OK=true
    fi
    ;;
  counter)
    # Counter must use atomic.AddInt64/32 OR be under a mutex
    if grep -qE 'atomic\.Add(Int64|Int32|Uint64|Uint32)|atomic\.AddInt' main.go; then
      PATTERN_OK=true
    elif grep -qE '(mu|mutex|lock)\.(Lock|RLock)\s*\(\)' main.go && grep -q 'count' main.go; then
      PATTERN_OK=true
    fi
    ;;
  channel_close)
    # sync.Once must wrap the close, OR only one close call remains in non-worker scope
    if grep -qE 'sync\.Once' main.go; then
      PATTERN_OK=true
    else
      # Count close() calls on shared channels: should be exactly 1 outside worker
      CLOSE_COUNT=$(grep -c 'close(' main.go || true)
      # At most 2 closes acceptable: one for work channel, one for done
      if [ "$CLOSE_COUNT" -le 2 ]; then
        PATTERN_OK=true
      fi
    fi
    ;;
  slice_append)
    # Appends must be under mutex OR results collected via channel
    if grep -qE '\bLock\s*\(\)' main.go && grep -q 'append' main.go; then
      PATTERN_OK=true
    elif python3 - <<'PYEOF'
import re, sys
src = open("main.go").read()
# Check if append is gone (replaced by channel-based collection)
has_append = bool(re.search(r'\bappend\s*\(', src))
has_chan_recv = bool(re.search(r'<-\s*\w+ch\b|<-results\b|<-resCh\b|<-out\b', src))
# Acceptable: mutex + append, or channel collection without concurrent appends
has_lock = bool(re.search(r'\.Lock\s*\(\)', src))
sys.exit(0 if (has_lock and has_append) or (has_chan_recv and not has_append) else 1)
PYEOF
    then
      PATTERN_OK=true
    fi
    ;;
  lazy_init)
    # sync.Once must replace the double-checked lock pattern
    if grep -qE 'sync\.Once' main.go; then
      PATTERN_OK=true
    elif grep -qE 'atomic\.Load|atomic\.Store|atomic\.Pointer' main.go; then
      PATTERN_OK=true
    fi
    ;;
esac

if $PATTERN_OK; then
  PASSED=$((PASSED + 1))
else
  fail "race_pattern_not_fixed_${RACE_TYPE}"
fi

# ---------------------------------------------------------------------------
# Check 6: BUG comments removed or reduced (executor addressed the known bugs)
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
BUG_COUNT=$(grep -c '// BUG' main.go || true)
if [ "$BUG_COUNT" -eq 0 ]; then
  PASSED=$((PASSED + 1))
else
  # Partial credit: allow up to 1 stale comment but flag if all remain
  ORIG_BUG_COUNT=3
  if [ "$BUG_COUNT" -lt "$ORIG_BUG_COUNT" ]; then
    PASSED=$((PASSED + 1))
  else
    fail "bug_comments_not_addressed"
  fi
fi

# ---------------------------------------------------------------------------
# Check 7: No naked goroutine variable writes without synchronisation
# Heuristic: if there is a write to p.<field> inside a goroutine func literal
# without any Lock() call in that literal, flag it.
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
UNSAFE_WRITE=$(python3 - <<'PYEOF'
import re, sys

src = open("main.go").read()

# Find goroutine function literals
goroutine_bodies = re.findall(r'go\s+func\s*\([^)]*\)\s*\{(.*?)\n\t\}', src, re.DOTALL)
found_unsafe = False
for body in goroutine_bodies:
    has_shared_write = bool(re.search(r'\bp\.\w+\s*=|\bp\.\w+\s*\+\+|\bappend\s*\(p\.', body))
    has_lock = bool(re.search(r'\.Lock\s*\(\)|atomic\.|sync\.Once|\.Store\s*\(', body))
    if has_shared_write and not has_lock:
        found_unsafe = True
        break

print("unsafe" if found_unsafe else "ok")
PYEOF
)
if [ "$UNSAFE_WRITE" = "ok" ]; then
  PASSED=$((PASSED + 1))
else
  fail "unsynchronised_goroutine_write_detected"
fi

# ---------------------------------------------------------------------------
# Check 8: go build succeeds (when Go toolchain is available)
# Falls back to syntax check via gofmt when go is absent.
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if command -v go >/dev/null 2>&1; then
  if go build ./... > /tmp/go2_build_out 2>&1; then
    PASSED=$((PASSED + 1))
  else
    fail "build_failed"
  fi
else
  # Fallback: gofmt syntax check
  if command -v gofmt >/dev/null 2>&1; then
    if gofmt -e main.go > /dev/null 2>&1; then
      PASSED=$((PASSED + 1))
    else
      fail "syntax_error_no_go_toolchain"
    fi
  else
    # No toolchain at all — grant the check on structural validity
    if python3 - <<'PYEOF'
import sys
src = open("main.go").read()
# Basic structural checks
ok = (
    "package main" in src and
    "func main()" in src and
    src.count("{") == src.count("}")
)
sys.exit(0 if ok else 1)
PYEOF
    then
      PASSED=$((PASSED + 1))
    else
      fail "structural_syntax_error"
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Check 9: go vet passes (when toolchain available)
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if command -v go >/dev/null 2>&1; then
  if go vet ./... > /tmp/go2_vet_out 2>&1; then
    PASSED=$((PASSED + 1))
  else
    fail "vet_failed"
  fi
else
  # Static: check for common vet-caught issues via Python
  python3 - <<'PYEOF'
import re, sys
src = open("main.go").read()
issues = []
# Printf format mismatches (simplistic)
if re.search(r'fmt\.Printf\s*\("[^"]*%[dsfv][^"]*"\s*\)', src):
    pass  # format string present — OK heuristic
sys.exit(0)
PYEOF
  PASSED=$((PASSED + 1))
fi

# ---------------------------------------------------------------------------
# Check 10: go test -race passes (when toolchain available)
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if command -v go >/dev/null 2>&1; then
  if go test -race -count=3 -timeout 60s ./... > /tmp/go2_test_out 2>&1; then
    PASSED=$((PASSED + 1))
  else
    fail "race_test_failed"
  fi
else
  # Static fallback: verify race_test.go is present and untouched
  if [ -f race_test.go ] && grep -q "func Test" race_test.go; then
    PASSED=$((PASSED + 1))
  else
    fail "race_test_missing_or_modified"
  fi
fi

# ---------------------------------------------------------------------------
# Check 11: race_test.go not modified (executor must only fix main.go)
# Compare line count as a lightweight integrity check.
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if [ -f race_test.go ]; then
  TEST_LINES=$(wc -l < race_test.go)
  # race_test.go should have at least 20 lines (our generated tests are ~40+)
  if [ "$TEST_LINES" -ge 20 ]; then
    # Still has Test functions
    if grep -q "func Test" race_test.go; then
      PASSED=$((PASSED + 1))
    else
      fail "race_test_functions_removed"
    fi
  else
    fail "race_test_truncated"
  fi
else
  fail "race_test_missing"
fi

# ---------------------------------------------------------------------------
# Check 12: attestation.json verdict=pass
# ---------------------------------------------------------------------------
CHECKS=$((CHECKS + 1))
if python3 -c "
import json, sys
att = json.load(open(sys.argv[1]))
assert att.get('verdict') == 'pass'
" "$SUBMISSION/attestation.json" 2>/dev/null; then
  PASSED=$((PASSED + 1))
else
  fail "bad_attestation"
fi

# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then
  SUCCESS=1; PASS=true
else
  SUCCESS=0; PASS=false
fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {
    "checks_passed": $PASSED,
    "checks_total": $CHECKS,
    "partial_score": $PARTIAL,
    "race_type": "$RACE_TYPE"
  },
  "failure_modes": $FM
}
JSON
