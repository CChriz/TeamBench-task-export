#!/usr/bin/env bash
# Seed-aware grader for MULTI3_polyglot: Polyglot Interface Bug Fix.
#
# Runs each unittest method individually for precise per-check scoring.
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
# Load seed-specific expected values
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

# Discover test class name from the test file
TEST_CLASS=$(python3 -c "
import re
src = open('$WORKSPACE/tests/test_contract.py').read()
m = re.search(r'class (\w+ContractTestCase)', src)
print(m.group(1) if m else 'ContractTestCase')
" 2>/dev/null || echo "ContractTestCase")

# Helper: run one unittest method, return 0 if it passes
run_test() {
    local method="$1"
    python3 -m unittest "tests.test_contract.${TEST_CLASS}.${method}" \
        --tb=no -q 2>/dev/null
}

# ---------------------------------------------------------------------------
# Check 1-4: files exist and compile
# ---------------------------------------------------------------------------
check "test -f '$WORKSPACE/backend/processor.py'" "missing_processor"
check "test -f '$WORKSPACE/frontend/handler.py'" "missing_handler"
check "test -f '$WORKSPACE/shared/schema.json'" "missing_schema"
check "python3 -m py_compile '$WORKSPACE/backend/processor.py' && \
       python3 -m py_compile '$WORKSPACE/frontend/handler.py'" "syntax_errors"

# ---------------------------------------------------------------------------
# Check 5-6: modules import cleanly (maps to unittest import tests)
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && run_test() { python3 -m unittest tests.test_contract.${TEST_CLASS}.\$1 -q 2>/dev/null; }; run_test test_processor_imports" \
    "processor_import_error"
check "cd '$WORKSPACE' && run_test() { python3 -m unittest tests.test_contract.${TEST_CLASS}.\$1 -q 2>/dev/null; }; run_test test_handler_imports" \
    "handler_import_error"

# ---------------------------------------------------------------------------
# Check 7-8: schema validity (maps to unittest schema tests)
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_schema_json_valid -q 2>/dev/null" \
    "schema_invalid"
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_schema_fields_match_spec -q 2>/dev/null" \
    "schema_wrong_fields"

# ---------------------------------------------------------------------------
# Check 9: schema.json correct/wrong field names (direct JSON check)
# ---------------------------------------------------------------------------
check "python3 -c \"
import json
s = json.load(open('$WORKSPACE/shared/schema.json'))
rf = s['record_fields']
assert '${CORRECT_SCHEMA_FIELD}' in rf, 'missing correct field'
assert '${WRONG_SCHEMA_FIELD}' not in rf, 'wrong field still present'
\"" "schema_field_alias_wrong"

# ---------------------------------------------------------------------------
# Check 10: backend emits correct ID field name
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_backend_id_field_name -q 2>/dev/null" \
    "backend_wrong_id_key"

# ---------------------------------------------------------------------------
# Check 11: backend date format is ISO-8601
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_backend_date_format -q 2>/dev/null" \
    "backend_wrong_date_format"

# ---------------------------------------------------------------------------
# Check 12: backend null handling (None not sentinel)
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_backend_null_is_none -q 2>/dev/null" \
    "backend_null_sentinel"

# ---------------------------------------------------------------------------
# Check 13: backend envelope uses 'data' key
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_envelope_key -q 2>/dev/null" \
    "backend_wrong_envelope"

# ---------------------------------------------------------------------------
# Check 14: backend bool fields remain bool (not int) — only if test exists
# ---------------------------------------------------------------------------
if grep -q "def test_bool_is_bool" "$WORKSPACE/tests/test_contract.py" 2>/dev/null; then
    check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_bool_is_bool -q 2>/dev/null" \
        "backend_bool_as_int"
fi

# ---------------------------------------------------------------------------
# Check 15: frontend reads correct ID field name
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_frontend_id_field_read -q 2>/dev/null" \
    "frontend_wrong_id_read"

# ---------------------------------------------------------------------------
# Check 16: frontend handles None in nullable field without crashing
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_frontend_null_guard -q 2>/dev/null" \
    "frontend_null_crash"

# ---------------------------------------------------------------------------
# Check 17: frontend parses dates as datetime.date
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_frontend_date_parse -q 2>/dev/null" \
    "frontend_wrong_date_parse"

# ---------------------------------------------------------------------------
# Check 18: frontend reads records from 'data' envelope key
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_frontend_envelope_read -q 2>/dev/null" \
    "frontend_wrong_envelope"

# ---------------------------------------------------------------------------
# Check 19: round-trip (serialize -> deserialize) reproduces values
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 -m unittest tests.test_contract.${TEST_CLASS}.test_round_trip -q 2>/dev/null" \
    "round_trip_failed"

# ---------------------------------------------------------------------------
# Check 20: full test suite passes (all tests green)
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE' && python3 tests/test_contract.py 2>&1 | tail -1 | grep -q '^OK'" \
    "test_suite_failed"

# ---------------------------------------------------------------------------
# Write score
# ---------------------------------------------------------------------------
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 4))" 2>/dev/null || echo "0")
if [ "$PASSED" -eq "$CHECKS" ]; then
    PASS=true
else
    PASS=false
fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))" \
    2>/dev/null || echo "[]")

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
