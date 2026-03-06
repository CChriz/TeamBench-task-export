#!/usr/bin/env bash
# INC10_rollback_plan grader
set -euo pipefail

WORKSPACE="${1:-${WORKSPACE_DIR:-/workspace}}"
REPORTS="${2:-${REPORTS_DIR:-/reports}}"

source "$(dirname "$0")/../../harness/grader_helpers.sh"
init_grader 10
cd "${WORKSPACE}"

# Load expected values
EXPECTED="${WORKSPACE}/expected.json"

# ── C1: rollback_plan.json exists ──
check_file_exists "C1" "rollback_plan.json exists" "rollback_plan.json"

# ── C2: Plan is valid JSON with required structure ──
result=$(python3 -c "
import json
try:
    with open('rollback_plan.json') as f:
        plan = json.load(f)
    assert 'steps' in plan or 'rollback_steps' in plan or 'rollback_order' in plan
    print('pass')
except:
    print('fail')
" 2>/dev/null || echo "fail")
check "C2" "rollback plan is valid JSON with steps" "$result"

# ── C3: Correct rollback order respects dependencies ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('rollback_plan.json') as f:
    plan = json.load(f)

correct_order = exp.get('correct_rollback_order', [])
# Extract service names from plan steps
steps = plan.get('steps', plan.get('rollback_steps', plan.get('rollback_order', [])))
plan_services = []
for step in steps:
    if isinstance(step, str):
        plan_services.append(step)
    elif isinstance(step, dict):
        svc = step.get('service', step.get('name', step.get('target', '')))
        plan_services.append(svc)

# Check order matches
if plan_services == correct_order:
    print('pass')
else:
    print('fail')
" 2>/dev/null || echo "fail")
check "C3" "rollback order respects dependency graph" "$result"

# ── C4: All 3 services addressed ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('rollback_plan.json') as f:
    plan = json.load(f)

content = json.dumps(plan).lower()
svcs = [exp['svc_a'], exp['svc_b'], exp['svc_c']]
found = sum(1 for s in svcs if s.lower() in content)
print('pass' if found >= 3 else 'fail')
" 2>/dev/null || echo "fail")
check "C4" "all 3 services addressed in rollback plan" "$result"

# ── C5: Stable versions referenced ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('rollback_plan.json') as f:
    content = json.dumps(json.load(f))

stable = [exp.get('stable_ver_a',''), exp.get('stable_ver_b',''), exp.get('stable_ver_c','')]
found = sum(1 for v in stable if v and v in content)
print('pass' if found >= 2 else 'fail')
" 2>/dev/null || echo "fail")
check "C5" "stable versions referenced in plan" "$result"

# ── C6: Health check URLs included ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('rollback_plan.json') as f:
    content = json.dumps(json.load(f))

urls = [exp.get('health_url_a',''), exp.get('health_url_b',''), exp.get('health_url_c','')]
found = sum(1 for u in urls if u and u in content)
print('pass' if found >= 2 else 'fail')
" 2>/dev/null || echo "fail")
check "C6" "health check URLs included" "$result"

# ── C7: Rollback reason identified ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('rollback_plan.json') as f:
    content = json.dumps(json.load(f)).lower()

reason = exp.get('rollback_reason', '').lower()
print('pass' if reason and reason in content else 'fail')
" 2>/dev/null || echo "fail")
check "C7" "rollback reason identified" "$result"

# ── C8: No circular dependencies in plan ──
result=$(python3 -c "
import json
with open('rollback_plan.json') as f:
    plan = json.load(f)

steps = plan.get('steps', plan.get('rollback_steps', plan.get('rollback_order', [])))
services_seen = []
for step in steps:
    if isinstance(step, str):
        svc = step
    elif isinstance(step, dict):
        svc = step.get('service', step.get('name', ''))
    else:
        continue
    if svc in services_seen:
        print('fail')
        exit()
    services_seen.append(svc)
print('pass')
" 2>/dev/null || echo "fail")
check "C8" "no duplicate/circular steps in plan" "$result"

# ── C9: Plan has at least 3 steps ──
result=$(python3 -c "
import json
with open('rollback_plan.json') as f:
    plan = json.load(f)
steps = plan.get('steps', plan.get('rollback_steps', plan.get('rollback_order', [])))
print('pass' if len(steps) >= 3 else 'fail')
" 2>/dev/null || echo "fail")
check "C9" "plan has at least 3 steps" "$result"

# ── C10: Broken version identified ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('rollback_plan.json') as f:
    content = json.dumps(json.load(f))

broken = exp.get('broken_version', '')
print('pass' if broken and broken in content else 'fail')
" 2>/dev/null || echo "fail")
check "C10" "broken version identified in plan" "$result"

finalize_grader
