"""
Parameterized generator for IR6: Search Index — TF-IDF Inverted Index.

Each seed produces:
  - 20+ documents in documents/ directory (.txt files)
  - queries.json with 5 test queries
  - expected_results.json with top-3 results per query (for grading)
  - Agent must produce: index.json (inverted index) and results.json (ranked results)

TNI driver: The spec tells the Planner the exact TF-IDF formula, stop-word list,
tokenization rules, and the expected precision-at-3 threshold. The brief only says
"build a search index and answer the queries". Without the Planner the Executor
may use a simpler ranking (raw term frequency, BM25, or fuzzy matching) that
produces different top-3 results, failing the grader checks.

Grader checks (9):
  1. index.json exists
  2. results.json exists
  3. index has at least 20 entries (terms)
  4. results.json has an entry for each query
  5. Top-1 result for query 0 matches expected
  6. Top-1 result for query 1 matches expected
  7. At least 3/5 queries have correct top-1 result
  8. results.json contains score fields (float values)
  9. Attestation verdict=pass
"""
from __future__ import annotations

import json
import math
import re

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Topic pools — each topic is (title, body_sentences, key_terms) ───────────

DOCUMENT_CORPORA = [
    # Corpus 0: technology topics
    {
        "name": "technology",
        "docs": [
            ("machine_learning_intro", "Machine learning enables computers to learn from data without explicit programming. Algorithms improve through experience. Neural networks form the backbone of deep learning.", ["machine", "learning", "neural", "algorithm"]),
            ("deep_learning_guide", "Deep learning uses multi-layer neural networks for feature extraction. Convolutional networks excel at image recognition tasks. Recurrent networks handle sequential data.", ["deep", "neural", "network", "convolutional"]),
            ("python_programming", "Python is a high-level programming language known for simplicity. It supports multiple paradigms including functional and object-oriented programming.", ["python", "programming", "language", "functional"]),
            ("database_systems", "Relational databases store data in tables with rows and columns. SQL enables complex queries across multiple tables. Indexes improve query performance.", ["database", "relational", "sql", "query"]),
            ("cloud_computing", "Cloud computing delivers computing services over the internet. Scalability and elasticity are key benefits. AWS, Azure, and GCP are major providers.", ["cloud", "computing", "scalability", "aws"]),
            ("network_security", "Network security protects computer networks from intrusions. Firewalls filter traffic based on rules. Encryption secures data in transit.", ["network", "security", "firewall", "encryption"]),
            ("api_design", "REST APIs use HTTP methods for resource manipulation. JSON is the standard data format for API communication. Rate limiting prevents abuse.", ["api", "rest", "http", "json"]),
            ("docker_containers", "Docker containers package applications with dependencies. Images provide reproducible build environments. Orchestration tools manage container clusters.", ["docker", "container", "image", "orchestration"]),
            ("git_version_control", "Git tracks changes to files over time. Branches enable parallel development workflows. Merging integrates changes from different branches.", ["git", "version", "branch", "merge"]),
            ("agile_methodology", "Agile development uses iterative sprints for delivery. Daily standups improve team communication. Retrospectives identify process improvements.", ["agile", "sprint", "iteration", "scrum"]),
            ("data_structures", "Data structures organise information for efficient access. Arrays provide constant-time indexing. Linked lists enable efficient insertion.", ["data", "structure", "array", "linked"]),
            ("operating_systems", "Operating systems manage hardware resources for applications. Process scheduling allocates CPU time. Virtual memory extends available RAM.", ["operating", "system", "process", "memory"]),
            ("compiler_design", "Compilers transform source code into executable programs. Lexical analysis tokenises the source text. Parsing builds an abstract syntax tree.", ["compiler", "lexical", "parsing", "syntax"]),
            ("web_development", "Web development creates applications for browsers. HTML structures content, CSS styles it, JavaScript adds interactivity.", ["web", "html", "css", "javascript"]),
            ("distributed_systems", "Distributed systems spread computation across multiple nodes. Consistency, availability, and partition tolerance form the CAP theorem.", ["distributed", "consistency", "availability", "partition"]),
            ("natural_language_processing", "Natural language processing enables computers to understand human text. Tokenization splits text into words. Named entity recognition identifies proper nouns.", ["natural", "language", "processing", "tokenization"]),
            ("graph_algorithms", "Graph algorithms traverse nodes and edges in networks. Breadth-first search finds shortest paths. Depth-first search explores all reachable nodes.", ["graph", "algorithm", "breadth", "depth"]),
            ("software_testing", "Software testing verifies that programs meet requirements. Unit tests check individual functions. Integration tests verify component interactions.", ["testing", "unit", "integration", "verification"]),
            ("microservices_architecture", "Microservices decompose applications into small services. Each service owns its data and communicates via APIs. Service meshes manage inter-service communication.", ["microservices", "service", "decompose", "communication"]),
            ("functional_programming", "Functional programming treats computation as function evaluation. Pure functions have no side effects. Higher-order functions accept functions as arguments.", ["functional", "pure", "higher", "function"]),
            ("kubernetes_orchestration", "Kubernetes orchestrates containerised workloads across clusters. Pods are the smallest deployable units. Services expose pods to network traffic.", ["kubernetes", "pod", "cluster", "workload"]),
            ("data_pipeline", "Data pipelines transform and move data between systems. ETL processes extract, transform, and load data. Stream processing handles real-time data flows.", ["pipeline", "etl", "transform", "stream"]),
        ],
        "queries": [
            ("neural_network_search", ["neural", "network", "deep", "learning"], ["deep_learning_guide", "machine_learning_intro", "natural_language_processing"]),
            ("python_database", ["python", "database", "sql"], ["database_systems", "python_programming", "data_structures"]),
            ("container_orchestration", ["container", "orchestration", "kubernetes"], ["kubernetes_orchestration", "docker_containers", "microservices_architecture"]),
            ("api_security", ["api", "security", "network"], ["network_security", "api_design", "web_development"]),
            ("functional_algorithm", ["functional", "algorithm", "graph"], ["graph_algorithms", "functional_programming", "data_structures"]),
        ],
    },
    # Corpus 1: science topics
    {
        "name": "science",
        "docs": [
            ("quantum_mechanics", "Quantum mechanics describes subatomic particle behaviour. Wave-particle duality is a fundamental principle. The uncertainty principle limits simultaneous measurements.", ["quantum", "particle", "wave", "uncertainty"]),
            ("relativity_theory", "General relativity describes gravity as spacetime curvature. Mass warps spacetime around it. Gravitational waves propagate through spacetime at light speed.", ["relativity", "gravity", "spacetime", "mass"]),
            ("dna_genetics", "DNA carries genetic information in base pair sequences. Genes encode proteins that perform cellular functions. Mutations alter genetic sequences.", ["dna", "genetic", "gene", "protein"]),
            ("climate_science", "Climate science studies long-term atmospheric patterns. Greenhouse gases trap solar radiation. Rising temperatures alter precipitation patterns.", ["climate", "atmosphere", "greenhouse", "temperature"]),
            ("photosynthesis", "Photosynthesis converts sunlight into chemical energy. Chloroplasts contain chlorophyll for light absorption. Carbon dioxide and water produce glucose.", ["photosynthesis", "sunlight", "chlorophyll", "glucose"]),
            ("neuroscience_brain", "Neuroscience studies the nervous system structure and function. Neurons transmit electrical signals. Synapses are junctions between neurons.", ["neuroscience", "neuron", "brain", "synapse"]),
            ("thermodynamics", "Thermodynamics studies heat and energy transfer. Entropy measures disorder in a system. The second law states entropy always increases.", ["thermodynamics", "entropy", "energy", "heat"]),
            ("evolutionary_biology", "Evolutionary biology explains species diversity through natural selection. Mutations create genetic variation. Fitness determines reproductive success.", ["evolution", "natural", "selection", "mutation"]),
            ("astronomy_stars", "Stars form from collapsing gas clouds. Nuclear fusion powers stellar energy production. Red giants form when hydrogen is exhausted.", ["star", "nuclear", "fusion", "hydrogen"]),
            ("chemistry_bonds", "Chemical bonds hold atoms together in molecules. Covalent bonds share electron pairs. Ionic bonds transfer electrons between atoms.", ["chemical", "bond", "electron", "molecule"]),
            ("fluid_dynamics", "Fluid dynamics studies liquid and gas motion. Turbulence creates chaotic flow patterns. Viscosity measures fluid resistance to flow.", ["fluid", "dynamics", "turbulence", "viscosity"]),
            ("ecology_ecosystems", "Ecosystems consist of organisms and their environment. Food webs show energy flow between species. Biodiversity measures species variety.", ["ecology", "ecosystem", "food", "biodiversity"]),
            ("particle_physics", "Particle physics studies fundamental matter constituents. The Standard Model classifies elementary particles. Quarks form protons and neutrons.", ["particle", "quark", "proton", "standard"]),
            ("genetics_crispr", "CRISPR enables precise genome editing. Guide RNA directs Cas9 to target DNA sequences. Gene editing has therapeutic applications.", ["crispr", "genome", "editing", "rna"]),
            ("oceanography", "Oceanography studies ocean physical and chemical properties. Currents distribute heat around the planet. Ocean acidification threatens marine ecosystems.", ["ocean", "current", "acidification", "marine"]),
            ("materials_science", "Materials science investigates solid structure and properties. Crystal lattices determine material strength. Alloys combine metals for improved properties.", ["material", "crystal", "alloy", "structure"]),
            ("microbiology", "Microbiology studies microscopic organisms. Bacteria reproduce through binary fission. Viruses hijack host cell machinery for replication.", ["microbe", "bacteria", "virus", "replication"]),
            ("geophysics", "Geophysics studies Earth's physical properties. Seismic waves reveal interior structure. Plate tectonics drives continental movement.", ["geophysics", "seismic", "plate", "tectonic"]),
            ("optics_light", "Optics studies light behaviour and properties. Refraction bends light at material boundaries. Diffraction causes light waves to spread around obstacles.", ["optics", "light", "refraction", "diffraction"]),
            ("biochemistry", "Biochemistry studies chemical processes in living systems. Enzymes catalyse biochemical reactions. Metabolism converts nutrients into energy.", ["biochemistry", "enzyme", "metabolism", "catalyst"]),
            ("condensed_matter", "Condensed matter physics studies solids and liquids. Superconductors transmit electricity with zero resistance. Semiconductors enable transistors and diodes.", ["condensed", "superconductor", "semiconductor", "resistance"]),
            ("astrophysics_galaxies", "Astrophysics studies galaxy formation and evolution. Dark matter provides gravitational scaffolding. Black holes warp spacetime beyond the event horizon.", ["astrophysics", "galaxy", "dark", "black"]),
        ],
        "queries": [
            ("quantum_particle", ["quantum", "particle", "wave"], ["quantum_mechanics", "particle_physics", "optics_light"]),
            ("dna_genetics_editing", ["dna", "gene", "crispr", "editing"], ["genetics_crispr", "dna_genetics", "microbiology"]),
            ("energy_thermodynamics", ["energy", "entropy", "heat", "thermodynamics"], ["thermodynamics", "photosynthesis", "biochemistry"]),
            ("gravity_spacetime", ["gravity", "spacetime", "relativity"], ["relativity_theory", "astrophysics_galaxies", "geophysics"]),
            ("ecosystem_biodiversity", ["ecosystem", "biodiversity", "evolution"], ["ecology_ecosystems", "evolutionary_biology", "oceanography"]),
        ],
    },
    # Corpus 2: business topics
    {
        "name": "business",
        "docs": [
            ("marketing_strategy", "Marketing strategy defines how companies reach target customers. Segmentation divides markets by demographic and behavioural traits. Positioning differentiates products from competitors.", ["marketing", "strategy", "segmentation", "positioning"]),
            ("financial_accounting", "Financial accounting records economic transactions. Balance sheets show assets and liabilities. Income statements report revenue and expenses.", ["financial", "accounting", "balance", "revenue"]),
            ("supply_chain", "Supply chains coordinate production and distribution. Inventory management balances stock levels with demand. Logistics optimises transportation routes.", ["supply", "chain", "inventory", "logistics"]),
            ("human_resources", "Human resources manages employee relations and development. Recruitment attracts qualified candidates. Performance reviews assess employee contributions.", ["human", "resources", "recruitment", "performance"]),
            ("investment_portfolio", "Portfolio management diversifies investments to reduce risk. Asset allocation balances equities and bonds. Rebalancing maintains target risk levels.", ["investment", "portfolio", "asset", "equity"]),
            ("product_management", "Product management defines product strategy and roadmap. User research uncovers customer needs. Prioritisation frameworks rank feature requests.", ["product", "management", "roadmap", "prioritisation"]),
            ("customer_service", "Customer service resolves issues and builds loyalty. Response time is a key satisfaction metric. Escalation procedures handle complex complaints.", ["customer", "service", "satisfaction", "escalation"]),
            ("operations_management", "Operations management optimises production processes. Lean manufacturing eliminates waste. Six Sigma reduces process variation.", ["operations", "management", "lean", "process"]),
            ("corporate_governance", "Corporate governance sets rules for company leadership. Boards of directors oversee executive decisions. Audit committees ensure financial accuracy.", ["corporate", "governance", "board", "audit"]),
            ("entrepreneurship", "Entrepreneurship creates new businesses and markets. Business plans outline strategy and financial projections. Venture capital funds early-stage startups.", ["entrepreneurship", "startup", "venture", "capital"]),
            ("mergers_acquisitions", "Mergers combine two companies into one entity. Acquisitions purchase controlling stakes. Due diligence evaluates target company financials.", ["merger", "acquisition", "due", "diligence"]),
            ("brand_management", "Brand management builds and protects brand identity. Brand equity measures consumer perception. Brand extensions leverage existing reputation.", ["brand", "management", "equity", "identity"]),
            ("pricing_strategy", "Pricing strategy determines product price points. Value-based pricing aligns price with customer value perception. Dynamic pricing adjusts to market conditions.", ["pricing", "strategy", "value", "dynamic"]),
            ("risk_management", "Risk management identifies and mitigates business risks. Risk registers catalogue known threats. Mitigation plans reduce exposure to critical risks.", ["risk", "management", "mitigation", "exposure"]),
            ("leadership_skills", "Leadership develops organisational vision and direction. Transformational leaders inspire fundamental change. Servant leadership prioritises team member needs.", ["leadership", "vision", "transformational", "servant"]),
            ("digital_transformation", "Digital transformation integrates technology into business operations. Process automation reduces manual effort. Data analytics drives evidence-based decisions.", ["digital", "transformation", "automation", "analytics"]),
            ("negotiation_tactics", "Negotiation tactics influence deal outcomes. BATNA defines the best alternative to a negotiated agreement. Anchoring sets initial position for negotiation.", ["negotiation", "tactics", "agreement", "anchoring"]),
            ("project_management", "Project management delivers defined outcomes within constraints. Gantt charts visualise project timelines. Critical path analysis identifies schedule risks.", ["project", "management", "gantt", "critical"]),
            ("competitive_analysis", "Competitive analysis examines rival strategies and capabilities. Porter's Five Forces framework assesses industry competition. SWOT analysis maps strengths and weaknesses.", ["competitive", "analysis", "porter", "swot"]),
            ("business_ethics", "Business ethics guides moral decision-making in organisations. Corporate social responsibility addresses stakeholder concerns. Ethical leadership models desired behaviour.", ["ethics", "corporate", "responsibility", "moral"]),
            ("organisational_behaviour", "Organisational behaviour studies how people act in companies. Group dynamics influence team performance. Motivation theories explain employee engagement.", ["organisational", "behaviour", "motivation", "engagement"]),
            ("innovation_management", "Innovation management nurtures new ideas into market solutions. Design thinking centres on user needs. Agile prototyping accelerates product iteration.", ["innovation", "design", "thinking", "prototype"]),
        ],
        "queries": [
            ("marketing_brand", ["marketing", "brand", "strategy", "positioning"], ["marketing_strategy", "brand_management", "competitive_analysis"]),
            ("financial_risk", ["financial", "risk", "investment", "portfolio"], ["investment_portfolio", "risk_management", "financial_accounting"]),
            ("operations_lean", ["operations", "lean", "process", "management"], ["operations_management", "project_management", "supply_chain"]),
            ("digital_analytics", ["digital", "analytics", "transformation"], ["digital_transformation", "innovation_management", "product_management"]),
            ("leadership_ethics", ["leadership", "ethics", "corporate", "governance"], ["business_ethics", "corporate_governance", "leadership_skills"]),
        ],
    },
]


