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

# ── Locate python ───────────────────────────────────────────────────────────
if [ -x "<HOME>/TeamBench/venv/bin/python" ]; then
  PYTHON="<HOME>/TeamBench/venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

export PYTHONPATH="$WORKSPACE${PYTHONPATH:+:$PYTHONPATH}"

# ── Load seed-specific expected values ─────────────────────────────────────
EXPECTED_JSON="$REPORTS/expected.json"

APP_NAME=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['app_name'])")
PORT=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['port'])")
RES_A=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['resources'][0])")
RES_B=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['resources'][1])")
RES_C=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['resources'][2])")
TTL_A=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['ttl_a'])")
TTL_B=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['ttl_b'])")
UNCACHEABLE=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['uncacheable_resource'])")
KEY_FORMAT=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['cache_key_format'])")
CACHE_PREFIX=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['cache_prefix'])")
CACHEABLE_JSON=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(json.dumps(d['cacheable_resources'], separators=(',',':')))")
CACHE_KEYS_JSON=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(json.dumps(d['cache_keys'], separators=(',',':')))")
INV_RULES_JSON=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(json.dumps(d['invalidation_rules'], separators=(',',':')))")
# First and second cacheable resource (plain strings, safe for shell substitution)
CACHEABLE_FIRST=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['cacheable_resources'][0])")
CACHEABLE_SECOND=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d['cacheable_resources'][1])")
# TTLs for each cacheable resource
TTL_FIRST=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); r=d['cacheable_resources'][0]; print(d['ttl_map'][r])")
TTL_SECOND=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); r=d['cacheable_resources'][1]; print(d['ttl_map'][r])")

# Export JSON vars so Python can read them via os.environ (avoids shell glob expansion of brackets)
export CACHEABLE_JSON CACHE_KEYS_JSON INV_RULES_JSON

cd "$WORKSPACE"

# ── CHECK 1: cache.py exists and Cache class is importable ─────────────────
check "$PYTHON -c \"
import sys
sys.path.insert(0, '$WORKSPACE')
from cache import Cache, cache
assert callable(getattr(Cache, 'set', None)), 'Cache.set missing'
assert callable(getattr(Cache, 'get', None)), 'Cache.get missing'
assert callable(getattr(Cache, 'delete', None)), 'Cache.delete missing'
assert callable(getattr(Cache, 'delete_pattern', None)), 'Cache.delete_pattern missing'
assert callable(getattr(Cache, 'clear', None)), 'Cache.clear missing'
print('CACHE_CLASS_OK')
\"" "cache_class_missing_or_incomplete"

# ── CHECK 2: Cache basic set/get works with TTL ────────────────────────────
check "$PYTHON -c \"
import sys, time
sys.path.insert(0, '$WORKSPACE')
from cache import Cache
c = Cache()
c.set('k', 'v', ttl_seconds=5)
assert c.get('k') == 'v', 'get() did not return stored value'
print('CACHE_SET_GET_OK')
\"" "cache_set_get_broken"

# ── CHECK 3: Cache respects TTL expiry ─────────────────────────────────────
check "$PYTHON -c \"
import sys, time
sys.path.insert(0, '$WORKSPACE')
from cache import Cache
c = Cache()
c.set('expiring_key', 'val', ttl_seconds=1)
assert c.get('expiring_key') == 'val', 'value missing before expiry'
time.sleep(1.1)
result = c.get('expiring_key')
assert result is None, f'Expected None after TTL, got {result!r}'
print('CACHE_TTL_EXPIRY_OK')
\"" "cache_ttl_not_enforced"

# ── CHECK 4: Cache delete_pattern with wildcard ────────────────────────────
check "$PYTHON -c \"
import sys
sys.path.insert(0, '$WORKSPACE')
from cache import Cache
c = Cache()
c.set('$RES_A:all', [1,2,3], 300)
c.set('$RES_A:42',  {'id':42}, 300)
c.set('$RES_B:all', [4,5,6], 300)
deleted = c.delete_pattern('$RES_A:*')
assert c.get('$RES_A:all') is None, '$RES_A:all should be deleted'
assert c.get('$RES_A:42') is None, '$RES_A:42 should be deleted'
assert c.get('$RES_B:all') is not None, '$RES_B:all should survive'
print('CACHE_DELETE_PATTERN_OK')
\"" "cache_delete_pattern_broken"

