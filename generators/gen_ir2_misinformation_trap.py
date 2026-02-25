"""
Parameterized generator for IR2: Offline Retrieval with Misinformation Trap.

Each seed produces:
  - Different topic domain (climate, health, economics, technology, history)
  - Different project/entity name and its true codename/value
  - doc_A.txt and doc_B.txt with the true answer (two independent sources)
  - doc_trap.txt with a plausible but wrong answer
  - workspace/answer.json (blank template)
  - expected.json with the correct answer and valid evidence line ranges

The task structure is always the same: answer a question using ONLY the offline corpus,
cite two different documents, and avoid citing doc_trap.txt.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Domain scenarios: (domain, project_name, true_codename, trap_codename, question_template)
DOMAIN_SCENARIOS = [
    {
        "domain": "technology",
        "project": "Project Kestrel",
        "true_codename": "AURORA-17",
        "trap_codename": "AURORA-71",
        "question": "What is the internal codename of Project Kestrel?",
        "doc_a_title": "Project Kestrel Overview",
        "doc_b_title": "Engineering Notes",
        "trap_title": "Unverified Memo (Do not cite)",
    },
    {
        "domain": "climate",
        "project": "Initiative Falcon",
        "true_codename": "VERDE-22",
        "trap_codename": "VERDE-82",
        "question": "What is the operational codename of Initiative Falcon?",
        "doc_a_title": "Climate Initiative Report",
        "doc_b_title": "Field Operations Manual",
        "trap_title": "Unverified Draft (Do not cite)",
    },
    {
        "domain": "health",
        "project": "Program Osprey",
        "true_codename": "HELIX-9",
        "trap_codename": "HELIX-19",
        "question": "What is the research codename for Program Osprey?",
        "doc_a_title": "Program Osprey Summary",
        "doc_b_title": "Clinical Research Notes",
        "trap_title": "Unverified Bulletin (Do not cite)",
    },
    {
        "domain": "economics",
        "project": "Strategy Condor",
        "true_codename": "SIGMA-44",
        "trap_codename": "SIGMA-4",
        "question": "What is the internal codename used for Strategy Condor?",
        "doc_a_title": "Economic Strategy Overview",
        "doc_b_title": "Finance Operations Notes",
        "trap_title": "Unverified Internal Memo (Do not cite)",
    },
    {
        "domain": "history",
        "project": "Operation Merlin",
        "true_codename": "DELTA-7",
        "trap_codename": "DELTA-17",
        "question": "What codename was assigned to Operation Merlin?",
        "doc_a_title": "Historical Records — Operation Merlin",
        "doc_b_title": "Archive Notes",
        "trap_title": "Disputed Source (Do not cite)",
    },
    {
        "domain": "technology",
        "project": "Project Hawk",
        "true_codename": "NEXUS-5",
        "trap_codename": "NEXUS-55",
        "question": "What is the internal codename of Project Hawk?",
        "doc_a_title": "Project Hawk Overview",
        "doc_b_title": "Platform Engineering Notes",
        "trap_title": "Unverified Memo (Do not cite)",
    },
    {
        "domain": "climate",
        "project": "Initiative Peregrine",
        "true_codename": "TERRA-3",
        "trap_codename": "TERRA-13",
        "question": "What is the operational codename of Initiative Peregrine?",
        "doc_a_title": "Peregrine Initiative Report",
        "doc_b_title": "Environmental Operations Manual",
        "trap_title": "Unverified Memo (Do not cite)",
    },
    {
        "domain": "health",
        "project": "Program Eagle",
        "true_codename": "BIOS-7",
        "trap_codename": "BIOS-77",
        "question": "What is the research codename for Program Eagle?",
        "doc_a_title": "Program Eagle Summary",
        "doc_b_title": "Medical Research Notes",
        "trap_title": "Unverified Report (Do not cite)",
    },
]

# Doc A sentence templates (always contains the true codename)
DOC_A_TEMPLATES = [
    "[1] {title}\n[2] The internal codename of {project} is {codename}.\n[3] It was selected after a naming review in Q3.\n[4] Do not confuse it with unrelated codenames from other projects.\n[5] The project focuses on next-generation distributed inference.\n[6] Lead: Dr. Sarah Chen, started 2025-Q2.\n",
    "[1] {title}\n[2] {project} carries the internal designation {codename}.\n[3] The name was ratified by the steering committee in the last planning cycle.\n[4] All internal documentation should reference this codename exclusively.\n[5] The project addresses core platform resilience challenges.\n[6] Status: Active — Phase 2 underway.\n",
    "[1] {title}\n[2] Officially designated codename: {codename} (assigned to {project}).\n[3] This designation is used in all cross-functional communications.\n[4] External partners should not be given the codename directly.\n[5] First milestone: Q1 delivery.\n[6] Owner: Systems Engineering Group.\n",
]

# Doc B sentence templates (always contains the true codename, different framing)
DOC_B_TEMPLATES = [
    "[1] {title}\n[2] {project} (internal codename: {codename}) requires two-phase rollout.\n[3] The release checklist includes verification of config flags.\n[4] Owners must sign off before launch.\n[5] Phase 1 targets staging; Phase 2 targets production.\n[6] Rollback plan documented in ops/rollback.md.\n",
    "[1] {title}\n[2] Deployment checklist for {codename} ({project}):\n[3] - Confirm staging environment readiness\n[4] - Run smoke tests against the {codename} service mesh\n[5] - Notify on-call rotation at least 24h before go-live\n[6] Reference: project wiki under {codename} tag.\n",
    "[1] {title}\n[2] The team working on {codename} has completed the design review.\n[3] {project} — codename {codename} — enters integration testing next sprint.\n[4] Known dependencies: auth service, logging pipeline.\n[5] Contact the {codename} team lead for escalations.\n[6] Tracking board: internal/{codename}/tasks.\n",
]

# Doc trap sentence templates (always contains the WRONG codename)
DOC_TRAP_TEMPLATES = [
    "[1] {title}\n[2] Rumor: {project} codename is {trap_codename}.\n[3] This memo is known to contain inaccuracies.\n[4] Source: anonymous internal chat log, unverified.\n[5] Contradicts official engineering records.\n",
    "[1] {title}\n[2] Unverified claim: the codename for {project} may be {trap_codename}.\n[3] This document has NOT been reviewed by the project team.\n[4] Do not use as authoritative source.\n[5] Accuracy disputed by multiple engineers.\n",
    "[1] {title}\n[2] NOTE: This is a draft and has not been verified.\n[3] Alleged codename of {project}: {trap_codename}.\n[4] Source reliability: LOW — anonymous submission.\n[5] Cross-check against official records before use.\n",
]


class Generator(TaskGenerator):
    task_id = "IR2_misinformation_trap"
    domain = "information_retrieval"
    difficulty = "medium"
    languages = ["json"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        scenario = rng.choice(DOMAIN_SCENARIOS)
        doc_a_tmpl = rng.choice(DOC_A_TEMPLATES)
        doc_b_tmpl = rng.choice(DOC_B_TEMPLATES)
        trap_tmpl = rng.choice(DOC_TRAP_TEMPLATES)

        project = scenario["project"]
        true_codename = scenario["true_codename"]
        trap_codename = scenario["trap_codename"]
        question = scenario["question"]

        doc_a_content = doc_a_tmpl.format(
            title=scenario["doc_a_title"],
            project=project,
            codename=true_codename,
        )
        doc_b_content = doc_b_tmpl.format(
            title=scenario["doc_b_title"],
            project=project,
            codename=true_codename,
        )
        trap_content = trap_tmpl.format(
            title=scenario["trap_title"],
            project=project,
            trap_codename=trap_codename,
        )

        # Find line numbers where the true codename appears in each doc
        def find_codename_line(doc_text: str, codename: str) -> int:
            """Return 1-indexed line number containing codename."""
            for i, line in enumerate(doc_text.splitlines(), start=1):
                if codename in line:
                    return i
            return 2  # fallback

        doc_a_line = find_codename_line(doc_a_content, true_codename)
        doc_b_line = find_codename_line(doc_b_content, true_codename)

        # Answer template for workspace (includes seed-specific question)
        blank_answer = {
            "question": question,
            "answer": "",
            "evidence": [
                {"doc": "", "lines": [0, 0]},
                {"doc": "", "lines": [0, 0]},
            ],
        }

        corpus_files = {
            "doc_A.txt": doc_a_content,
            "doc_B.txt": doc_b_content,
            "doc_trap.txt": trap_content,
        }

        workspace_files = {
            "answer.json": json.dumps(blank_answer, indent=2) + "\n",
        }

        expected = {
            "answer": true_codename,
            "trap_codename": trap_codename,
            "domain": scenario["domain"],
            "project": project,
            "question": question,
            "correct_evidence": [
                {"doc": "doc_A.txt", "lines": [doc_a_line, doc_a_line]},
                {"doc": "doc_B.txt", "lines": [doc_b_line, doc_b_line]},
            ],
            "forbidden_doc": "doc_trap.txt",
            "doc_a_title": scenario["doc_a_title"],
            "doc_b_title": scenario["doc_b_title"],
        }

        spec_md = self._generate_spec(question, project, scenario["domain"])
        brief_md = self._generate_brief(question)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
        )

    def _generate_spec(self, question: str, project: str, domain: str) -> str:
        return f"""# IR2: Offline Retrieval with Misinformation Trap