def _tokenize(text: str) -> list[str]:
    """Simple whitespace+punctuation tokenizer, lowercase."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return tokens


STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "it", "its", "this", "that", "these", "those",
    "as", "not", "no", "so", "if", "than", "then", "when", "where", "which",
    "who", "how", "all", "each", "between", "into", "through", "during",
    "their", "they", "them", "we", "our", "you", "your", "he", "she", "his",
    "her", "my", "me", "us", "i", "both", "also", "can", "about", "after",
    "before", "such", "what", "more", "most", "other", "over", "under",
    "while", "within", "without", "across", "against", "along", "among",
}


def _build_expected_results(corpus: dict) -> dict:
    """Build expected top-3 results per query using TF-IDF."""
    docs = corpus["docs"]
    queries = corpus["queries"]
    n_docs = len(docs)

    # Build term -> doc_id -> tf
    doc_texts = []
    for title, body, _ in docs:
        tokens = [t for t in _tokenize(body + " " + title) if t not in STOP_WORDS]
        doc_texts.append(tokens)

    # IDF computation
    df: dict[str, int] = {}
    for tokens in doc_texts:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    def tfidf_score(query_terms: list[str], doc_tokens: list[str]) -> float:
        tf_map: dict[str, float] = {}
        total = len(doc_tokens)
        if total == 0:
            return 0.0
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1
        score = 0.0
        for term in query_terms:
            if term in tf_map and term in df:
                tf = tf_map[term] / total
                idf = math.log((n_docs + 1) / (df[term] + 1)) + 1
                score += tf * idf
        return score

    results = {}
    for q_name, q_terms, expected_top3 in queries:
        scores = []
        for i, (title, body, _) in enumerate(docs):
            tokens = [t for t in _tokenize(body + " " + title) if t not in STOP_WORDS]
            s = tfidf_score(q_terms, tokens)
            scores.append((title, s))
        scores.sort(key=lambda x: -x[1])
        top3 = [t for t, _ in scores[:3]]
        results[q_name] = {
            "query_terms": q_terms,
            "expected_top3": expected_top3,
            "computed_top3": top3,
            "expected_top1": expected_top3[0],
        }
    return results


class Generator(TaskGenerator):
    task_id = "IR6_search_index"
    domain = "information_retrieval"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        corpus = DOCUMENT_CORPORA[seed % len(DOCUMENT_CORPORA)]
        docs = corpus["docs"]
        queries = corpus["queries"]

        expected_results = _build_expected_results(corpus)

        # Build workspace: documents/ directory + queries.json + expected_results.json
        workspace_files: dict[str, str] = {}

        for title, body, _ in docs:
            workspace_files[f"documents/{title}.txt"] = body + "\n"

        queries_json = [
            {"query_id": q_name, "terms": q_terms}
            for q_name, q_terms, _ in queries
        ]
        workspace_files["queries.json"] = json.dumps(queries_json, indent=2) + "\n"

        # expected_results.json is written to workspace so agent can verify manually
        # but the grader uses expected.json from reports dir
        workspace_files["README.md"] = self._readme(corpus["name"])

        expected = {
            "corpus_name": corpus["name"],
            "num_docs": len(docs),
            "queries": {
                q_name: {
                    "query_terms": q_terms,
                    "expected_top1": exp_top3[0],
                    "expected_top3": exp_top3,
                }
                for q_name, q_terms, exp_top3 in queries
            },
            "computed_results": expected_results,
            "min_index_terms": 20,
            "required_score_field": True,
        }

        spec_md = self._generate_spec(corpus["name"], len(docs), queries)
        brief_md = self._generate_brief(corpus["name"], len(docs))

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _readme(self, corpus_name: str) -> str:
        return f"""# IR6: Search Index Task — {corpus_name.title()} Corpus

