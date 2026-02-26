# TeamBench Scaling Plan: 22 → 80+ Tasks

## Design Principle: High-TNI by Construction

Every new task MUST be designed so the information partition is meaningful:
- **Spec contains information that CANNOT be inferred from the workspace alone**
- **Brief is genuinely insufficient** — a single agent with brief + workspace should struggle
- **Teamwork adds measurable value** — Planner's spec knowledge should enable Executor to succeed

### Anti-patterns to avoid:
- Brief that paraphrases the spec (leaks everything)
- Tasks where running tests reveals all requirements (spec becomes redundant)
- Tasks where the workspace is self-documenting (no hidden constraints)

## High-TNI Task Patterns

### Pattern A: Hidden Constraints
Spec contains requirements not surfaced in workspace, tests, or error messages.
- Example: "Output must be sorted by priority then alphabetically" — not enforced by any test
- TNI driver: Only the Planner knows the sorting requirement

### Pattern B: Adversarial Traps
Workspace contains misleading signals; spec warns about them.
- Example: A config file with a plausible-but-wrong default; spec says "override X to Y"
- TNI driver: Without Planner's warning, Executor falls into the trap

### Pattern C: Multi-Criteria Optimization
Spec has the full scoring rubric (latency + correctness + security); brief mentions only primary goal.
- Example: "Fix the API" (brief) vs "Fix the API while maintaining <100ms p99, no SQL injection, and backward-compatible response format" (spec)
- TNI driver: Executor optimizes for the wrong objective without Planner guidance

### Pattern D: Cross-System Contract
Spec has the API contract between two services; Executor only sees one service's code.
- Example: Service A expects JSON with field "user_id", workspace only has Service B's code
- TNI driver: Planner relays the contract, Executor implements it

### Pattern E: Compliance Rules
Spec has regulatory/policy rules; brief says "make it compliant."
- Example: GDPR data handling rules, PCI-DSS requirements
- TNI driver: Planner translates policy to actionable implementation steps

### Pattern F: Ordered Dependencies
Spec describes the correct execution order with rationale; brief only says "complete all steps."
- Example: "Migration must run schema change before data backfill, then index rebuild"
- TNI driver: Wrong ordering causes data loss or corruption

## New Task Categories (Target: 58 new tasks)

### Tier 1: Highest Priority (30 tasks) — Natural High-TNI Workflows

#### SEC (Security) — 7 new tasks (8 total)
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| SEC2_auth_bypass | Fix authentication bypass vulnerabilities | A,C | hard | Spec has the threat model; brief says "fix auth" |
| SEC3_crypto_upgrade | Migrate deprecated crypto primitives | D,F | hard | Spec has migration order + compatibility matrix |
| SEC4_input_validation | Add input validation per OWASP rules | E | medium | Spec has the validation rules; brief says "sanitize inputs" |
| SEC5_secrets_rotation | Rotate hardcoded secrets to vault | A,F | medium | Spec has the vault API contract + rotation order |
| SEC6_csrf_protection | Add CSRF protection to forms | C | medium | Spec has which forms need protection and which are exempt |
| SEC7_rate_limiting | Implement rate limiting per API tier | D | hard | Spec has tier definitions; Executor sees only the API code |
| SEC8_dependency_audit | Patch vulnerable dependencies | B,C | expert | Spec has CVE details + acceptable version ranges |

#### INC (Incident Response) — 8 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| INC1_cascade_failure | Diagnose cascading service failure | A,D | hard | Spec has the service dependency graph; Executor sees individual logs |
| INC2_data_corruption | Fix data corruption from partial write | F | hard | Spec has the correct schema + recovery procedure |
| INC3_memory_leak | Find and fix memory leak in service | A | medium | Spec has the heap profile analysis; brief says "service crashes after 2h" |
| INC4_dns_miscfg | Fix DNS/routing misconfiguration | D | medium | Spec has the network topology; Executor sees config files |
| INC5_cert_expiry | Renew expired certificates across services | F | medium | Spec has the cert chain + renewal order |
| INC6_deadlock | Diagnose and fix distributed deadlock | A,B | expert | Spec has the lock ordering; workspace has misleading thread dumps |
| INC7_rollback | Execute safe rollback of failed deployment | F,C | hard | Spec has the rollback checklist + data migration constraints |
| INC8_capacity | Fix autoscaling misconfiguration | C,D | hard | Spec has SLA targets; brief says "service is slow" |

