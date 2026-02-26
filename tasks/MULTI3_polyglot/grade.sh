#!/usr/bin/env bash
# Seed-aware grader for MULTI3_polyglot: Polyglot Interface Bug Fix.
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
    local expr="$1"
    local tag="$2"
    CHECKS=$((CHECKS + 1))
    if eval "$expr" 2>/dev/null; then
        PASSED=$((PASSED + 1))
    else
        FAILURES="${FAILURES:+${FAILURES},}${tag}"
    fi
}

cd "$WORKSPACE"

# Ensure __init__.py stubs exist for package imports
for pkg in backend frontend shared tests; do
    [ -d "$pkg" ] && touch "$pkg/__init__.py"
done

# ---------------------------------------------------------------------------
# Load seed-specific expected values from expected.json
# ---------------------------------------------------------------------------
ID_FIELD="config_id"
DATE_FIELD="updated_at"
NULL_FIELD="note"
WRONG_SCHEMA_FIELD="service"
CORRECT_SCHEMA_FIELD="service_name"

if [ -f "$EXPECTED" ]; then
    ID_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED')); print(d.get('id_field','config_id'))" 2>/dev/null || echo "config_id")
    DATE_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED')); print(d.get('date_field','updated_at'))" 2>/dev/null || echo "updated_at")
    NULL_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED')); print(d.get('null_field','note'))" 2>/dev/null || echo "note")
    WRONG_SCHEMA_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED')); print(d.get('wrong_schema_field','service'))" 2>/dev/null || echo "service")
    CORRECT_SCHEMA_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED')); print(d.get('correct_schema_field','service_name'))" 2>/dev/null || echo "service_name")
fi

# ---------------------------------------------------------------------------
# Check 1: backend/processor.py exists and imports cleanly
# ---------------------------------------------------------------------------
check "test -f '$WORKSPACE/backend/processor.py'" "missing_processor"
check "python3 -c 'import sys; sys.path.insert(0,\"$WORKSPACE\"); import backend.processor'" "processor_import_error"

# ---------------------------------------------------------------------------
# Check 2: frontend/handler.py exists and imports cleanly
# ---------------------------------------------------------------------------
check "test -f '$WORKSPACE/frontend/handler.py'" "missing_handler"
check "python3 -c 'import sys; sys.path.insert(0,\"$WORKSPACE\"); import frontend.handler'" "handler_import_error"

# ---------------------------------------------------------------------------
# Check 3: shared/schema.json is valid JSON with required keys
# ---------------------------------------------------------------------------
check "test -f '$WORKSPACE/shared/schema.json'" "missing_schema"
check "python3 -c \"
import json
s = json.load(open('$WORKSPACE/shared/schema.json'))
assert 'record_fields' in s, 'missing record_fields'
assert 'envelope' in s, 'missing envelope'
\"" "schema_invalid_json"

# ---------------------------------------------------------------------------
# Check 4: schema.json uses correct field names (no wrong aliases)
# ---------------------------------------------------------------------------
check "python3 -c \"
import json
s = json.load(open('$WORKSPACE/shared/schema.json'))
rf = s['record_fields']
assert '${CORRECT_SCHEMA_FIELD}' in rf, \
    f'schema.json missing correct field ${CORRECT_SCHEMA_FIELD}, has: {list(rf.keys())}'
assert '${WRONG_SCHEMA_FIELD}' not in rf, \
    f'schema.json still has wrong field name ${WRONG_SCHEMA_FIELD}'
\"" "schema_wrong_field_name"

# ---------------------------------------------------------------------------
# Check 5: schema.json lists all expected spec fields
# ---------------------------------------------------------------------------
check "python3 -c \"
import json, sys
s = json.load(open('$WORKSPACE/shared/schema.json'))
rf = s['record_fields']
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
for f in [id_field, date_field, null_field]:
    assert f in rf, f'schema.json missing field {f!r}, has: {list(rf.keys())}'
\"" "schema_missing_spec_fields"

# ---------------------------------------------------------------------------
# Check 6: backend serialize_record emits correct ID field key (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import backend.processor as p
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
rec = {id_field: 99, date_field: datetime.date(2024, 3, 10), null_field: None}
wire = p.serialize_record(rec)
assert id_field in wire, f'serialize_record emits wrong id key; got: {list(wire.keys())}'
assert wire[id_field] == 99, f'{id_field} value wrong: {wire[id_field]!r}'
PYEOF" "backend_wrong_id_key"

# ---------------------------------------------------------------------------
# Check 7: backend formats dates as ISO-8601 YYYY-MM-DD (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import backend.processor as p
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
rec = {id_field: 1, date_field: datetime.date(2024, 6, 15), null_field: None}
wire = p.serialize_record(rec)
val = wire.get(date_field, '')
assert isinstance(val, str), f'{date_field} must be str in wire, got {type(val).__name__}'
parts = val.split('-')
assert len(parts) == 3 and len(parts[0]) == 4, f'Expected YYYY-MM-DD, got {val!r}'
datetime.date.fromisoformat(val)
PYEOF" "backend_wrong_date_format"

