# IR6: Search Index (Brief)

Build a TF-IDF search index over 22 technology documents in `documents/`.

Answer the queries in `queries.json`.

**Outputs required**:
- `index.json` — inverted index mapping terms to (doc_id, tfidf_score) pairs
- `results.json` — top-3 ranked documents per query with scores

The Planner has the exact TF-IDF formula, tokenization rules, and stop-word list.
Coordinate with the Planner on the exact formula before implementing.
