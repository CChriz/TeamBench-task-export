"""
Parameterized generator for IR5: Search Ranking Fix (TF-IDF).

Each seed produces:
  - Different corpus topic (programming, databases, security)
  - A buggy search.py with 3 scoring bugs
  - Expected rankings computed with the correct formula
  - Seed-specific spec.md and brief.md (inline, no disk reads)
"""
from __future__ import annotations

import json
import math
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

TOPICS = [
    {
        "name": "programming_languages",
        "docs": [
            ("doc1", "Python Programming", "python is a popular programming language python is used for web development and data science python has many libraries"),
            ("doc2", "Java Development", "java is a statically typed programming language java is used for enterprise applications and android development"),
            ("doc3", "Web Development", "web development involves html css and javascript python and java are also used for web development frameworks"),
            ("doc4", "Data Science", "data science uses python and r for statistical analysis machine learning and data visualization are key areas"),
            ("doc5", "Machine Learning", "machine learning is a subset of artificial intelligence python libraries like scikit learn and tensorflow are popular"),
            ("doc6", "Cloud Computing", "cloud computing provides scalable infrastructure aws azure and gcp are major cloud providers"),
        ],
        "queries": [
            "python programming",
            "web development",
            "machine learning data",
        ],
        "tiebreak_query": "programming language",
    },
    {
        "name": "databases",
        "docs": [
            ("doc1", "Database Design", "database design involves normalization indexing and query optimization sql databases use structured query language"),
            ("doc2", "NoSQL Databases", "nosql databases like mongodb and cassandra handle unstructured data nosql is popular for scalable applications"),
            ("doc3", "SQL Queries", "sql queries retrieve data from relational databases joins aggregations and subqueries are common sql operations"),
            ("doc4", "Data Modeling", "data modeling defines the structure of a database entity relationship diagrams help visualize data models"),
            ("doc5", "Query Optimization", "query optimization improves database performance indexing and query planning are key optimization techniques"),
            ("doc6", "Data Warehousing", "data warehousing combines data from multiple sources for analysis olap cubes and star schemas are common"),
        ],
        "queries": [
            "sql database",
            "data modeling",
            "query optimization indexing",
        ],
        "tiebreak_query": "database query",
    },
    {
        "name": "security",
        "docs": [
            ("doc1", "Network Security", "network security protects against cyber threats firewalls intrusion detection and encryption are essential security measures"),
            ("doc2", "Cryptography", "cryptography uses mathematical algorithms for encryption symmetric and asymmetric encryption protect data in transit"),
            ("doc3", "Authentication", "authentication verifies user identity passwords biometrics and multi factor authentication improve security"),
            ("doc4", "Web Security", "web security prevents attacks like xss csrf and sql injection input validation and output encoding are key defenses"),
            ("doc5", "Penetration Testing", "penetration testing identifies security vulnerabilities ethical hackers simulate attacks to test security defenses"),
            ("doc6", "Security Compliance", "security compliance ensures adherence to standards like gdpr hipaa and pci dss regular audits verify compliance"),
        ],
        "queries": [
            "security encryption",
            "web attacks sql injection",
            "authentication identity",
        ],
        "tiebreak_query": "security measures",
    },
]


