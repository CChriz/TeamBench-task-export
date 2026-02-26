#!/usr/bin/env bash
# Seed-aware grader for SQL2: Query Optimize
# Reads ground-truth from expected.json; validates optimizer.py output and schema.sql.
#
# Args: $1=WORKSPACE $2=REPORTS $3=SUBMISSION $4=TASK_DIR [$5=EXPECTED_JSON]
set -o pipefail
WORKSPACE="$1"
REPORTS="$2"
SUBMISSION="$3"
TASK_DIR="$4"
EXPECTED="${5:-$REPORTS/expected.json}"

mkdir -p "$REPORTS"

CHECKS=0; PASSED=0; FAILURES=""
check() {
  CHECKS=$((CHECKS + 1))
  if eval "$1" 2>/dev/null; then
    PASSED=$((PASSED + 1))
  else
    FAILURES="${FAILURES:+${FAILURES},}$2"
  fi
}

cd "$WORKSPACE"

# ── Check 1: optimizer.py exists ──────────────────────────────────────────────
check "test -f optimizer.py" "missing_optimizer_py"

# ── Check 2: schema.sql exists ────────────────────────────────────────────────
check "test -f schema.sql" "missing_schema_sql"

# ── Check 3: optimizer.py runs without error ──────────────────────────────────
check "python3 optimizer.py schema.sql" "optimizer_crash"

# ── Check 4: schema.sql contains at least one CREATE INDEX ────────────────────
check "grep -qi 'CREATE INDEX' schema.sql" "no_create_index_in_schema"

# ── Check 5: Correct number of indexes created ────────────────────────────────
check "python3 - <<'PYEOF'
import json, re, sys
expected = json.load(open('$EXPECTED'))
req_count = len(expected['required_indexes'])
with open('schema.sql') as f:
    content = f.read()
found = len(re.findall(r'CREATE\s+INDEX', content, re.IGNORECASE))
assert found >= req_count, f'Expected >= {req_count} CREATE INDEX statements, found {found}'
print(f'INDEX_COUNT_OK: {found} >= {req_count}')
PYEOF" "wrong_index_count"

# ── Check 6: All required index names are present ─────────────────────────────
check "python3 - <<'PYEOF'
import json, sys
expected = json.load(open('$EXPECTED'))
with open('schema.sql') as f:
    content = f.read().lower()
missing = []
for ix in expected['required_indexes']:
    if ix['name'].lower() not in content:
        missing.append(ix['name'])
assert not missing, f'Missing index names: {missing}'
print('INDEX_NAMES_OK')
PYEOF" "missing_required_index_names"

# ── Check 7: Naming convention — all index names start with "idx_" ────────────
check "python3 - <<'PYEOF'
import re
with open('schema.sql') as f:
    content = f.read()
# Extract all index names from CREATE INDEX statements
names = re.findall(r'CREATE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', content, re.IGNORECASE)
bad = [n for n in names if not n.lower().startswith('idx_')]
assert not bad, f'Index names not starting with idx_: {bad}'
print(f'NAMING_CONVENTION_OK: {len(names)} indexes all start with idx_')
PYEOF" "naming_convention_violated"

# ── Check 8: Required index columns are present ───────────────────────────────
check "python3 - <<'PYEOF'
import json, re
expected = json.load(open('$EXPECTED'))
with open('schema.sql') as f:
    content = f.read().lower()
missing_cols = []
for ix in expected['required_indexes']:
    # Check that the key columns appear near the index name in schema.sql
    idx_name = ix['name'].lower()
    cols_str = ix['columns'].lower()
    # Extract table and first column from the columns spec (e.g. 'orders(user_id, created_at)')
    m = re.match(r'(\w+)\((.+)\)', cols_str)
    if m:
        table = m.group(1)
        first_col = m.group(2).split(',')[0].strip()
        # Find the CREATE INDEX block for this index
        pattern = rf'create\s+index[^;]*{re.escape(idx_name)}[^;]*on\s+{re.escape(table)}\s*\([^)]*{re.escape(first_col)}'
        if not re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            missing_cols.append(f'{idx_name}: table={table} first_col={first_col}')
assert not missing_cols, f'Index column mismatches: {missing_cols}'
print('INDEX_COLUMNS_OK')
PYEOF" "wrong_index_columns"

# ── Check 9: All slow query names are covered ─────────────────────────────────
check "python3 - <<'PYEOF'
import json, ast, sys, re

expected = json.load(open('$EXPECTED'))
query_names = set(expected['query_names'])

# Read optimizer.py and look for get_indexes() return
with open('optimizer.py') as f:
    src = f.read()

# Check that get_indexes does not return an empty list
assert 'return []' not in src or src.count('return []') == 0, \
    'get_indexes() still returns empty list'

# Check that each query name is referenced somewhere in the file
missing = []
for qname in query_names:
    if qname not in src:
        missing.append(qname)
assert not missing, f'Query names not referenced in optimizer.py: {missing}'
print('QUERY_COVERAGE_OK')
PYEOF" "queries_not_covered"

# ── Check 10: Storage budget not exceeded ─────────────────────────────────────
check "python3 - <<'PYEOF'
import json, re

expected = json.load(open('$EXPECTED'))
budget = expected['storage_budget_mb']

size_estimates = {'btree': 40.0, 'partial': 12.0, 'composite': 55.0, 'covering': 80.0}

with open('schema.sql') as f:
    content = f.read()

