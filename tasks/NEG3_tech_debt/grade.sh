#!/usr/bin/env bash
set -o pipefail
WORKSPACE="$1"
REPORTS="$2"
SUBMISSION="$3"
TASK_DIR="$4"

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

# Write a shared helper that extracts PLAN from prioritize.py
cat > /tmp/_neg3_extract_plan.py << 'PYEOF'
import ast, json, sys
with open("prioritize.py") as f:
    src = f.read()
tree = ast.parse(src)
plan = None
for node in ast.walk(tree):
    if isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.target.id == "PLAN" and node.value:
            plan = ast.literal_eval(node.value)
            break
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "PLAN":
                plan = ast.literal_eval(node.value)
                break
        if plan is not None:
            break
if plan is None:
    print("PLAN not found", file=sys.stderr)
    sys.exit(1)
with open("/tmp/_neg3_plan.json", "w") as f:
    json.dump(plan, f)
print(f"PLAN: {plan}")
PYEOF

# Pre-extract plan (best-effort; individual checks catch failures)
python3 /tmp/_neg3_extract_plan.py 2>/dev/null || true

# 1. PLAN defined and non-empty
check "python3 /tmp/_neg3_extract_plan.py && \
python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
assert isinstance(plan, list) and len(plan) > 0
print('PLAN_EXISTS:', plan)
\"" "plan_not_defined"

# 2. plan_valid: python prioritize.py exits 0
check "python3 prioritize.py" "plan_invalid"

# 3. Exactly 3 items selected
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
assert len(plan) == 3, f'Expected 3 items, got {len(plan)}'
print('EXACTLY_3_OK:', plan)
\"" "not_exactly_3_items"

# 4. Time budget not exceeded
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
with open('tech_debt.json') as f:
    reg = json.load(f)
items_by_id = {item['id']: item for item in reg['items']}
budget = reg['time_budget_hours']
total = sum(items_by_id[tid]['fix_hours'] for tid in plan if tid in items_by_id)
assert total <= budget, f'Budget exceeded: {total}h > {budget}h'
print(f'BUDGET_OK: {total}h / {budget}h')
\"" "budget_exceeded"

# 5. Dependency order respected (blocker before dependent, if both selected)
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
with open('tech_debt.json') as f:
    reg = json.load(f)
dep = reg.get('dependency')
if dep is None:
    print('NO_DEP: no dependency constraint')
else:
    blocker = dep['blocker']
    dependent = dep['dependent']
    if blocker in plan and dependent in plan:
        bi = plan.index(blocker)
        di = plan.index(dependent)
        assert bi < di, f'Violation: {blocker} pos {bi} must < {dependent} pos {di}'
        print(f'DEP_ORDER_OK: {blocker} before {dependent}')
    else:
        print('DEP_NOT_BOTH_SELECTED: N/A')
\"" "dependency_order_violated"

# 6. Dependent not selected without its blocker
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
with open('tech_debt.json') as f:
    reg = json.load(f)
dep = reg.get('dependency')
if dep is None:
    print('NO_DEP')
else:
    blocker = dep['blocker']
    dependent = dep['dependent']
    if dependent in plan:
        assert blocker in plan, f'{dependent} selected without its blocker {blocker}'
    print('DEPENDENT_WITHOUT_BLOCKER_OK')
\"" "dependent_without_blocker"

# 7. Selected items have total value >= 80% of the greedy-optimal total value
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
with open('tech_debt.json') as f:
    reg = json.load(f)
items = reg['items']
budget = reg['time_budget_hours']
max_items = reg['max_items_to_fix']
items_by_id = {i['id']: i for i in items}
# Greedy optimal value (budget-aware)
ranked = sorted(items, key=lambda x: x['value_score'], reverse=True)
opt_val = 0; opt_hrs = 0; opt_cnt = 0
for item in ranked:
    if opt_cnt >= max_items: break
    if opt_hrs + item['fix_hours'] <= budget:
        opt_val += item['value_score']; opt_hrs += item['fix_hours']; opt_cnt += 1