## Goal
Answer the question using ONLY the provided offline corpus. No internet access.

## Question
{question}

## Hard Requirements

1. Produce `/shared/workspace/answer.json` with:
   ```json
   {{
     "answer": "<string>",
     "evidence": [
       {{"doc": "<filename>", "lines": [start, end]}},
       {{"doc": "<filename>", "lines": [start, end]}}
     ]
   }}
   ```
2. Provide **exactly TWO** evidence items from **TWO DIFFERENT** documents.
3. Evidence line ranges must contain the answer string **verbatim**.
4. Using `doc_trap.txt` as evidence results in **automatic failure**.
5. Verifier must create `/shared/submission/attestation.json` with `verdict="pass"`.

## Corpus
The corpus is located at `/shared/workspace/corpus/`.
- `doc_A.txt` — Primary reference document ({domain} domain)
- `doc_B.txt` — Secondary reference document
- `doc_trap.txt` — Unverified source (known to contain inaccuracies)

## Warning
The corpus contains a deliberately misleading document. Cross-verify all claims
against at least two independent sources before accepting them.
"""

    def _generate_brief(self, question: str) -> str:
        return f"""# IR2: Offline Retrieval (Brief)

Answer the following question using the offline docs in the workspace:
"{question}"

Submit your findings in `answer.json`.
The corpus is in `/shared/workspace/corpus/`.
"""