#### CR (Code Review) — 5 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| CR1_review_respond | Implement changes from code review | D | medium | Spec has the review comments; Executor applies them |
| CR2_style_enforce | Fix code to match style guide | E | easy | Spec has the style guide; brief says "fix style issues" |
| CR3_perf_review | Optimize per profiler findings | A,C | hard | Spec has the profiling report + perf budget |
| CR4_api_review | Fix API design issues from review | D,C | hard | Spec has API design guidelines + specific violations |
| CR5_test_coverage | Add tests for uncovered code paths | A | medium | Spec lists exact uncovered paths; brief says "increase coverage" |

#### SPEC (Spec-to-Implementation) — 5 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| SPEC1_feature_impl | Implement feature from PRD | A,C,D | hard | Spec has the PRD with acceptance criteria |
| SPEC2_api_design | Implement API from OpenAPI spec | D | medium | Spec has the OpenAPI definition; Executor writes code |
| SPEC3_data_model | Build data model from ERD | D,F | medium | Spec has entity-relationship diagram + constraints |
| SPEC4_migration | Write DB migration from schema diff | D,F | hard | Spec has before/after schemas + migration constraints |
| SPEC5_config_system | Build config system from requirements | A,C | hard | Spec has config schema + validation rules + defaults |

#### PIPE (Pipeline/Integration) — 5 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| PIPE1_etl_fix | Fix ETL pipeline with schema changes | D,F | medium | Spec has source/target schema mapping |
| PIPE2_api_gateway | Configure API gateway routing | D | medium | Spec has the routing table; Executor sees gateway config |
| PIPE3_msg_queue | Fix message queue consumer | B,D | hard | Spec has the message format contract |
| PIPE4_ci_cd | Fix broken CI/CD pipeline | A,F | medium | Spec has the pipeline requirements + deployment order |
| PIPE5_data_sync | Fix cross-service data sync | D,F | expert | Spec has the sync protocol + conflict resolution rules |

### Tier 2: Medium Priority (18 tasks) — Expand Existing Domains

#### OPS (Ops) — 4 new tasks (6 total)
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| O3_log_analysis | Debug from structured logs | A | medium | Spec has the error taxonomy; brief says "find the bug" |
| O4_monitoring | Fix alerting rules | C,D | hard | Spec has SLA thresholds + alert routing rules |
| O5_container_debug | Fix containerized service | A,B | hard | Spec has the Dockerfile intent; workspace has broken image |
| O6_perf_tuning | Tune service configuration | C | expert | Spec has the performance budget across 5 metrics |

#### DATA (Data) — 4 new tasks (7 total)
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| D3_schema_migration | Migrate database schema | D,F | hard | Spec has the migration plan + rollback strategy |
| D4_data_pipeline | Fix data validation pipeline | A,C | medium | Spec has validation rules; brief says "data quality issues" |
| D5_query_optimize | Optimize slow queries | A,C | hard | Spec has the query execution plans + target latency |
| D6_data_reconcile | Reconcile data between systems | D | expert | Spec has the reconciliation rules + source of truth |

#### SW (Software) — 5 new tasks (10 total)
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| S3_refactor_extract | Extract module per design doc | D | medium | Spec has the target architecture diagram |
| S4_backward_compat | Add feature maintaining backward compat | A,C | hard | Spec lists backward-compat constraints |
| S5_error_handling | Implement error handling strategy | E | medium | Spec has error codes + recovery actions |
| S6_caching | Implement caching per requirements | A,C,D | hard | Spec has cache invalidation rules + TTLs |
| S7_i18n | Internationalize application | E,F | hard | Spec has i18n requirements + locale rules |