plan_val = sum(items_by_id[tid]['value_score'] for tid in plan if tid in items_by_id)
threshold = opt_val * 0.8
assert plan_val >= threshold, f'Plan value {plan_val} < 80% of optimal {opt_val} (threshold {threshold})'
print(f'HIGH_VALUE_OK: plan={plan_val} >= 80% of optimal={opt_val}')
\"" "low_value_items_selected"

# 8. No bare except clauses (only if TD005 in plan)
check "python3 -c \"
import json, ast
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD005' not in plan:
    print('TD005_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        src = f.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            raise AssertionError('Bare except found — TD005 not fixed')
    print('NO_BARE_EXCEPT_OK')
\"" "bare_except_not_fixed"

# 9. Named constants present (only if TD004 in plan)
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD004' not in plan:
    print('TD004_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        src = f.read()
    ok = any(n in src for n in ['TIMEOUT_SECONDS', 'MAX_RETRIES', 'MAX_BATCH_SIZE'])
    assert ok, 'Named constants missing — TD004 not fixed'
    print('NAMED_CONSTANTS_OK')
\"" "named_constants_not_fixed"

# 10. No old_format() calls (only if TD007 in plan)
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD007' not in plan:
    print('TD007_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        src = f.read()
    assert 'old_format' not in src, 'old_format() still present — TD007 not fixed'
    print('NO_OLD_FORMAT_OK')
\"" "old_format_not_replaced"

# 11. Public method type annotations (only if TD002 in plan)
check "python3 -c \"
import json, ast
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD002' not in plan:
    print('TD002_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        src = f.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ('process','fetch','delete','list_all'):
            assert node.returns is not None, f'{node.name} missing return annotation — TD002 not fixed'
    print('TYPE_ANNOTATIONS_OK')
\"" "type_annotations_missing"

# 12. Legacy function removed (only if TD001 in plan)
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD001' not in plan:
    print('TD001_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        src = f.read()
    assert '_legacy_process' not in src, '_legacy_process still present — TD001 not fixed'
    print('NO_LEGACY_FUNCTION_OK')
\"" "legacy_function_not_removed"

# 13. Debug comment block removed (only if TD010 in plan)
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD010' not in plan:
    print('TD010_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        src = f.read()
    assert 'DEBUG BLOCK' not in src, 'Debug block still present — TD010 not fixed'
    assert '# import pdb' not in src, 'Debug block still present — TD010 not fixed'
    print('NO_DEBUG_BLOCK_OK')
\"" "debug_block_not_removed"

# 14. Tests replaced (not just stubs) — only if TD006 in plan
check "python3 -c \"
import json
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD006' not in plan:
    print('TD006_NOT_IN_PLAN: skip')
else:
    with open('tests/test_service.py') as f:
        src = f.read()
    real = [l for l in src.splitlines() if l.strip().startswith('def test_') and 'placeholder' not in l]
    assert len(real) >= 2, f'Only {len(real)} real test(s) — TD006 not fixed'
    print(f'TESTS_NOT_STUB_OK: {len(real)} real tests')
\"" "tests_still_stub"

# 15. pytest passes (only if TD006 in plan)
check "python3 -c \"
import json, subprocess, sys
with open('/tmp/_neg3_plan.json') as f:
    plan = json.load(f)
if 'TD006' not in plan:
    print('TD006_NOT_IN_PLAN: skip')
    sys.exit(0)
r = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-q', '--tb=short'],
                   capture_output=True, text=True)
out = r.stdout + r.stderr
print(out[-500:] if len(out) > 500 else out)
assert r.returncode == 0, 'pytest failed'
\"" "tests_fail"

# Partial scoring
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then SUCCESS=1; PASS=true; else SUCCESS=0; PASS=false; fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {"checks_passed": $PASSED, "checks_total": $CHECKS, "partial_score": $PARTIAL},
  "failure_modes": $FM
}
JSON
