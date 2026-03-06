# IR8: Search Index — Full Specification (Planner Only)

## Overview

An inverted index implementation in `search_engine.py` has **4 bugs** in tokenization, stopword removal, phrase query handling, and BM25 scoring. Fix all 4 so that `python3 test_search.py` passes.

---

## Application Architecture

```
workspace/
  search_engine.py     # Inverted index + search (buggy)
  test_search.py       # Test suite (do not modify)
```

---

## Bug Inventory

### Bug 1: Wrong tokenization — doesn't handle hyphens
- **Symptom**: Hyphenated words like "state-of-the-art" are kept as a single token instead of being split into individual words
- **Expected behavior**: Hyphens should be treated as word separators, so "state-of-the-art" becomes ["state", "of", "the", "art"]
- **Constraint**: The tokenizer currently only splits on whitespace; it must also split on hyphens

### Bug 2: Missing stopword removal
- **Symptom**: Common words like "the", "a", "is", "of" appear in the index and pollute search results
- **Expected behavior**: A standard stopword list must be applied during indexing and querying to filter out common words
- **Constraint**: Use the STOPWORDS set already defined in the file (it exists but is never used)

### Bug 3: Broken phrase queries
- **Symptom**: Phrase queries (quoted strings like `"machine learning"`) return documents containing either word, not documents where the words appear consecutively
- **Expected behavior**: Phrase queries must only match documents where the exact phrase appears (words in order, adjacent)
- **Constraint**: The index must store term positions to support phrase matching

### Bug 4: Wrong BM25 k1 parameter
- **Symptom**: BM25 scoring uses k1=0.0, which effectively ignores term frequency — all matching documents get the same score regardless of how many times the query term appears
- **Expected behavior**: Use k1=1.2 (standard BM25 parameter) so that term frequency influences ranking

---

## Expected Outcome

After all 4 fixes: `python3 test_search.py` — all tests pass.

---

## Constraints

- Do not modify `test_search.py`
- Only fix `search_engine.py`
