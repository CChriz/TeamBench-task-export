"""
Parameterized generator for IR7: Document Clustering.

Each seed produces:
  - 30+ documents in documents/ directory (.txt files) across 4-5 topic clusters
  - category_hints.json with partial labels (10 documents pre-labelled)
  - Agent must produce clusters.json mapping doc_id -> cluster_id (integer 0..K-1)

TNI driver: The spec tells the Planner the exact number of clusters K, which docs
are pre-labelled (and their correct cluster), and that the clustering must be
keyword/TF-IDF based (not LLM semantic inference). The brief only says "cluster
30+ documents". Without the Planner the Executor may use wrong K, ignore hints,
or use a method that misclassifies the deliberately ambiguous boundary docs.

Grader checks (9):
  1. clusters.json exists and is valid JSON
  2. All documents are assigned a cluster (no missing doc_ids)
  3. Exactly K unique cluster IDs (integers 0..K-1)
  4. No empty clusters (each cluster has at least 2 docs)
  5. Pre-labelled docs from category_hints.json are in correct clusters
  6. At least 80% of pre-labelled docs are correctly placed
  7. Core topic docs are correctly clustered together
  8. Cluster sizes are reasonable (no cluster has >60% of all docs)
  9. Attestation verdict=pass
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Topic cluster definitions ─────────────────────────────────────────────────
# Each corpus has K clusters with 6-7 docs each, plus 2-3 ambiguous boundary docs

CORPORA = [
    # Corpus 0: 4 tech clusters
    {
        "name": "tech_topics",
        "K": 4,
        "clusters": [
            {
                "id": 0,
                "label": "machine_learning",
                "core_docs": [
                    ("ml_supervised", "Supervised learning trains models on labelled examples. Classification predicts discrete categories. Regression predicts continuous values. Training data quality determines model performance."),
                    ("ml_unsupervised", "Unsupervised learning finds patterns in unlabelled data. Clustering groups similar data points. Dimensionality reduction simplifies feature spaces. Autoencoders learn compact representations."),
                    ("ml_neural_networks", "Neural networks learn hierarchical feature representations. Backpropagation updates weights to minimise loss. Activation functions introduce non-linearity. Dropout prevents overfitting during training."),
                    ("ml_evaluation", "Model evaluation measures predictive performance. Cross-validation estimates generalisation error. Precision and recall trade off false positives and negatives. ROC curves visualise classifier performance."),
                    ("ml_feature_engineering", "Feature engineering transforms raw data into model inputs. Normalisation scales numeric features to equal range. One-hot encoding represents categorical variables. Feature selection removes irrelevant predictors."),
                    ("ml_ensemble", "Ensemble methods combine multiple models for improved accuracy. Random forests aggregate decision tree predictions. Gradient boosting builds trees sequentially. Bagging reduces variance through bootstrap aggregation."),
                ],
            },
            {
                "id": 1,
                "label": "databases",
                "core_docs": [
                    ("db_relational", "Relational databases store data in normalised tables. Foreign keys link related rows across tables. ACID transactions ensure data consistency. Indexes speed up query execution."),
                    ("db_nosql", "NoSQL databases sacrifice strict consistency for scalability. Document stores use flexible JSON schemas. Key-value stores provide O(1) lookups. Column-family stores suit time-series data."),
                    ("db_query_optimisation", "Query optimisation reduces execution time and resource usage. The query planner selects efficient join strategies. Covering indexes satisfy queries without table access. Partitioning distributes data across shards."),
                    ("db_transactions", "Database transactions group operations into atomic units. Isolation levels control concurrent read visibility. Deadlocks occur when transactions wait on each other. Two-phase commit coordinates distributed transactions."),
                    ("db_replication", "Database replication copies data to multiple nodes. Leader-follower replication directs writes to the leader. Multi-leader replication allows writes at multiple nodes. Conflict resolution handles concurrent writes."),
                    ("db_schema_design", "Schema design balances normalisation against query performance. Third normal form eliminates transitive dependencies. Denormalisation introduces redundancy for read speed. Entity-relationship diagrams model data relationships."),
                ],
            },
            {
                "id": 2,
                "label": "networking",
                "core_docs": [
                    ("net_tcp_ip", "TCP/IP is the foundational internet protocol suite. IP provides packet routing across networks. TCP ensures reliable ordered delivery. UDP trades reliability for lower latency."),
                    ("net_http", "HTTP transfers hypertext documents across the web. REST uses HTTP verbs for resource operations. HTTP/2 multiplexes multiple streams over one connection. TLS encrypts HTTP traffic as HTTPS."),
                    ("net_dns", "DNS resolves domain names to IP addresses. Authoritative servers hold definitive records. Recursive resolvers traverse the hierarchy. Caching reduces resolution latency."),
                    ("net_firewalls", "Firewalls filter network traffic by rules. Stateful inspection tracks connection state. Application-layer firewalls inspect payload content. Intrusion detection systems alert on suspicious patterns."),
                    ("net_load_balancing", "Load balancers distribute traffic across server pools. Round-robin cycles through backends sequentially. Least-connections routes to the least busy server. Health checks remove unhealthy backends from rotation."),
                    ("net_vpn", "VPNs create encrypted tunnels over public networks. Site-to-site VPNs connect office networks. Remote access VPNs let users connect securely. Protocols include OpenVPN, WireGuard, and IPSec."),
                ],
            },
            {
                "id": 3,
                "label": "devops",
                "core_docs": [
                    ("devops_cicd", "CI/CD pipelines automate build, test, and deploy stages. Continuous integration merges code changes frequently. Continuous delivery automates release to staging. Continuous deployment pushes every passing build to production."),
                    ("devops_infrastructure", "Infrastructure as code provisions resources declaratively. Terraform manages cloud resources across providers. Ansible automates configuration management. Immutable infrastructure replaces rather than modifies servers."),
                    ("devops_monitoring", "Monitoring collects metrics from running systems. Dashboards visualise system health at a glance. Alerting notifies operators of threshold breaches. Distributed tracing tracks requests across services."),
                    ("devops_containers", "Containers package applications with their runtime dependencies. Docker builds images from Dockerfiles. Kubernetes schedules containers across clusters. Helm charts template Kubernetes manifests."),
                    ("devops_gitops", "GitOps manages infrastructure state through Git repositories. Pull-based reconciliation applies Git changes to clusters. Drift detection alerts when state diverges from Git. Rollback reverts to a previous Git commit."),
                    ("devops_secrets", "Secrets management protects sensitive credentials. Vault stores and rotates secrets securely. Environment variables inject secrets at runtime. Secret scanning prevents credentials in source code."),
                ],
            },
        ],
        "ambiguous_docs": [
            ("ml_database_embeddings", "Vector databases store embedding representations for similarity search. Machine learning models generate embeddings from text. Approximate nearest-neighbour indexes enable fast retrieval.", 0),
            ("net_security_tls", "TLS certificates authenticate servers to clients. Certificate authorities sign certificates. Mutual TLS authenticates both client and server. Cipher suites negotiate encryption algorithms.", 2),
            ("devops_ml_training", "MLOps applies DevOps practices to machine learning. Model registries version trained models. Feature stores centralise training data pipelines. A/B testing compares model versions in production.", 3),
        ],
    },
    # Corpus 1: 4 science clusters
    {
        "name": "science_fields",
        "K": 4,
        "clusters": [
            {
                "id": 0,
                "label": "physics",
                "core_docs": [
                    ("phys_mechanics", "Classical mechanics describes motion under forces. Newton's laws relate force, mass, and acceleration. Conservation of momentum holds in closed systems. Kinetic energy converts to potential energy in conservative fields."),
                    ("phys_thermodynamics", "Thermodynamics studies heat and work exchanges. Entropy measures the disorder of a system. The Carnot cycle defines maximum heat engine efficiency. Phase transitions occur at specific temperature and pressure combinations."),
                    ("phys_electromagnetism", "Electromagnetism unifies electric and magnetic phenomena. Maxwell's equations describe field propagation. Electromagnetic waves travel at the speed of light. Inductance and capacitance store magnetic and electric energy."),
                    ("phys_quantum", "Quantum mechanics describes atomic and subatomic phenomena. The Schrödinger equation governs wave function evolution. Heisenberg's uncertainty principle limits simultaneous measurements. Superposition allows particles to occupy multiple states."),
                    ("phys_relativity", "Special relativity unifies space and time into spacetime. The speed of light is constant in all reference frames. Time dilation slows clocks in motion. Mass-energy equivalence is expressed as E equals mc squared."),
                    ("phys_optics", "Wave optics explains diffraction and interference phenomena. Snell's law governs refraction at material boundaries. Polarisation restricts the oscillation plane of electromagnetic waves. Lasers produce coherent monochromatic light."),
                ],
            },
            {
                "id": 1,
                "label": "biology",
                "core_docs": [
                    ("bio_cell", "Cells are the fundamental units of life. Prokaryotic cells lack a nucleus. Eukaryotic cells contain membrane-bound organelles. Mitosis replicates somatic cells for growth and repair."),
                    ("bio_genetics", "Genetics studies how traits are inherited. DNA encodes genetic information in base pair sequences. Transcription copies DNA to RNA. Translation builds proteins from messenger RNA codons."),
                    ("bio_evolution", "Evolution explains species diversity through natural selection. Mutations introduce heritable variation. Fitness determines reproductive success in a given environment. Speciation produces reproductively isolated populations."),
                    ("bio_ecology", "Ecology examines interactions between organisms and environments. Food webs map energy flow between trophic levels. Predator-prey dynamics regulate population sizes. Habitat destruction reduces biodiversity."),
                    ("bio_microbiology", "Microbiology studies microscopic organisms. Bacteria reproduce asexually through binary fission. Viruses replicate inside host cells. Archaea thrive in extreme environments."),
                    ("bio_neuroscience", "Neuroscience investigates nervous system structure and function. Neurons transmit electrochemical signals through axons. Synapses pass signals between neurons. Plasticity allows the brain to reorganise itself."),
                ],
            },
            {
                "id": 2,
                "label": "chemistry",
                "core_docs": [
                    ("chem_organic", "Organic chemistry studies carbon-containing compounds. Hydrocarbons form the backbone of organic molecules. Functional groups determine chemical reactivity. Polymerisation links monomers into long chains."),
                    ("chem_inorganic", "Inorganic chemistry studies compounds lacking carbon. Coordination complexes bind ligands to metal centres. Redox reactions transfer electrons between species. Ionic compounds form through electron transfer."),
                    ("chem_physical", "Physical chemistry applies physics to chemical systems. Reaction kinetics measures rates and rate laws. Chemical equilibrium balances forward and reverse reactions. Electrochemistry studies electron transfer in solution."),
                    ("chem_analytical", "Analytical chemistry measures chemical composition. Spectroscopy uses light absorption for identification. Chromatography separates mixtures by affinity differences. Mass spectrometry measures molecular mass fragments."),
                    ("chem_biochemistry", "Biochemistry studies chemical processes in living organisms. Enzymes catalyse reactions by lowering activation energy. Metabolic pathways convert nutrients into cellular energy. Lipids form cell membrane bilayers."),
                    ("chem_materials", "Materials chemistry designs substances with target properties. Polymers consist of repeating monomer units. Ceramics withstand high temperatures. Composites combine materials for improved strength."),
                ],
            },
            {
                "id": 3,
                "label": "earth_science",
                "core_docs": [
                    ("earth_geology", "Geology studies Earth's solid materials and processes. Rock cycles transform igneous, sedimentary, and metamorphic rocks. Plate tectonics drives continental movement. Volcanic activity releases magma from the mantle."),
                    ("earth_climate", "Climate science examines long-term atmospheric patterns. Greenhouse gases trap outgoing infrared radiation. Ocean currents redistribute heat across the planet. Ice cores record past atmospheric composition."),
                    ("earth_oceanography", "Oceanography studies physical and chemical properties of oceans. Thermohaline circulation drives deep ocean currents. Tidal forces result from gravitational interactions. Coral reefs support exceptional biodiversity."),
                    ("earth_atmosphere", "Atmospheric science studies the layers of air surrounding Earth. The troposphere contains most weather phenomena. Jet streams influence weather pattern movement. Ozone absorbs harmful ultraviolet radiation."),
                    ("earth_geophysics", "Geophysics uses physics to study Earth's interior. Seismic waves reveal internal layering. Magnetic anomalies map seafloor spreading. Gravity surveys detect subsurface density variations."),
                    ("earth_hydrology", "Hydrology studies water movement through the environment. The water cycle describes evaporation, condensation, and precipitation. Aquifers store groundwater in permeable rock. River discharge varies with precipitation and snowmelt."),
                ],
            },
        ],
        "ambiguous_docs": [
            ("biophys_membrane", "Biophysics applies physics to biological systems. Membrane potential arises from ion concentration gradients. Patch clamp techniques measure ion channel conductance. Optical tweezers manipulate single molecules.", 0),
            ("biochem_enzyme_kinetics", "Enzyme kinetics applies physical chemistry to biological catalysts. Michaelis-Menten kinetics describes substrate saturation. Inhibitors reduce reaction rates competitively or non-competitively.", 2),
            ("earth_geo_chemistry", "Geochemistry examines Earth's chemical composition and processes. Isotope ratios date rock formations. Mineral weathering releases ions into soil water. Hydrothermal vents host chemosynthetic ecosystems.", 3),
        ],
    },
    # Corpus 2: 5 business clusters
    {
        "name": "business_functions",
        "K": 5,
        "clusters": [
            {
                "id": 0,
                "label": "finance",
                "core_docs": [
                    ("fin_accounting", "Financial accounting records and reports economic transactions. The balance sheet shows assets, liabilities, and equity. The income statement reports revenue minus expenses. Cash flow statements track actual money movement."),
                    ("fin_investment", "Investment analysis evaluates expected returns and risks. Discounted cash flow models value future earnings. Portfolio diversification reduces unsystematic risk. Beta measures sensitivity to market movements."),
                    ("fin_corporate", "Corporate finance manages company capital structure. Debt financing uses borrowed funds with fixed obligations. Equity financing dilutes ownership but carries no repayment. WACC balances cost of debt and equity."),
                    ("fin_risk", "Financial risk management identifies and hedges exposures. Value at risk quantifies potential loss in adverse scenarios. Credit risk measures likelihood of counterparty default. Derivatives transfer risk to willing counterparties."),
                    ("fin_budgeting", "Budgeting translates strategy into financial targets. Zero-based budgeting justifies every expense from scratch. Variance analysis compares actuals to budget. Rolling forecasts update projections as conditions change."),
                    ("fin_tax", "Tax planning minimises corporate tax liabilities legally. Transfer pricing governs intercompany transactions. Deferred tax liabilities arise from timing differences. Tax treaties prevent double taxation across jurisdictions."),
                ],
            },
            {
                "id": 1,
                "label": "marketing",
                "core_docs": [
                    ("mkt_strategy", "Marketing strategy defines target segments and value proposition. Market research uncovers customer needs and preferences. Competitive positioning differentiates the brand from rivals. Go-to-market plans sequence product launch activities."),
                    ("mkt_digital", "Digital marketing reaches customers through online channels. Search engine optimisation improves organic visibility. Pay-per-click advertising targets intent-driven searches. Social media marketing builds community engagement."),
                    ("mkt_content", "Content marketing attracts audiences through valuable information. Blog posts demonstrate expertise and improve SEO. Video content drives high engagement on social platforms. Thought leadership builds brand authority."),
                    ("mkt_brand", "Brand management builds and protects brand equity. Brand identity includes visual elements and tone of voice. Brand extensions leverage existing recognition. Rebranding refreshes perception in changing markets."),
                    ("mkt_analytics", "Marketing analytics measures campaign performance. Customer acquisition cost tracks spending efficiency. Lifetime value estimates long-term customer revenue. Attribution models assign credit to marketing touchpoints."),
                    ("mkt_crm", "CRM systems manage customer relationships and sales pipelines. Lead scoring prioritises prospects by conversion likelihood. Segmentation enables personalised communication. Retention programmes reduce customer churn."),
                ],
            },
            {
                "id": 2,
                "label": "operations",
                "core_docs": [
                    ("ops_supply_chain", "Supply chain management coordinates supplier to customer flow. Procurement selects and contracts with suppliers. Inventory management balances stock with demand uncertainty. Last-mile logistics delivers products to end customers."),
                    ("ops_lean", "Lean operations eliminate waste from production processes. Value stream mapping identifies non-value-adding steps. Kaizen drives continuous incremental improvement. Just-in-time delivery reduces inventory holding costs."),
                    ("ops_quality", "Quality management ensures products meet specifications. Six Sigma uses statistical tools to reduce defects. ISO standards define quality system requirements. Root cause analysis prevents defect recurrence."),
                    ("ops_project", "Project management delivers defined outputs within constraints. Work breakdown structures decompose deliverables. Critical path method identifies schedule-critical tasks. Earned value analysis tracks progress against cost."),
                    ("ops_logistics", "Logistics manages the physical flow of goods. Warehouse management systems coordinate picking and packing. Route optimisation reduces transportation costs. Cold chain logistics maintains temperature-sensitive products."),
                    ("ops_outsourcing", "Outsourcing transfers non-core activities to third parties. Business process outsourcing handles back-office functions. Offshore outsourcing accesses lower-cost labour markets. SLAs define performance expectations for vendors."),
                ],
            },
            {
                "id": 3,
                "label": "hr",
                "core_docs": [
                    ("hr_recruitment", "Recruitment attracts and selects qualified candidates. Job descriptions define role requirements and expectations. Competency-based interviews assess behavioural evidence. Assessment centres evaluate candidates through simulations."),
                    ("hr_development", "Learning and development builds employee skills and capabilities. Training needs analysis identifies skill gaps. Mentoring pairs experienced employees with newcomers. Leadership development prepares high-potential employees for senior roles."),
                    ("hr_compensation", "Compensation management designs fair and competitive pay structures. Job evaluation ranks roles by complexity and impact. Market benchmarking aligns salaries with industry norms. Variable pay links rewards to individual and company performance."),
                    ("hr_performance", "Performance management aligns employee effort with organisational goals. OKRs link individual objectives to company strategy. 360-degree feedback collects views from multiple raters. Performance improvement plans support struggling employees."),
                    ("hr_culture", "Organisational culture shapes how work gets done. Values statements articulate desired behavioural norms. Employee engagement surveys measure workforce commitment. Diversity and inclusion programmes promote equitable workplaces."),
                    ("hr_compliance", "HR compliance ensures adherence to employment law. Equal opportunity regulations prohibit discriminatory practices. Data protection law governs personal employee data. Whistleblowing policies protect employees who report misconduct."),
                ],
            },
            {
                "id": 4,
                "label": "strategy",
                "core_docs": [
                    ("strat_competitive", "Competitive strategy defines how a company competes. Porter's Five Forces analyses industry attractiveness. Cost leadership competes on lowest delivered cost. Differentiation commands premium pricing through unique value."),
                    ("strat_growth", "Growth strategy identifies paths to revenue expansion. Market penetration increases share in existing markets. Market development enters new geographies or segments. Diversification enters unrelated businesses."),
                    ("strat_innovation", "Innovation strategy channels resources toward new opportunities. Disruptive innovation targets underserved market segments. Open innovation sources ideas from external partners. Innovation portfolios balance incremental and breakthrough bets."),
                    ("strat_ma", "Mergers and acquisitions accelerate strategic transformation. Due diligence evaluates target financials and risks. Integration planning preserves acquired value. Synergy realisation requires disciplined execution."),
                    ("strat_digital", "Digital strategy harnesses technology for competitive advantage. Platform strategies create network effects. Data assets enable algorithmic differentiation. Digital ecosystems integrate complementary partner offerings."),
                    ("strat_global", "Global strategy manages operations across multiple countries. Localisation adapts products for cultural preferences. Standardisation achieves scale economies across markets. Joint ventures share risk in unfamiliar markets."),
                ],
            },
        ],
        "ambiguous_docs": [
            ("fin_strategy_ma", "Strategic acquisitions deploy capital for competitive advantage. Target valuation uses discounted cash flow and comparable transactions. Post-merger integration aligns cultures and systems.", 0),
            ("mkt_ops_crm", "CRM systems bridge marketing and operations. Lead management tracks prospects through the sales funnel. Order management integrates with fulfilment operations.", 1),
            ("hr_strat_talent", "Talent strategy ensures the organisation has future capabilities. Workforce planning forecasts headcount by role and skill. Succession planning identifies replacements for critical positions.", 3),
        ],
    },
]


class Generator(TaskGenerator):
    task_id = "IR7_doc_clustering"
    domain = "information_retrieval"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        corpus = CORPORA[seed % len(CORPORA)]
        K = corpus["K"]
        clusters = corpus["clusters"]
        ambiguous = corpus["ambiguous_docs"]

        # Build full document list
        all_docs: list[tuple[str, str, int]] = []  # (doc_id, text, cluster_id)
        for cluster in clusters:
            for doc_id, text in cluster["core_docs"]:
                all_docs.append((doc_id, text, cluster["id"]))
        for doc_id, text, cluster_id in ambiguous:
            all_docs.append((doc_id, text, cluster_id))

        # Shuffle docs so order doesn't reveal clusters
        rng.shuffle(all_docs)

        # Pick 10 docs as hints (at least 2 per cluster, prioritise core docs)
        hint_docs: list[tuple[str, int]] = []
        seen_clusters: set[int] = set()
        for doc_id, text, cid in all_docs:
            if cid not in seen_clusters:
                hint_docs.append((doc_id, cid))
                seen_clusters.add(cid)
            if len(hint_docs) == K:
                break
        # Add more hints to reach 10
        remaining = [(d, c) for d, _, c in all_docs if d not in {h for h, _ in hint_docs}]
        rng.shuffle(remaining)
        hint_docs.extend(remaining[: 10 - len(hint_docs)])

        # Core docs that must be correctly clustered (used by grader)
        core_docs_by_cluster: dict[int, list[str]] = {c["id"]: [] for c in clusters}
        for cluster in clusters:
            core_docs_by_cluster[cluster["id"]] = [d for d, _ in cluster["core_docs"][:3]]

        expected = {
            "corpus_name": corpus["name"],
            "K": K,
            "num_docs": len(all_docs),
            "doc_cluster_map": {doc_id: cid for doc_id, _, cid in all_docs},
            "hint_docs": {doc_id: cid for doc_id, cid in hint_docs},
            "core_docs_by_cluster": core_docs_by_cluster,
            "cluster_labels": {str(c["id"]): c["label"] for c in clusters},
        }

        workspace_files: dict[str, str] = {}
        for doc_id, text, _ in all_docs:
            workspace_files[f"documents/{doc_id}.txt"] = text + "\n"

        category_hints = {
            "num_clusters": K,
            "labelled_documents": {doc_id: cid for doc_id, cid in hint_docs},
            "note": f"These {len(hint_docs)} documents are pre-labelled. Use them to anchor your clustering.",
        }
        workspace_files["category_hints.json"] = json.dumps(category_hints, indent=2) + "\n"
        workspace_files["README.md"] = self._readme(corpus["name"], K, len(all_docs))

        spec_md = self._generate_spec(corpus["name"], K, len(all_docs), len(hint_docs), clusters)
        brief_md = self._generate_brief(corpus["name"], K, len(all_docs))

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _readme(self, corpus_name, K, n_docs):
        return f"""# IR7: Document Clustering — {corpus_name.replace('_', ' ').title()}

