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

# 1. config.json is valid JSON
check "python3 -c \"
import json, sys
with open('config.json') as f:
    cfg = json.load(f)
assert isinstance(cfg, dict), 'config.json must be a JSON object'
print('CONFIG_VALID_JSON')
\"" "invalid_json"

# 2. config.json contains all required knobs
check "python3 -c \"
import json
with open('config.json') as f:
    cfg = json.load(f)
required = ['thread_pool_size', 'connection_pool_size', 'cache_size_mb',
            'batch_size', 'timeout_ms', 'gc_interval_sec']
missing = [k for k in required if k not in cfg]
assert not missing, 'Missing knobs: ' + str(missing)
print('CONFIG_KEYS_OK')
\"" "missing_config_knobs"

# 3. All knob values within valid ranges
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import validate_config
with open('config.json') as f:
    cfg = json.load(f)
errors = validate_config(cfg)
range_errors = [e for e in errors if 'Contradictory' not in e]
assert not range_errors, 'Range violations: ' + str(range_errors)
print('KNOB_RANGES_OK')
\"" "config_values_invalid"

# 4. No contradictory settings (thread_pool_size * batch_size <= 10000)
check "python3 -c \"
import json
with open('config.json') as f:
    cfg = json.load(f)
threads = cfg.get('thread_pool_size', 1)
batch   = cfg.get('batch_size', 1)
product = threads * batch
assert product <= 10000, 'Contradictory: thread_pool_size(' + str(threads) + ') * batch_size(' + str(batch) + ') = ' + str(product) + ' > 10000'
print('NO_CONTRADICTION_OK: ' + str(threads) + 'x' + str(batch) + '=' + str(product))
\"" "contradictory_settings"

# 5. CPU utilisation within target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, CPU_TARGET_PCT
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
cpu = m['cpu_pct']
assert cpu < CPU_TARGET_PCT, 'CPU=' + str(cpu) + '% exceeds target ' + str(CPU_TARGET_PCT) + '%'
print('CPU_OK: ' + str(cpu) + '%')
\"" "cpu_target_missed"

# 6. Memory utilisation within target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, MEMORY_TARGET_PCT
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
mem = m['memory_pct']
assert mem < MEMORY_TARGET_PCT, 'Memory=' + str(mem) + '% exceeds target ' + str(MEMORY_TARGET_PCT) + '%'
print('MEMORY_OK: ' + str(mem) + '%')
\"" "memory_target_missed"

# 7. p99 latency within target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, P99_TARGET_MS
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
p99 = m['p99_ms']
assert p99 < P99_TARGET_MS, 'p99=' + str(p99) + 'ms exceeds target ' + str(P99_TARGET_MS) + 'ms'
print('P99_OK: ' + str(p99) + 'ms')
\"" "p99_target_missed"

# 8. Throughput meets target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, THROUGHPUT_TARGET
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
tput = m['throughput_rps']
assert tput > THROUGHPUT_TARGET, 'Throughput=' + str(tput) + 'rps below target ' + str(THROUGHPUT_TARGET) + 'rps'
print('THROUGHPUT_OK: ' + str(tput) + 'rps')
\"" "throughput_target_missed"

# 9. Error rate within target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, ERROR_RATE_TARGET
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
err = m['error_rate_pct']
assert err < ERROR_RATE_TARGET, 'Error rate=' + str(err) + '% exceeds target ' + str(ERROR_RATE_TARGET) + '%'
print('ERROR_RATE_OK: ' + str(err) + '%')
\"" "error_rate_target_missed"

# 10. Weighted score above baseline (0.35)
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, _weighted_score, BASELINE_SCORE
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
score = _weighted_score(m)
assert score > BASELINE_SCORE, 'Score ' + str(score) + ' not above baseline ' + str(BASELINE_SCORE)
print('SCORE_OK: ' + str(score))
\"" "score_below_baseline"

# 11. Simulator confirms improvement over baseline in at least one metric
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_metrics, BASELINE_CPU_PCT, BASELINE_MEMORY_PCT, \
    BASELINE_P99_MS, BASELINE_THROUGHPUT, BASELINE_ERROR_RATE
with open('config.json') as f:
    cfg = json.load(f)
m = compute_metrics(cfg)
improved = (
    m['cpu_pct']        < BASELINE_CPU_PCT      or
    m['memory_pct']     < BASELINE_MEMORY_PCT    or
    m['p99_ms']         < BASELINE_P99_MS        or
    m['throughput_rps'] > BASELINE_THROUGHPUT    or
    m['error_rate_pct'] < BASELINE_ERROR_RATE
)
assert improved, 'No metric improved over the bad baseline config'
print('IMPROVEMENT_CONFIRMED')
\"" "no_improvement_over_baseline"

# 12. target.json is present and readable
check "python3 -c \"
import json
with open('target.json') as f:
    t = json.load(f)
assert 'performance_budget' in t, 'target.json missing performance_budget'
assert 'scoring_weights' in t, 'target.json missing scoring_weights'
print('TARGET_JSON_OK')
\"" "target_json_missing"

# 13. All checks pass simultaneously via simulator --check
check "python3 simulator.py --check" "simulator_check_fail"

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