# ── CHECK 5: app.py imports and uses cache module ─────────────────────────
check "$PYTHON -c \"
import ast, sys
src = open('$WORKSPACE/app.py').read()
tree = ast.parse(src)
imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports += [a.name for a in node.names]
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.append(node.module)
assert any('cache' in imp for imp in imports), f'app.py does not import cache module; imports={imports}'
print('APP_IMPORTS_CACHE_OK')
\"" "app_does_not_import_cache"

# ── CHECK 6: Cacheable GET endpoints return source=cache on second call ────
check "$PYTHON -c \"
import sys, json, time, os
sys.path.insert(0, '$WORKSPACE')

from app import app
client = app.test_client()

cacheable = json.loads(os.environ['CACHEABLE_JSON'])
for resource in cacheable:
    r1 = client.get(f'/{resource}')
    assert r1.status_code == 200, f'GET /{resource} returned {r1.status_code}'
    r2 = client.get(f'/{resource}')
    assert r2.status_code == 200
    d2 = json.loads(r2.data)
    assert d2.get('source') == 'cache', f'GET /{resource} second call source={d2.get(\\\"source\\\")!r}, expected cache'
print('CACHEABLE_ENDPOINTS_CACHED_OK')
\"" "cacheable_endpoints_not_cached"

# ── CHECK 7: Uncacheable endpoint never returns source=cache ───────────────
check "$PYTHON -c \"
import sys, json
sys.path.insert(0, '$WORKSPACE')
from app import app
client = app.test_client()

# Call three times; source must never be 'cache'
for _ in range(3):
    r = client.get('/$UNCACHEABLE')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d.get('source') != 'cache', f'/$UNCACHEABLE returned source=cache (must not be cached)'
print('UNCACHEABLE_ENDPOINT_NOT_CACHED_OK')
\"" "uncacheable_endpoint_is_cached"

# ── CHECK 8: Cache hit is faster than DB call ──────────────────────────────
check "$PYTHON -c \"
import sys, json, time
sys.path.insert(0, '$WORKSPACE')
from cache import Cache
c = Cache()

# Simulate miss vs hit latency
import time
c.set('speed_test', {'data': [1,2,3]}, 300)
t0 = time.perf_counter()
for _ in range(10):
    v = c.get('speed_test')
t1 = time.perf_counter()
cache_ms = (t1 - t0) * 1000 / 10

# 10 cache hits should take < 50 ms total (< 5ms each)
assert cache_ms < 5, f'Cache get() took {cache_ms:.2f}ms avg — too slow'
print(f'CACHE_SPEED_OK ({cache_ms:.3f}ms avg)')
\"" "cache_too_slow"

# ── CHECK 9: POST to cacheable resource invalidates its cache ──────────────
check "$PYTHON -c \"
import sys, json
sys.path.insert(0, '$WORKSPACE')
from app import app
client = app.test_client()

res = '$CACHEABLE_FIRST'
# Prime the cache
r1 = client.get(f'/{res}')
assert r1.status_code == 200
# Verify it is cached
r2 = client.get(f'/{res}')
d2 = json.loads(r2.data)
assert d2.get('source') == 'cache', f'Cache was not primed for /{res}'

# POST to invalidate
new_item = {'name': 'NewItem', 'value': 999}
rpost = client.post(f'/{res}', data=json.dumps(new_item), content_type='application/json')
assert rpost.status_code == 201, f'POST /{res} returned {rpost.status_code}'