## Files

- `documents/` — {n_docs} text documents to cluster
- `category_hints.json` — {10} pre-labelled documents to anchor clustering

## Your Goal

Cluster all {n_docs} documents into exactly {K} clusters.
Output `clusters.json` mapping each document ID to a cluster ID (0 to {K - 1}).
"""

    def _generate_spec(self, corpus_name, K, n_docs, n_hints, clusters):
        cluster_labels = ", ".join(f"{c['id']}={c['label']}" for c in clusters)
        return f"""# IR7: Document Clustering — {corpus_name.replace('_', ' ').title()}

## Task Overview

Cluster {n_docs} documents from `documents/` into exactly **{K} clusters**
(numbered 0 through {K - 1}).

The {n_hints} pre-labelled documents in `category_hints.json` anchor the correct clusters:
{cluster_labels}.

---

## Clustering Requirements

### Number of Clusters
Exactly **K = {K}**. Do not infer K from the data — it is fixed.

### Cluster IDs
Use integers 0 through {K - 1}. The mapping between cluster IDs and labels
is determined by the pre-labelled documents in `category_hints.json`.

### Method
Use keyword/TF-IDF based clustering:
1. Tokenise each document (lowercase, `[a-z]+` regex, remove common stop words).
2. Build a TF-IDF matrix over all documents.
3. Assign each document to its nearest cluster centroid (k-means or similar).
4. Use the pre-labelled documents to initialise centroids or to correct final labels.