class Generator(TaskGenerator):
    task_id = "IR5_search_ranking"
    domain = "information_retrieval"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        topic = TOPICS[seed % len(TOPICS)]
        docs = topic["docs"]

        # Compute correct expected rankings using the correct TF-IDF formula
        query_tests = []
        for query in topic["queries"]:
            ranked = self._correct_ranking(docs, query)
            query_tests.append({
                "query": query,
                "expected_top3": ranked[:3],
                "expected_order": ranked,
            })

        workspace_files: dict[str, str] = {}
        workspace_files["search.py"] = self._buggy_search()
        for doc_id, title, content in docs:
            workspace_files[f"corpus/{doc_id}.txt"] = f"{title}\n\n{content}\n"
        workspace_files["tests/test_search.py"] = self._test_file(topic["queries"], query_tests)

        expected = {
            "topic": topic["name"],
            "query_tests": query_tests,
            "tiebreak_query": topic["tiebreak_query"],
            "doc_count": len(docs),
            "bugs": [
                "wrong_idf_formula",
                "missing_length_normalization",
                "no_tiebreak_by_doc_id",
            ],
            "correct_idf_formula": "log((N+1)/(df+1)) + 1",
            "normalization": "divide_score_by_doc_length",
            "tiebreak": "doc_id_ascending",
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._spec(),
            brief_md=self._brief(),
            expected=expected,
            workspace_files=workspace_files,
        )

    def _correct_ranking(self, docs: list, query: str) -> list[str]:
        """Correct TF-IDF: smoothed IDF + length normalization + tiebreak by doc_id."""
        N = len(docs)
        tokens_per_doc: dict[str, list[str]] = {}
        for doc_id, title, content in docs:
            tokens_per_doc[doc_id] = (title.lower() + " " + content.lower()).split()

        query_terms = query.lower().split()

        df: dict[str, int] = {}
        for term in query_terms:
            df[term] = sum(
                1 for doc_id, _, _ in docs if term in tokens_per_doc[doc_id]
            )

        scores: dict[str, float] = {}
        for doc_id, title, content in docs:
            tokens = tokens_per_doc[doc_id]
            doc_len = len(tokens) or 1
            score = 0.0
            for term in query_terms:
                tf = tokens.count(term)
                idf = math.log((N + 1) / (df.get(term, 0) + 1)) + 1
                score += tf * idf
            scores[doc_id] = round(score / doc_len, 4)

        return sorted(scores.keys(), key=lambda d: (-scores[d], d))

    def _buggy_search(self) -> str:
        return '''\
"""TF-IDF Search Engine.

Bugs to fix:
  BUG1: Wrong IDF formula — must be log((N+1)/(df+1)) + 1 (smoothed)
  BUG2: No length normalization — divide score by number of tokens in document
  BUG3: No tie-breaking by doc_id — sort by (-score, doc_id) for determinism
"""
import argparse
import json
import math
import os


def load_corpus(corpus_dir: str = "corpus") -> dict:
    """Load all .txt files from the corpus directory."""
    docs = {}
    for fname in sorted(os.listdir(corpus_dir)):
        if fname.endswith(".txt"):
            doc_id = fname.replace(".txt", "")
            with open(os.path.join(corpus_dir, fname), encoding="utf-8") as f:
                lines = f.readlines()
            title = lines[0].strip() if lines else doc_id
            content = " ".join(line.strip() for line in lines[1:] if line.strip())
            docs[doc_id] = {"title": title, "content": content}
    return docs


def tokenize(text: str) -> list[str]:
    """Whitespace tokenization, lowercase."""
    return text.lower().split()


def compute_tfidf(docs: dict, query_terms: list[str]) -> list[dict]:
    """Compute TF-IDF scores for each document and return ranked results."""
    N = len(docs)

    # Compute document frequencies
    df: dict[str, int] = {}
    for term in set(query_terms):
        count = 0
        for doc_id, doc in docs.items():
            tokens = tokenize(doc["title"] + " " + doc["content"])
            if term in tokens:
                count += 1
        df[term] = count

    results = []
    for doc_id, doc in docs.items():
        tokens = tokenize(doc["title"] + " " + doc["content"])
        score = 0.0

        for term in query_terms:
            tf = tokens.count(term)
            # BUG1: should be log((N+1)/(df+1)) + 1
            idf = math.log(N / df[term]) if df.get(term, 0) > 0 else 0
            score += tf * idf

        # BUG2: missing length normalization — divide by len(tokens)

        results.append({
            "doc_id": doc_id,
            "title": doc["title"],
            "score": round(score, 4),
        })

    # BUG3: no tie-breaking — should sort by (-score, doc_id)
    results.sort(key=lambda r: -r["score"])

    return results[:10]


def main() -> None:
    parser = argparse.ArgumentParser(description="TF-IDF Search Engine")
    parser.add_argument("--query", required=True, help="Search query string")
    parser.add_argument("--corpus", default="corpus", help="Corpus directory path")
    args = parser.parse_args()

    docs = load_corpus(args.corpus)
    query_terms = tokenize(args.query)
    results = compute_tfidf(docs, query_terms)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
'''

    def _test_file(self, queries: list[str], query_tests: list[dict]) -> str:
        first_q = query_tests[0]
        top1 = first_q["expected_top3"][0] if first_q["expected_top3"] else "doc1"
        q0 = repr(queries[0])
        qlast = repr(queries[-1])
        top1_r = repr(top1)
        return f'''\
"""Tests for the TF-IDF search engine."""
import json
import subprocess
import sys


def _search(query: str) -> list[dict]:
    result = subprocess.run(
        [sys.executable, "search.py", "--query", query],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"search.py failed:\\n{{result.stderr}}"
    return json.loads(result.stdout)


def test_returns_results():
    results = _search({q0})
    assert len(results) > 0, "No results returned"
    for r in results:
        assert "doc_id" in r
        assert "score" in r
        assert "title" in r


def test_top_result_correct():
    """Top result for the first test query must be {top1}."""
    results = _search({q0})
    assert results[0]["doc_id"] == {top1_r}, (
        f"Expected top doc_id {{results[0][\'doc_id\']!r}} == {top1_r}"
    )


def test_scores_are_floats():
    results = _search({q0})
    for r in results:
        assert isinstance(r["score"], float), f"score must be float, got {{type(r[\'score\']).__name__}}"


def test_tiebreak_deterministic():
    """Running the same query twice must give identical results."""
    r1 = _search({qlast})
    r2 = _search({qlast})
    assert [r["doc_id"] for r in r1] == [r["doc_id"] for r in r2], "Non-deterministic results"


if __name__ == "__main__":
    test_returns_results()
    test_top_result_correct()
    test_scores_are_floats()
    test_tiebreak_deterministic()
    print("All tests passed.")
'''

    def _spec(self) -> str:
        return """\
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
"""

    def _brief(self) -> str:
        return """\
# IR5: Search Ranking Fix (Brief)

Fix the TF-IDF search engine in `search.py`. There are 3 scoring bugs:
wrong IDF formula, missing length normalization, no tie-breaking by doc_id.
Run: `python search.py --query "YOUR QUERY"`
"""