# Next GET must hit DB (cache was invalidated)
r3 = client.get(f'/{res}')
d3 = json.loads(r3.data)
assert d3.get('source') == 'db', f'Expected source=db after POST invalidation, got {d3.get(\\\"source\\\")!r}'
print('POST_INVALIDATES_CACHE_OK')
\"" "post_does_not_invalidate_cache"

# ── CHECK 10: PUT to res_a invalidates cache if res_a is cacheable ─────────
# The stub always provides PUT /$RES_A/{id}. If res_a is the uncacheable
# resource, there is no cache to invalidate — the check passes trivially.
check "$PYTHON -c \"
import sys, json, os
sys.path.insert(0, '$WORKSPACE')
from app import app
client = app.test_client()

res_a = '$RES_A'
uncacheable = '$UNCACHEABLE'
if res_a == uncacheable:
    print('PUT_INVALIDATES_CACHE_OK (res_a is uncacheable, skip)')
else:
    # Prime cache
    client.get(f'/{res_a}')
    r2 = client.get(f'/{res_a}')
    d2 = json.loads(r2.data)
    assert d2.get('source') == 'cache', f'Cache not primed for PUT test on /{res_a}'
    # PUT to update item 1
    rput = client.put(f'/{res_a}/1', data=json.dumps({'value': 777}), content_type='application/json')
    assert rput.status_code == 200, f'PUT /{res_a}/1 returned {rput.status_code}'
    # Next GET must hit DB
    r3 = client.get(f'/{res_a}')
    d3 = json.loads(r3.data)
    assert d3.get('source') == 'db', f'Expected source=db after PUT invalidation, got {d3.get(\\\"source\\\")!r}'
    print('PUT_INVALIDATES_CACHE_OK')
\"" "put_does_not_invalidate_cache"

# ── CHECK 11: After POST, fresh data is returned (no stale cache) ──────────
check "$PYTHON -c \"
import sys, json
sys.path.insert(0, '$WORKSPACE')
from app import app
client = app.test_client()

res = '$CACHEABLE_SECOND'
# Prime
client.get(f'/{res}')
client.get(f'/{res}')  # now cached

# Write new item
new_item = {'name': 'FreshItem', 'value': 42}
rpost = client.post(f'/{res}', data=json.dumps(new_item), content_type='application/json')
assert rpost.status_code == 201

# Read again — must include new item in data
r3 = client.get(f'/{res}')
d3 = json.loads(r3.data)
names = [item.get('name') for item in d3.get('data', [])]
assert 'FreshItem' in names, f'Stale cache: new item not in response after POST. names={names}'
print('NO_STALE_DATA_AFTER_WRITE_OK')
\"" "stale_data_after_write"

# ── CHECK 12: TTL values are correct in app source (cacheable resources only) ──
check "$PYTHON -c \"
src = open('$WORKSPACE/app.py').read()
ttl_first = '$TTL_FIRST'
ttl_second = '$TTL_SECOND'
assert ttl_first in src, f'TTL {ttl_first} for $CACHEABLE_FIRST not found in app.py'
assert ttl_second in src, f'TTL {ttl_second} for $CACHEABLE_SECOND not found in app.py'
print('TTL_VALUES_CORRECT_OK')
\"" "ttl_values_wrong"

# ── CHECK 13: Health endpoint still works (no regressions) ─────────────────
check "$PYTHON -c \"
import sys, json
sys.path.insert(0, '$WORKSPACE')
from app import app
client = app.test_client()
r = client.get('/health')
assert r.status_code == 200
d = json.loads(r.data)
assert d.get('status') == 'ok', f'health status={d.get(\"status\")!r}'
print('HEALTH_ENDPOINT_OK')
\"" "health_endpoint_broken"

# ── Score ──────────────────────────────────────────────────────────────────
PARTIAL=$($PYTHON -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then SUCCESS=1; PASS=true; else SUCCESS=0; PASS=false; fi
FM=$($PYTHON -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {"checks_passed": $PASSED, "checks_total": $CHECKS, "partial_score": $PARTIAL},
  "failure_modes": $FM
}
JSON