### Pre-labelled Documents
The `category_hints.json` file gives {n_hints} ground-truth labels.
These documents MUST end up in their specified cluster.

---

## Required Output: clusters.json

```json
{{
  "doc_id_1": 0,
  "doc_id_2": 1,
  "doc_id_3": 0,
  ...
}}
```

- Every document in `documents/` must appear as a key.
- Values must be integers in range [0, {K - 1}].
- Pre-labelled documents must have their specified cluster IDs.

---

## Constraints

- Exactly {K} distinct cluster IDs must appear in the output.
- No cluster may be empty.
- No cluster may contain more than 60% of all documents.
- All {n_docs} documents must be assigned.
- Verifier must produce `attestation.json` with `verdict="pass"`.
"""

    def _generate_brief(self, corpus_name, K, n_docs):
        return f"""# IR7: Document Clustering (Brief)

Cluster {n_docs} {corpus_name.replace('_', ' ')} documents into {K} groups.

**Input files**:
- `documents/` — all documents to cluster
- `category_hints.json` — {10} pre-labelled documents with correct cluster IDs

**Output required**:
- `clusters.json` — mapping of doc_id to cluster_id (integer 0 to {K - 1})

The Planner has the exact clustering requirements including K, method, and
constraints. Coordinate with the Planner before implementing.
"""