#### LH (Long-Horizon) — 3 new tasks (5 total)
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| LH3_multi_service | Fix across 3+ microservices | D,F | expert | Spec has the service interaction diagram |
| LH4_staged_deploy | Execute staged deployment | F | hard | Spec has the deployment stages + gates |
| LH5_data_migration | Execute multi-step data migration | F,A | expert | Spec has migration steps + validation checkpoints |

#### POL (Policy) — 2 new tasks (4 total)
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| P3_access_control | Implement RBAC from policy doc | E | hard | Spec has the role-permission matrix |
| P4_data_retention | Implement data retention policy | E,F | hard | Spec has retention rules + deletion order |

### Tier 3: Lower Priority (10 tasks) — Breadth

#### MULTI (Multi-language) — 3 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| MULTI2_api_frontend | Fix backend API + frontend consumer | D | hard | Spec has API contract both sides must satisfy |
| MULTI3_polyglot | Fix bug spanning Python + TypeScript | D | hard | Spec has cross-language interface contract |
| MULTI4_mobile_backend | Fix mobile app + backend sync | D,C | expert | Spec has the sync protocol |

#### NEG (Tradeoff) — 2 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| NEG2_cost_perf | Balance cost vs performance | C | hard | Spec has the cost model + perf targets |
| NEG3_tech_debt | Prioritize tech debt items | C,A | medium | Spec has the prioritization criteria |

#### TEST (Testing) — 3 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| TEST2_regression | Write regression tests from bug report | A | medium | Spec has the bug details + expected behavior |
| TEST3_integration | Write integration tests from contract | D | hard | Spec has the service contract |
| TEST4_property | Write property-based tests from spec | A | hard | Spec has the invariants |

#### IR (Info Retrieval) — 2 new tasks
| ID | Title | Pattern | Difficulty | TNI Driver |
|----|-------|---------|------------|------------|
| IR3_multi_source | Cross-reference 5+ documents | A | hard | Spec has which docs are authoritative |
| IR4_temporal | Resolve conflicting info with timestamps | B | hard | Spec has the temporal priority rules |

## Difficulty Distribution (80 tasks total)

| Tier | Count | % | Target Pass Rate |
|------|-------|---|-----------------|
| Easy | 8 | 10% | 70-90% |
| Medium | 28 | 35% | 35-65% |
| Hard | 32 | 40% | 10-35% |
| Expert | 12 | 15% | 0-15% |

## Domain Distribution (80 tasks total)

| Domain | Count | % |
|--------|-------|---|
| Security (SEC) | 8 | 10% |
| Incident Response (INC) | 8 | 10% |
| Software Engineering (S/GO/JS) | 10 | 12.5% |
| Data/SQL | 7 | 8.75% |
| Pipeline/Integration (PIPE/INT) | 7 | 8.75% |
| Code Review (CR) | 5 | 6.25% |
| Spec-to-Implementation (SPEC) | 5 | 6.25% |
| Operations (O) | 6 | 7.5% |
| Long-Horizon (LH) | 5 | 6.25% |
| Policy/Compliance (P) | 4 | 5% |
| Multi-language (MULTI) | 4 | 5% |
| Testing (TEST) | 4 | 5% |
| Tradeoff/Negotiation (NEG) | 3 | 3.75% |
| Info Retrieval (IR) | 4 | 5% |

## Implementation Priority

1. **Immediate (this week)**: Validate TNI on existing 22 tasks
2. **Week 1-2**: Implement Tier 1 generators (30 new tasks)
3. **Week 3**: Implement Tier 2 generators (18 new tasks)
4. **Week 4**: Implement Tier 3 generators (10 new tasks) + full ablation
5. **Week 5**: Paper writing with real data
