# IR5: Search Ranking Fix (TF-IDF)

## Goal
Fix a TF-IDF search engine (`search.py`) that has 3 bugs in its scoring algorithm.
After fixes, the engine must return correct ranked results for test queries.

## Hard Requirements

### Scoring Bugs
1. **Wrong IDF formula**: Currently uses `log(N / df)`. Correct formula is `log((N + 1) / (df + 1)) + 1` (smoothed IDF to avoid division by zero and zero scores).
2. **Missing length normalization**: Scores are not normalized by document length. Divide the TF-IDF score by the number of tokens in the document.
3. **Broken tie-breaking**: When two documents have the same score, they should be ordered by document ID ascending. Currently no tie-breaking (order is arbitrary).

### Functional Requirements
4. Run: `python search.py --query "QUERY"` prints ranked results as JSON.
5. The search index is built from `corpus/*.txt` files.
6. Queries are case-insensitive and use whitespace tokenization.
7. Results include `doc_id`, `score` (rounded to 4 decimal places), and `title`.
8. Top-K is 10 (return at most 10 results).

## Deliverables
- Fixed `search.py`
- Verifier confirms correct ranking for test queries.
