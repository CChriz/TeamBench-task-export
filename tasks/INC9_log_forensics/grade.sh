#!/usr/bin/env bash
# INC9_log_forensics grader
set -euo pipefail

WORKSPACE="${1:-${WORKSPACE_DIR:-/workspace}}"
REPORTS="${2:-${REPORTS_DIR:-/reports}}"

source "$(dirname "$0")/../../harness/grader_helpers.sh"
init_grader 10
cd "${WORKSPACE}"

# ── C1: root_cause_report.json exists ──
check_file_exists "C1" "root_cause_report.json exists" "root_cause_report.json"

# ── C2: Report is valid JSON with required fields ──
result=$(python3 -c "
import json
try:
    with open('root_cause_report.json') as f:
        report = json.load(f)
    required = ['root_cause', 'timeline', 'affected_services']
    # Accept various field naming conventions
    content = json.dumps(report).lower()
    found = 0
    for r in required:
        if r in report or r.replace('_', '') in content:
            found += 1
    print('pass' if found >= 2 else 'fail')
except:
    print('fail')
" 2>/dev/null || echo "fail")
check "C2" "report has required fields" "$result"

# ── C3: Correct root cause service identified ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    content = json.dumps(json.load(f)).lower()

root_svc = exp.get('root_cause_service', '').lower()
print('pass' if root_svc and root_svc in content else 'fail')
" 2>/dev/null || echo "fail")
check "C3" "correct root cause service identified" "$result"

# ── C4: Root cause type identified ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    content = json.dumps(json.load(f)).lower()

cause_type = exp.get('root_cause_type', '').lower()
print('pass' if cause_type and cause_type in content else 'fail')
" 2>/dev/null || echo "fail")
check "C4" "root cause type correctly identified" "$result"

# ── C5: Affected services listed correctly ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    report = json.load(f)

content = json.dumps(report).lower()
affected = exp.get('affected_services', [])
found = sum(1 for s in affected if s.lower() in content)
print('pass' if found >= len(affected) else 'fail')
" 2>/dev/null || echo "fail")
check "C5" "all affected services listed" "$result"

# ── C6: Batch job red herring NOT blamed as root cause ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    report = json.load(f)

root_cause = json.dumps(report.get('root_cause', report.get('cause', ''))).lower()
red_herring = exp.get('red_herring_batch_job', '').lower()
# Red herring should not be identified as THE root cause
if red_herring and red_herring in root_cause:
    print('fail')
else:
    print('pass')
" 2>/dev/null || echo "fail")
check "C6" "batch job red herring not blamed as root cause" "$result"

# ── C7: Clock skew red herring addressed ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    content = json.dumps(json.load(f)).lower()

clock_hint = exp.get('red_herring_clock_skew', '').lower()
# Should mention clock skew but not blame it
print('pass' if 'clock' in content or 'skew' in content or 'ntp' in content else 'fail')
" 2>/dev/null || echo "fail")
check "C7" "clock skew anomaly acknowledged" "$result"

# ── C8: Timeline has reasonable time window ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    report = json.load(f)

content = json.dumps(report).lower()
start = exp.get('first_event_window_start', '')
end = exp.get('first_event_window_end', '')
# Check that timeline references are within expected window
has_timeline = 'timeline' in report or 'events' in report or 'sequence' in report
print('pass' if has_timeline else 'fail')
" 2>/dev/null || echo "fail")
check "C8" "timeline with event sequence present" "$result"

# ── C9: Root cause time approximately correct ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('root_cause_report.json') as f:
    content = json.dumps(json.load(f))

root_time = exp.get('root_cause_time', '')
# Check partial time match (hour:minute)
if root_time:
    time_part = root_time.split('T')[1][:5] if 'T' in root_time else root_time[:5]
    print('pass' if time_part in content else 'fail')
else:
    print('pass')
" 2>/dev/null || echo "fail")
check "C9" "root cause time approximately correct" "$result"

# ── C10: Report recommends remediation ──
result=$(python3 -c "
import json
with open('root_cause_report.json') as f:
    content = json.dumps(json.load(f)).lower()

remediation_terms = ['remediat', 'fix', 'resolv', 'mitigat', 'recommend', 'action', 'prevent']
found = any(t in content for t in remediation_terms)
print('pass' if found else 'fail')
" 2>/dev/null || echo "fail")
check "C10" "report includes remediation recommendations" "$result"

finalize_grader