## Files

- `documents/` — {corpus_name} text documents to index
- `queries.json` — search queries to answer

## Your Goal

1. Build an inverted index from all documents in `documents/`.
2. Implement TF-IDF ranking.
3. Answer each query in `queries.json`.
4. Output `index.json` and `results.json`.
"""

    def _generate_spec(self, corpus_name, n_docs, queries):
        query_list = "\n".join(
            f"- `{q_name}`: terms={q_terms}"
            for q_name, q_terms, _ in queries
        )
        return f"""# IR6: Search Index — TF-IDF Inverted Index

## Task Overview

Build an inverted index over {n_docs} {corpus_name} documents and implement
TF-IDF ranking to answer {len(queries)} queries.

---

## Corpus

Documents are in `documents/*.txt`. Each file is a short text on a {corpus_name} topic.
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
{{
  "term1": {{"doc_id": tf_idf_score, ...}},
  "term2": {{"doc_id": tf_idf_score, ...}},
  ...
}}
```

### results.json
```json
{{
  "query_id": [
    {{"doc_id": "name", "score": 0.234}},
    {{"doc_id": "name", "score": 0.198}},
    {{"doc_id": "name", "score": 0.145}}
  ],
  ...
}}
```

Each query result must include the top-3 ranked documents with scores.

---

## Queries

{query_list}

---

## Constraints

- `index.json` must have at least 20 unique terms as keys.
- Each result entry must have `doc_id` (string) and `score` (float) fields.
- Results for each query must be sorted descending by score.
- Verifier must produce `attestation.json` with `verdict="pass"`.
"""

    def _generate_brief(self, corpus_name, n_docs):
        return f"""# IR6: Search Index (Brief)

Build a TF-IDF search index over {n_docs} {corpus_name} documents in `documents/`.

Answer the queries in `queries.json`.

**Outputs required**:
- `index.json` — inverted index mapping terms to (doc_id, tfidf_score) pairs
- `results.json` — top-3 ranked documents per query with scores

The Planner has the exact TF-IDF formula, tokenization rules, and stop-word list.
Coordinate with the Planner on the exact formula before implementing.
"""
