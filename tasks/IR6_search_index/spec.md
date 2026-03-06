# IR6: Search Index — TF-IDF Inverted Index

## Task Overview

Build an inverted index over 22 technology documents and implement
TF-IDF ranking to answer 5 search queries.

---

## Corpus

Documents are in `documents/*.txt`. Each file is a short text on a technology topic.
Filename (without `.txt`) is the document ID.

---

## Tokenization Rules (EXACT — deviations cause grader failures)

1. Lowercase all text.
2. Extract tokens using `[a-z]+` regex (letters only, no digits or punctuation).
3. Remove stop words (the, a, an, and, or, but, in, on, at, to, for, of, with,
   by, from, is, are, was, were, be, been, have, has, had, do, does, did,
   will, would, could, should, may, might, it, its, this, that, these, those,
   as, not, no, so, if, than, then, when, where, which, who, how, all, each).

---

## TF-IDF Formula

```
TF(term, doc)  = count(term in doc) / total_tokens_in_doc
IDF(term)      = log((N + 1) / (df(term) + 1)) + 1   [smoothed]
TF-IDF(term, doc) = TF * IDF
```

Where:
- `N` = total number of documents
- `df(term)` = number of documents containing the term
- Use natural log (`math.log`)

Score for a query is the SUM of TF-IDF scores for each query term in that document.

---

## Required Outputs

### index.json
```json
{
  "term1": {"doc_id": tf_idf_score, ...},
  "term2": {"doc_id": tf_idf_score, ...},
  ...
}
```

### results.json
```json
{
  "query_id": [
    {"doc_id": "name", "score": 0.234},
    {"doc_id": "name", "score": 0.198},
    {"doc_id": "name", "score": 0.145}
  ],
  ...
}
```

Each query result must include the top-3 ranked documents with scores.

---

## Queries

- `neural_network_search`: terms=["neural", "network", "deep", "learning"]
- `python_database`: terms=["python", "database", "sql"]
- `container_orchestration`: terms=["container", "orchestration", "kubernetes"]
- `api_security`: terms=["api", "security", "network"]
- `functional_algorithm`: terms=["functional", "algorithm", "graph"]

---

## Constraints

- `index.json` must have at least 20 unique terms as keys.
- Each result entry must have `doc_id` (string) and `score` (float) fields.
- Results for each query must be sorted descending by score.
- Verifier must produce `attestation.json` with `verdict="pass"`.
