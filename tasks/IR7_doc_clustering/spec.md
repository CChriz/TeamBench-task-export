# IR7: Document Clustering — Tech Topics

## Task Overview

Cluster 27 documents from `documents/` into exactly **4 clusters**
(numbered 0 through 3).

The 10 pre-labelled documents in `category_hints.json` anchor the correct clusters:
0=machine_learning, 1=databases, 2=networking, 3=devops.

---

## Clustering Requirements

### Number of Clusters
Exactly **K = 4**. Do not infer K from the data — it is fixed.

### Cluster IDs
Use integers 0 through 3. The mapping between cluster IDs and labels
is determined by the pre-labelled documents in `category_hints.json`.

### Method
Use keyword/TF-IDF based clustering:
1. Tokenise each document (lowercase, `[a-z]+` regex, remove common stop words).
2. Build a TF-IDF matrix over all documents.
3. Assign each document to its nearest cluster centroid (k-means or similar).
4. Use the pre-labelled documents to initialise centroids or to correct final labels.

### Pre-labelled Documents
The `category_hints.json` file gives 10 ground-truth labels.
These documents MUST end up in their specified cluster.

---

## Required Output: clusters.json

```json
{
  "doc_id_1": 0,
  "doc_id_2": 1,
  "doc_id_3": 0,
  ...
}
```

- Every document in `documents/` must appear as a key.
- Values must be integers in range [0, 3].
- Pre-labelled documents must have their specified cluster IDs.

---

## Constraints

- Exactly 4 distinct cluster IDs must appear in the output.
- No cluster may be empty.
- No cluster may contain more than 60% of all documents.
- All 27 documents must be assigned.
- Verifier must produce `attestation.json` with `verdict="pass"`.
