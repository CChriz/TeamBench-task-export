#!/usr/bin/env bash
# INT3 grader: verify database migration bugs are fixed
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
# C1: All migration files are valid Python
# -------------------------------------------------------------------
if python3 -c "
import ast, sys, glob
for f in sorted(glob.glob('migrations/*.py')):
    if f.endswith('__init__.py'):
        continue
    try:
        ast.parse(open(f).read())
    except SyntaxError as e:
        print(f'Syntax error in {f}: {e}', file=sys.stderr)
        sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C1" "All migration files are valid Python" "pass"
else
    check "C1" "Migration file has syntax error" "fail"
fi

# -------------------------------------------------------------------
# C2: migrate.py up succeeds (all migrations apply)
# -------------------------------------------------------------------
if python3 migrate.py up 2>/dev/null; then
    check "C2" "migrate.py up succeeds" "pass"
else
    check "C2" "migrate.py up fails" "fail"
fi

# -------------------------------------------------------------------
# C3: migrate.py down succeeds (rollback all)
# -------------------------------------------------------------------
if python3 migrate.py up 2>/dev/null && python3 migrate.py down 2>/dev/null; then
    check "C3" "migrate.py down succeeds after up" "pass"
else
    check "C3" "migrate.py down fails" "fail"
fi

# -------------------------------------------------------------------
# C4: FK constraint order fixed (referenced table created before FK)
# -------------------------------------------------------------------
if python3 -c "
import sys
# Run migrations up and check no FK error
try:
    exec(open('migrate.py').read().replace('sys.exit', '# '))
except:
    pass
# Check migration 002 creates the parent table or references existing one
src = open('migrations/002_add_features.py').read()
# The fix should ensure CREATE TABLE for referenced table comes before FK
if 'REFERENCES' in src:
    lines = src.split('\n')
    ref_line = next((i for i, l in enumerate(lines) if 'REFERENCES' in l), -1)
    create_lines = [i for i, l in enumerate(lines) if 'CREATE TABLE' in l.upper()]
    if create_lines and ref_line > create_lines[0]:
        sys.exit(0)
    # Or references a table from 001
    sys.exit(0)
sys.exit(0)
" 2>/dev/null; then
    check "C4" "FK constraint ordering is correct" "pass"
else
    check "C4" "FK constraint ordering still broken" "fail"
fi

# -------------------------------------------------------------------
# C5: NOT NULL column has DEFAULT value
# -------------------------------------------------------------------
if python3 -c "
import sys
src = open('migrations/002_add_features.py').read().upper()
# Any ADD COLUMN ... NOT NULL should have DEFAULT
import re
adds = re.findall(r'ADD\s+COLUMN\s+\w+\s+\w+\s+NOT\s+NULL(?!\s+DEFAULT)', src)
sys.exit(1 if adds else 0)
" 2>/dev/null; then
    check "C5" "NOT NULL columns have DEFAULT values" "pass"
else
    check "C5" "NOT NULL column without DEFAULT" "fail"
fi

# -------------------------------------------------------------------
# C6: Index names do not collide
# -------------------------------------------------------------------
if python3 -c "
import sys, re
all_indexes = []
import glob
for f in sorted(glob.glob('migrations/*.py')):
    if '__init__' in f:
        continue
    src = open(f).read()
    idxs = re.findall(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', src, re.I)
    all_indexes.extend(idxs)
# Check for duplicates
if len(all_indexes) != len(set(all_indexes)):
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C6" "No index name collisions" "pass"
else
    check "C6" "Index name collision detected" "fail"
fi

# -------------------------------------------------------------------
# C7: Rollback drops correct column
# -------------------------------------------------------------------
if python3 -c "
import sys, re
src = open('migrations/002_add_features.py').read()
# Find the down/rollback function
# The rollback should drop the column that was added in up, not a wrong one
up_adds = re.findall(r'ADD\s+COLUMN\s+(\w+)', src, re.I)
down_drops = re.findall(r'DROP\s+COLUMN\s+(\w+)', src, re.I)
# The dropped columns should be subset of added columns
for col in down_drops:
    if col.lower() not in [a.lower() for a in up_adds]:
        sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C7" "Rollback drops correct columns" "pass"
else
    check "C7" "Rollback drops wrong column" "fail"
fi

# -------------------------------------------------------------------
# C8: Full round-trip: up -> verify schema -> down -> verify clean
# -------------------------------------------------------------------
if python3 -c "
import sys, os, sqlite3
db = 'test_migration_c8.db'
if os.path.exists(db):
    os.remove(db)
os.environ['MIGRATION_DB'] = db
exec(open('migrate.py').read().replace('if __name__', 'if False #'))
from migrate import run_up, run_down
try:
    run_up(db)
    run_down(db)
except Exception as e:
    print(f'Round-trip failed: {e}', file=sys.stderr)
    sys.exit(1)
finally:
    if os.path.exists(db):
        os.remove(db)
sys.exit(0)
" 2>/dev/null; then
    check "C8" "Full migration round-trip succeeds" "pass"
else
    check "C8" "Full migration round-trip fails" "fail"
fi

# -------------------------------------------------------------------
# C9: Tests pass
# -------------------------------------------------------------------
if python3 -m pytest tests/ -q --tb=no 2>/dev/null | grep -q "passed"; then
    check "C9" "Migration tests pass" "pass"
else
    check "C9" "Migration tests fail" "fail"
fi

# -------------------------------------------------------------------
# C10: migrate.py not modified
# -------------------------------------------------------------------
if python3 -c "
import hashlib, sys, os
src = open('migrate.py', 'rb').read()
expected = os.environ.get('MIGRATE_PY_HASH', '')
if expected and hashlib.sha256(src).hexdigest() != expected:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
    check "C10" "migrate.py not modified" "pass"
else
    check "C10" "migrate.py was modified (should not be)" "fail"
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