# Count indexes by type using comments in schema.sql (optimizer.py writes them)
type_counts = {}
for ix in expected['required_indexes']:
    t = ix['type']
    type_counts[t] = type_counts.get(t, 0) + 1

# Recompute from required_indexes (authoritative)
total = sum(size_estimates.get(ix['type'], 40.0) for ix in expected['required_indexes'])
assert total <= budget, f'Estimated index storage {total:.1f} MB exceeds budget {budget} MB'
print(f'STORAGE_BUDGET_OK: {total:.1f} MB <= {budget} MB')
PYEOF" "storage_budget_exceeded"

# ── Check 11: Index type annotations present in schema.sql ───────────────────
check "python3 - <<'PYEOF'
import json, re

expected = json.load(open('$EXPECTED'))
with open('schema.sql') as f:
    content = f.read().lower()

# Check that type comments appear (optimizer.py should write them)
type_keywords = expected.get('index_types_required', [])
missing_type_comments = []
for t in type_keywords:
    if f'type: {t}' not in content:
        missing_type_comments.append(t)
assert not missing_type_comments, f'Missing type annotations in schema.sql: {missing_type_comments}'
print('TYPE_ANNOTATIONS_OK')
PYEOF" "missing_type_annotations"

# ── Check 12: validate_budget() function present and callable ─────────────────
check "python3 - <<'PYEOF'
import importlib.util, sys, os

spec = importlib.util.spec_from_file_location('optimizer', 'optimizer.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert hasattr(mod, 'validate_budget'), 'validate_budget() function missing from optimizer.py'
assert hasattr(mod, 'get_indexes'), 'get_indexes() function missing from optimizer.py'
assert callable(mod.validate_budget), 'validate_budget is not callable'
assert callable(mod.get_indexes), 'get_indexes is not callable'

# Call get_indexes and validate it returns a list
indexes = mod.get_indexes()
assert isinstance(indexes, list), f'get_indexes() must return list, got {type(indexes)}'
assert len(indexes) > 0, 'get_indexes() returned empty list'
print(f'FUNCTIONS_OK: get_indexes() returned {len(indexes)} entries')
PYEOF" "optimizer_functions_broken"

# ── Check 13: get_indexes() entries have required fields ──────────────────────
check "python3 - <<'PYEOF'
import importlib.util

spec = importlib.util.spec_from_file_location('optimizer', 'optimizer.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

indexes = mod.get_indexes()
required_fields = {'name', 'table', 'columns', 'type', 'query'}
bad = []
for i, ix in enumerate(indexes):
    missing = required_fields - set(ix.keys())
    if missing:
        bad.append(f'entry[{i}] missing fields: {missing}')
    if not ix.get('name', '').startswith('idx_'):
        bad.append(f'entry[{i}] name {ix.get(\"name\")!r} does not start with idx_')
    if ix.get('type') not in ('btree', 'partial', 'composite', 'covering'):
        bad.append(f'entry[{i}] invalid type: {ix.get(\"type\")!r}')
    if not isinstance(ix.get('columns'), list) or not ix['columns']:
        bad.append(f'entry[{i}] columns must be non-empty list')
assert not bad, f'Index entry validation failures: {bad}'
print(f'INDEX_ENTRIES_VALID_OK: {len(indexes)} entries all valid')
PYEOF" "invalid_index_entries"

# ── Check 14: Partial indexes have WHERE clause ───────────────────────────────
check "python3 - <<'PYEOF'
import importlib.util, json

expected = json.load(open('$EXPECTED'))
partial_required = [ix for ix in expected['required_indexes'] if ix['type'] == 'partial']

if not partial_required:
    print('PARTIAL_INDEX_CHECK_SKIPPED: no partial indexes required')
else:
    spec = importlib.util.spec_from_file_location('optimizer', 'optimizer.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    indexes = {ix['name']: ix for ix in mod.get_indexes()}
    bad = []
    for req in partial_required:
        name = req['name']
        if name in indexes:
            ix = indexes[name]
            if not ix.get('partial_where'):
                bad.append(f'{name}: partial index missing partial_where clause')
    assert not bad, f'Partial index WHERE clauses missing: {bad}'
    print(f'PARTIAL_INDEX_WHERE_OK: {len(partial_required)} partial index(es) have WHERE clauses')
PYEOF" "partial_indexes_missing_where"

# ── Check 15: Schema SQL is valid SQLite (parse check) ────────────────────────
check "python3 - <<'PYEOF'
import sqlite3, re

with open('schema.sql') as f:
    content = f.read()

# Strip partial index WHERE clauses for SQLite compat check
# (SQLite supports partial indexes but let's verify the DDL is at least parseable)
conn = sqlite3.connect(':memory:')
# Execute statement by statement, skip lines starting with --
stmts = [s.strip() for s in content.split(';') if s.strip() and not s.strip().startswith('--')]
errors = []
for stmt in stmts:
    try:
        conn.execute(stmt)
    except sqlite3.OperationalError as e:
        errors.append(f'{str(e)[:80]}: ...{stmt[:60]}...')
conn.close()
assert not errors, f'SQLite parse errors in schema.sql: {errors}'
print(f'SCHEMA_SQL_VALID_OK: {len(stmts)} statements parsed cleanly')
PYEOF" "schema_sql_invalid"

# ── Write score.json ──────────────────────────────────────────────────────────
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
    "partial_score": $PARTIAL
  },
  "failure_modes": $FM
}
JSON
