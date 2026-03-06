# IR7: Document Clustering (Brief)

Cluster 27 tech topic documents into 4 groups.

**Input files**:
- `documents/` — all documents to cluster
- `category_hints.json` — 10 pre-labelled documents with correct cluster IDs

**Output required**:
- `clusters.json` — mapping of doc_id to cluster_id (integer 0 to 3)

The Planner has the exact clustering requirements including K, method, and
constraints. Coordinate with the Planner before implementing.
