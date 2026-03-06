#!/usr/bin/env bash
# IR6_search_index grader
set -euo pipefail

WORKSPACE="${1:-${WORKSPACE_DIR:-/workspace}}"
REPORTS="${2:-${REPORTS_DIR:-/reports}}"

source "$(dirname "$0")/../../harness/grader_helpers.sh"
init_grader 10
cd "${WORKSPACE}"

# ── C1: search_index.json exists ──
check_file_exists "C1" "search_index.json exists" "search_index.json"

# ── C2: Index is valid JSON ──
result=$(python3 -c "
import json
try:
    with open('search_index.json') as f:
        idx = json.load(f)
    assert isinstance(idx, dict)
    print('pass')
except:
    print('fail')
" 2>/dev/null || echo "fail")
check "C2" "search index is valid JSON dict" "$result"

# ── C3: Index covers minimum number of terms ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('search_index.json') as f:
    idx = json.load(f)

min_terms = exp.get('min_index_terms', 50)
print('pass' if len(idx) >= min_terms else 'fail')
" 2>/dev/null || echo "fail")
check "C3" "index has sufficient terms" "$result"

# ── C4: search_results.json exists ──
check_file_exists "C4" "search_results.json exists" "search_results.json"

# ── C5: Search results valid JSON ──
result=$(python3 -c "
import json
try:
    with open('search_results.json') as f:
        results = json.load(f)
    assert isinstance(results, (dict, list))
    print('pass')
except:
    print('fail')
" 2>/dev/null || echo "fail")
check "C5" "search results is valid JSON" "$result"

# ── C6: All queries answered ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('search_results.json') as f:
    results = json.load(f)

queries = exp.get('queries', [])
if isinstance(results, dict):
    answered = len(results)
elif isinstance(results, list):
    answered = len(results)
else:
    answered = 0
print('pass' if answered >= len(queries) else 'fail')
" 2>/dev/null || echo "fail")
check "C6" "all queries have results" "$result"

# ── C7: Top results match expected for at least 50% of queries ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('search_results.json') as f:
    results = json.load(f)

computed = exp.get('computed_results', {})
matches = 0
total = 0
for qid, expected_docs in computed.items():
    total += 1
    if isinstance(results, dict) and qid in results:
        actual = results[qid]
        if isinstance(actual, list) and len(actual) > 0:
            # Check if top result matches
            top = actual[0]
            if isinstance(top, dict):
                top = top.get('doc', top.get('document', top.get('id', '')))
            if isinstance(expected_docs, list) and len(expected_docs) > 0:
                exp_top = expected_docs[0]
                if isinstance(exp_top, dict):
                    exp_top = exp_top.get('doc', exp_top.get('document', exp_top.get('id', '')))
                if str(top) == str(exp_top):
                    matches += 1
print('pass' if total > 0 and matches >= total * 0.5 else 'fail')
" 2>/dev/null || echo "fail")
check "C7" "top results match expected for >= 50% queries" "$result"

# ── C8: Results include relevance scores ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('search_results.json') as f:
    results = json.load(f)

score_field = exp.get('required_score_field', 'score')
if isinstance(results, dict):
    for qid, docs in results.items():
        if isinstance(docs, list) and len(docs) > 0:
            first = docs[0]
            if isinstance(first, dict) and score_field in first:
                print('pass')
                exit()
print('fail')
" 2>/dev/null || echo "fail")
check "C8" "results include relevance scores" "$result"

# ── C9: Scores are in descending order ──
result=$(python3 -c "
import json
with open('expected.json') as f:
    exp = json.load(f)
with open('search_results.json') as f:
    results = json.load(f)

score_field = exp.get('required_score_field', 'score')
sorted_ok = 0
checked = 0
if isinstance(results, dict):
    for qid, docs in results.items():
        if isinstance(docs, list) and len(docs) >= 2:
            checked += 1
            scores = []
            for d in docs:
                if isinstance(d, dict):
                    scores.append(float(d.get(score_field, 0)))
            if scores == sorted(scores, reverse=True):
                sorted_ok += 1
print('pass' if checked > 0 and sorted_ok >= checked * 0.8 else 'fail')
" 2>/dev/null || echo "fail")
check "C9" "scores in descending order" "$result"

# ── C10: Index covers all documents ──
result=$(python3 -c "
import json, os
with open('expected.json') as f:
    exp = json.load(f)

num_docs = exp.get('num_docs', 20)
# Check index references docs
with open('search_index.json') as f:
    idx = json.load(f)

# Count unique docs across all posting lists
all_docs = set()
for term, postings in idx.items():
    if isinstance(postings, list):
        for p in postings:
            if isinstance(p, dict):
                all_docs.add(p.get('doc', p.get('document', p.get('id', ''))))
            else:
                all_docs.add(str(p))
    elif isinstance(postings, dict):
        all_docs.update(postings.keys())

print('pass' if len(all_docs) >= num_docs * 0.8 else 'fail')
" 2>/dev/null || echo "fail")
check "C10" "index covers >= 80% of documents" "$result"

finalize_grader
