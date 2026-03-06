"""
Parameterized generator for IR8: Search Index.

Each seed produces:
  - Different document corpus
  - Different stopword sets
  - Same 4 bug types: no hyphen splitting, no stopword removal,
    broken phrase queries, wrong BM25 k1

The 4 bugs are always:
  1. Tokenizer splits only on whitespace (not hyphens)
  2. STOPWORDS set exists but is never applied
  3. Phrase queries do boolean OR instead of positional match
  4. BM25 k1=0.0 (ignores term frequency)
"""
from __future__ import annotations

import os

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOC_SETS = [
    [
        (1, "machine learning is a state-of-the-art approach to artificial intelligence"),
        (2, "deep learning models require large-scale training data"),
        (3, "the state of machine learning research is rapidly advancing"),
        (4, "learning about machines and their applications"),
        (5, "artificial intelligence and machine learning go hand-in-hand"),
    ],
    [
        (1, "natural language processing uses state-of-the-art transformers"),
        (2, "the transformer architecture revolutionized language understanding"),
        (3, "language models are pre-trained on large-scale corpora"),
        (4, "processing natural resources requires careful planning"),
        (5, "natural language generation is a sub-field of NLP"),
    ],
    [
        (1, "computer vision is a well-known field of artificial intelligence"),
        (2, "image recognition uses state-of-the-art neural networks"),
        (3, "the vision of autonomous driving relies on computer vision"),
        (4, "well known algorithms include SIFT and SURF for feature detection"),
        (5, "computer graphics and computer vision are related fields"),
    ],
]

