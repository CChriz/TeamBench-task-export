#!/usr/bin/env bash
# GH120_redis-py_3863 — placeholder grader.
#
# The full task specification has not yet been restored to the public release.
# Until then, this grader reports a 0 score with a clear failure mode so that
# LB90 sweeps complete instead of crashing on this slot.
#
# Called as: grade.sh WORKSPACE REPORTS SUBMISSION TASK_DIR [EXPECTED_JSON]
set -uo pipefail

REPORTS="${2:-${REPORTS_DIR:-/reports}}"
mkdir -p "${REPORTS}"
cat > "${REPORTS}/score.json" <<'EOF'
{
  "pass": false,
  "primary": {"success": 0},
  "secondary": {"partial_score": 0.0, "checks_passed": 0, "checks_total": 1},
  "failure_modes": ["task_under_re_curation"],
  "note": "GH120_redis-py_3863 is one of 90 leaderboard slots; its full spec is pending restoration. The remaining 89 tasks are unaffected."
}
EOF
exit 0