# ---------------------------------------------------------------------------
# Check 8: backend encodes None as JSON null (not sentinel string) (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import backend.processor as p
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
rec = {id_field: 1, date_field: datetime.date(2024, 1, 1), null_field: None}
wire = p.serialize_record(rec)
val = wire.get(null_field)
assert val is None, f'{null_field} must be None (JSON null), got {val!r}'
PYEOF" "backend_null_sentinel"

# ---------------------------------------------------------------------------
# Check 9: backend serialize_batch wraps records under 'data' key (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import backend.processor as p
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
rec = {id_field: 1, date_field: datetime.date(2024, 1, 1), null_field: None}
env = p.serialize_batch([rec])
assert 'data' in env, f'envelope missing data key; has: {list(env.keys())}'
assert isinstance(env['data'], list), 'envelope[data] must be a list'
assert env.get('count') == 1, f'count should be 1, got {env.get(\"count\")}'
PYEOF" "backend_wrong_envelope_key"

# ---------------------------------------------------------------------------
# Check 10: backend encodes bool fields as bool not int (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import backend.processor as p
import inspect
# Find a bool field by inspecting the source
src = inspect.getsource(p.serialize_record)
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
# Detect bool fields: look for True/False pattern or field names ending in is_/enabled/resolved
import re
bool_fields = re.findall(r\"['\"](\w+)['\"].*?int\(record\[", src)
if bool_fields:
    for bf in bool_fields:
        assert False, f'serialize_record still casts {bf} to int — should remain bool'
# Also check source does not use int() on record values
assert 'int(record[' not in src, 'serialize_record casts bool field to int — remove int() cast'
PYEOF" "backend_bool_as_int"

# ---------------------------------------------------------------------------
# Check 11: frontend deserialize_record reads correct ID key (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import frontend.handler as h
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
wire = {id_field: 42, date_field: '2024-06-15', null_field: None}
rec = h.deserialize_record(wire)
assert id_field in rec, f'deserialize_record missing {id_field!r}; has: {list(rec.keys())}'
assert rec[id_field] == 42, f'{id_field} wrong value: {rec[id_field]!r}'
PYEOF" "frontend_wrong_id_read"

# ---------------------------------------------------------------------------
# Check 12: frontend handles None in nullable field without crashing (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import frontend.handler as h
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
wire = {id_field: 42, date_field: '2024-06-15', null_field: None}
try:
    rec = h.deserialize_record(wire)
except AttributeError as e:
    raise AssertionError(f'handler crashed on None {null_field}: {e}')
assert rec.get(null_field) is None, f'{null_field} should be None, got {rec.get(null_field)!r}'
PYEOF" "frontend_null_crash"

# ---------------------------------------------------------------------------
# Check 13: frontend parses dates as datetime.date objects (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import frontend.handler as h
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
wire = {id_field: 42, date_field: '2024-06-15', null_field: None}
rec = h.deserialize_record(wire)
val = rec.get(date_field)
assert isinstance(val, datetime.date), \
    f'{date_field} must be datetime.date, got {type(val).__name__}: {val!r}'
assert val == datetime.date(2024, 6, 15), f'{date_field} wrong: {val!r}'
PYEOF" "frontend_wrong_date_parse"

# ---------------------------------------------------------------------------
# Check 14: frontend process_envelope reads from 'data' key (runtime)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, datetime
sys.path.insert(0, '$WORKSPACE')
import frontend.handler as h
id_field = '${ID_FIELD}'
date_field = '${DATE_FIELD}'
null_field = '${NULL_FIELD}'
wire = {id_field: 42, date_field: '2024-06-15', null_field: None}
envelope = {'data': [wire], 'count': 1}
records = h.process_envelope(envelope)
assert isinstance(records, list), 'process_envelope must return a list'
assert len(records) == 1, f'expected 1 record, got {len(records)}'
PYEOF" "frontend_wrong_envelope_read"

# ---------------------------------------------------------------------------
# Check 15: full test suite passes (unittest)
# ---------------------------------------------------------------------------
check "python3 '$WORKSPACE/tests/test_contract.py' 2>&1 | grep -q '^OK'" "test_suite_failed"

# ---------------------------------------------------------------------------
# Write score
# ---------------------------------------------------------------------------
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 4))" 2>/dev/null || echo "0")
if [ "$PASSED" -eq "$CHECKS" ]; then
    PASS=true
else
    PASS=false
fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))" 2>/dev/null || echo "[]")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $([ "$PASS" = "true" ] && echo 1 || echo 0)},
  "secondary": {
    "checks_passed": $PASSED,
    "checks_total": $CHECKS,
    "partial_score": $PARTIAL
  },
  "failure_modes": $FM
}
JSON

echo "Grade: $PASSED/$CHECKS ($PARTIAL) failures=[${FAILURES}]"
exit 0