STOPWORD_SETS = [
    {"the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "and", "for", "on", "with"},
    {"the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "and", "for", "it", "at"},
    {"the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "and", "by", "that", "this"},
]


class Generator(TaskGenerator):
    task_id = "IR8_search_index"
    domain = "information_retrieval"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        docs = DOC_SETS[seed % len(DOC_SETS)]
        stopwords = STOPWORD_SETS[seed % len(STOPWORD_SETS)]

        workspace_files = {
            "search_engine.py": self._gen_engine(docs, stopwords),
            "test_search.py": self._gen_tests(docs, stopwords),
        }

        expected = {
            "seed": seed,
            "doc_count": len(docs),
            "stopwords": sorted(stopwords),
            "bugs": [
                "tokenizer does not split on hyphens",
                "STOPWORDS defined but never applied",
                "phrase queries use boolean OR instead of positional match",
                "BM25 k1=0.0 ignores term frequency",
            ],
        }

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Information Retrieval"},
        )

    def _gen_engine(self, docs, stopwords):
        stopwords_repr = ", ".join(f'"{w}"' for w in sorted(stopwords))
        docs_repr = "\n".join(
            f'    ({doc_id}, "{text}"),'
            for doc_id, text in docs
        )
        return f'''"""Inverted index search engine with BM25 scoring."""
import math
import re
from collections import defaultdict

STOPWORDS = {{{stopwords_repr}}}

CORPUS = [
{docs_repr}
]


def tokenize(text):
    """Tokenize text into lowercase words.

    BUG: Only splits on whitespace. Does not handle hyphens.
    BUG: Does not remove stopwords.
    """
    text = text.lower()
    tokens = text.split()
    # STOPWORDS is defined above but never used here
    return tokens


class SearchEngine:
    """Simple inverted index with BM25 scoring."""

    def __init__(self):
        self.documents = {{}}
        self.index = defaultdict(list)
        self.doc_lengths = {{}}
        self.avg_doc_length = 0
        self.doc_count = 0

    def add_document(self, doc_id, text):
        """Index a document."""
        self.documents[doc_id] = text
        tokens = tokenize(text)
        self.doc_lengths[doc_id] = len(tokens)
        self.doc_count += 1

        for pos, token in enumerate(tokens):
            self.index[token].append((doc_id, pos))

        total = sum(self.doc_lengths.values())
        self.avg_doc_length = total / self.doc_count if self.doc_count else 0

    def search(self, query):
        """Search for documents matching the query.

        Supports phrase queries with double quotes.
        Returns list of (doc_id, score) sorted by score descending.
        """
        if not query or not query.strip():
            return []

        phrase_match = re.match(r\'^"(.+)"$\', query.strip())
        if phrase_match:
            phrase = phrase_match.group(1)
            return self._phrase_search(phrase)

        tokens = tokenize(query)
        if not tokens:
            return []
        return self._bm25_search(tokens)

    def _phrase_search(self, phrase):
        """Search for exact phrase.

        BUG: Does boolean OR instead of checking consecutive positions.
        """
        tokens = tokenize(phrase)
        if not tokens:
            return []

        matching_docs = set()
        for token in tokens:
            for doc_id, pos in self.index.get(token, []):
                matching_docs.add(doc_id)

        return [(doc_id, 1.0) for doc_id in sorted(matching_docs)]

    def _bm25_search(self, query_tokens):
        """BM25 scoring.

        BUG: k1=0.0 means term frequency is ignored.
        """
        k1 = 0.0
        b = 0.75
        scores = defaultdict(float)

        for token in query_tokens:
            postings = self.index.get(token, [])
            if not postings:
                continue
            doc_ids_with_term = set(doc_id for doc_id, _ in postings)
            df = len(doc_ids_with_term)
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id in doc_ids_with_term:
                tf = sum(1 for did, _ in postings if did == doc_id)
                dl = self.doc_lengths.get(doc_id, 0)
                avgdl = self.avg_doc_length if self.avg_doc_length > 0 else 1
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * dl / avgdl)
                if denominator == 0:
                    denominator = 1
                scores[doc_id] += idf * numerator / denominator

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def build_index():
    """Build index from built-in corpus."""
    engine = SearchEngine()
    for doc_id, text in CORPUS:
        engine.add_document(doc_id, text)
    return engine
'''

    def _gen_tests(self, docs, stopwords):
        phrase_doc = docs[0]
        return f'''"""
Test suite for IR8_search_index. Do NOT modify.
"""
import unittest


class SearchTestCase(unittest.TestCase):

    def _build(self):
        from search_engine import SearchEngine
        engine = SearchEngine()
        corpus = [
{chr(10).join(f'            ({d[0]}, "{d[1]}"),' for d in docs)}
        ]
        for doc_id, text in corpus:
            engine.add_document(doc_id, text)
        return engine

    def test_import(self):
        from search_engine import SearchEngine, tokenize, STOPWORDS

    def test_hyphen_tokenization(self):
        from search_engine import tokenize
        tokens = tokenize("state-of-the-art")
        self.assertIn("state", tokens, msg="Hyphens should split tokens")
        self.assertIn("art", tokens, msg="Hyphens should split tokens")
        self.assertNotIn("state-of-the-art", tokens)

    def test_stopword_removal(self):
        from search_engine import tokenize, STOPWORDS
        tokens = tokenize("the quick brown fox")
        for sw in ["the"]:
            if sw in STOPWORDS:
                self.assertNotIn(sw, tokens, msg=f"Stopword '{{sw}}' not removed")

    def test_basic_search(self):
        engine = self._build()
        results = engine.search("{phrase_doc[1].split()[0]}")
        ids = [r[0] for r in results]
        self.assertIn({phrase_doc[0]}, ids)

    def test_phrase_query_positive(self):
        engine = self._build()
        words = [w for w in "{phrase_doc[1]}".lower().replace("-", " ").split()
                 if w not in {stopwords!r}]
        if len(words) >= 2:
            phrase = f"{{words[0]}} {{words[1]}}"
            results = engine.search(f'"{{phrase}}"')
            ids = [r[0] for r in results]
            self.assertIn({phrase_doc[0]}, ids,
                          msg=f"Phrase '{{phrase}}' should match doc {phrase_doc[0]}")

    def test_phrase_query_negative(self):
        engine = self._build()
        results = engine.search('"xyzzy abcdef"')
        self.assertEqual(len(results), 0)

    def test_bm25_tf_matters(self):
        from search_engine import SearchEngine
        engine = SearchEngine()
        engine.add_document(1, "python")
        engine.add_document(2, "python python python")
        results = engine.search("python")
        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0][0], 2,
                         msg="Doc with higher TF should rank first")

    def test_empty_query(self):
        engine = self._build()
        results = engine.search("")
        self.assertEqual(len(results), 0)

    def test_stopwords_not_in_index(self):
        engine = self._build()
        from search_engine import STOPWORDS
        for sw in list(STOPWORDS)[:3]:
            results = engine.search(sw)
            self.assertEqual(len(results), 0,
                             msg=f"Stopword '{{sw}}' should not appear in index")

    def test_all_docs_indexed(self):
        engine = self._build()
        self.assertEqual(engine.doc_count, {len(docs)})


if __name__ == "__main__":
    unittest.main()
'''
