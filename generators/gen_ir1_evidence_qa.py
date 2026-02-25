"""
Parameterized generator for IR1: Offline Browse — Evidence-Required QA.

Each seed produces:
  - Different project names, budget amounts, dates, and people
  - 3 corpus documents: meeting_notes.txt, budget_summary.txt, project_list.txt
  - 3-5 questions whose answers require cross-referencing multiple documents
  - seed-specific expected.json with correct answers and required citation docs
  - seed-specific spec.md and brief.md
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import (
    SeededRandom, NamePool, ValuePool, BudgetGenerator, PROJECT_NAMES,
)

# Quarter labels for meeting notes
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
FISCAL_YEARS = [2025, 2026, 2027]

# Roles for meeting attendees
ROLES = ["CEO", "CFO", "CTO", "VP Engineering", "VP Product", "VP Finance",
         "Director of Engineering", "Chief Architect", "Head of Operations"]

# Project statuses
STATUSES = ["Active", "Planning", "Paused", "Complete", "Cancelled"]

# Reasons for budget revision
REVISION_REASONS = [
    "additional ML infrastructure",
    "expanded security requirements",
    "new compliance mandates",
    "accelerated delivery timeline",
    "additional headcount",
    "upgraded cloud infrastructure",
    "expanded scope after pilot results",
    "regulatory audit requirements",
]


class Generator(TaskGenerator):
    task_id = "IR1_evidence_qa"
    domain = "information_retrieval"
    difficulty = "medium"
    languages = []

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=30)
        budget_gen = BudgetGenerator(seed + 1)

        # ── Pick seed-specific project names ──
        all_projects = rng.sample(PROJECT_NAMES, 6)
        # The "target" project whose budget is the main question
        target_project = all_projects[0]
        other_projects = all_projects[1:]

        # ── Pick fiscal year and quarter ──
        fy = rng.choice(FISCAL_YEARS)
        quarter = rng.choice(QUARTERS)
        meeting_month_map = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
        meeting_month = meeting_month_map[quarter]
        meeting_day = rng.randint(10, 28)
        meeting_date = f"{fy}-{meeting_month}-{meeting_day:02d}"

        # ── Budget amounts ──
        # Initial budget for target project
        initial_val = round(rng.uniform(1.5, 8.0), 1)
        initial_str = f"${initial_val}M"
        # Revision delta
        delta_val = round(rng.uniform(0.2, 1.5), 1)
        delta_str = f"${delta_val}M"
        # Final approved budget
        final_val = round(initial_val + delta_val, 1)
        final_str = f"${final_val}M"

        # Budgets for other projects (to fill documents)
        other_budgets = []
        dept_total = final_val
        for _ in other_projects:
            v = round(rng.uniform(2.0, 12.0), 1)
            other_budgets.append(v)
            dept_total += v
        dept_total = round(dept_total, 1)

        # ── Meeting attendees ──
        attendee_roles = rng.sample(ROLES, 4)
        attendees = ", ".join(attendee_roles)

        # ── Revision reason ──
        revision_reason = rng.choice(REVISION_REASONS)

        # ── Project leads (for project list) ──
        lead_names = names.get(len(all_projects))
        lead_initials = [f"{n[0]}. {names.next()}" for n in lead_names]

        # ── Project statuses ──
        project_statuses = [rng.choice(STATUSES) for _ in all_projects]
        # Target project must be Active
        project_statuses[0] = "Active"

        # ── Department name ──
        depts = ["Engineering", "Product", "Operations", "Infrastructure", "Data Science"]
        dept_name = rng.choice(depts)

        # ── Generate corpus documents ──
        budget_summary = self._gen_budget_summary(
            fy, dept_name, dept_total,
            target_project, final_val, initial_val,
            other_projects, other_budgets,
        )

        meeting_notes = self._gen_meeting_notes(
            fy, quarter, meeting_date, attendees,
            target_project, initial_val, delta_val, final_val,
            revision_reason,
        )

        project_list = self._gen_project_list(
            fy, all_projects, project_statuses, lead_initials, target_project,
        )

        # ── Generate questions and answers ──
        # Question 1: What was the final approved budget for target_project?
        q1 = f"What was the final budget (in USD) approved for the {target_project} project in fiscal year {fy}?"
        a1 = final_str
        # q1 requires budget_summary (has revised amount) and meeting_notes (has approved amount)
        q1_docs = ["budget_summary.txt", "meeting_notes.txt"]

        # Question 2: What was the original/initial budget before revision?
        q2 = f"What was the original budget for the {target_project} project before the {quarter} FY{fy} revision?"
        a2 = initial_str
        q2_docs = ["meeting_notes.txt", "budget_summary.txt"]

        # Question 3: Who led the target project?
        target_idx = all_projects.index(target_project)
        lead = lead_initials[target_idx]
        q3 = f"Who is the project lead for the {target_project} project according to the project registry?"
        a3 = lead
        q3_docs = ["project_list.txt", "meeting_notes.txt"]

        # Pick how many questions to include (3-5)
        n_questions = rng.randint(3, min(5, 3))  # keep at 3 for clarity in grading
        questions = [
            {"question": q1, "answer": a1, "required_docs": q1_docs},
            {"question": q2, "answer": a2, "required_docs": q2_docs},
            {"question": q3, "answer": a3, "required_docs": q3_docs},
        ][:n_questions]

        # The primary graded question is always Q1 (budget question)
        primary_answer = a1
        primary_docs = q1_docs

        expected = {
            "primary_answer": primary_answer,
            "primary_answer_variants": [
                final_str,
                f"{final_val}M",
                str(int(final_val * 1_000_000)),
                f"{final_val * 1000:.0f}K",
            ],
            "primary_required_docs": primary_docs,
            "target_project": target_project,
            "fiscal_year": fy,
            "initial_budget": initial_str,
            "final_budget": final_str,
            "questions": questions,
        }

        corpus_files = {
            "budget_summary.txt": budget_summary,
            "meeting_notes.txt": meeting_notes,
            "project_list.txt": project_list,
        }

        # Workspace: blank answer.json template seeded with target info
        # (seed-specific so workspace_files differ across seeds for cross-seed validation)
        import json
        answer_template = json.dumps({
            "_task": f"IR1_{target_project}_FY{fy}",
            "answer": "",
            "evidence": [
                {"doc": "", "lines": [0, 0]},
                {"doc": "", "lines": [0, 0]},
            ]
        }, indent=2)

        workspace_files = {
            "answer.json": answer_template,
        }

        spec_md = self._generate_spec(target_project, fy, questions)
        brief_md = self._generate_brief(target_project, fy)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
        )

    def _gen_budget_summary(
        self, fy: int, dept: str, total: float,
        target: str, final_val: float, initial_val: float,
        others: list[str], other_budgets: list[float],
    ) -> str:
        lines = [
            f"[1] FY{fy} Budget Summary",
            f"[2] Department: {dept}",
            f"[3] Total allocated: ${total}M",
            f"[4] Breakdown:",
        ]
        line_num = 5
        for proj, bval in zip(others[:3], other_budgets[:3]):
            lines.append(f"[{line_num}]   - Project {proj}: ${bval}M")
            line_num += 1
        lines.append(
            f"[{line_num}]   - {target}: ${final_val}M (revised from initial ${initial_val}M)"
        )
        line_num += 1
        if len(others) > 3:
            lines.append(f"[{line_num}]   - Project {others[3]}: ${other_budgets[3]}M")
            line_num += 1
        lines.append(f"[{line_num}] Note: {target} budget was revised upward after board approval.")
        return "\n".join(lines) + "\n"

    def _gen_meeting_notes(
        self, fy: int, quarter: str, date: str, attendees: str,
        target: str, initial_val: float, delta_val: float, final_val: float,
        reason: str,
    ) -> str:
        agenda_num = SeededRandom(hash((fy, quarter, target)) & 0xFFFF).randint(2, 5)
        lines = [
            f"[1] Board Meeting Notes — {quarter} FY{fy}",
            f"[2] Date: {date}",
            f"[3] Attendees: {attendees}",
            f"[4]",
            f"[5] Agenda Item {agenda_num}: {target} Budget Revision",
            f"[6] - Original FY{fy} budget: ${initial_val}M",
            f"[7] - Requested increase: ${delta_val}M for {reason}",
            f"[8] - Final approved budget: ${final_val}M",
            f"[9] - Motion passed unanimously",
            f"[10] - CFO noted this aligns with strategic priority framework",
        ]
        return "\n".join(lines) + "\n"

    def _gen_project_list(
        self, fy: int, projects: list[str], statuses: list[str],
        leads: list[str], target: str,
    ) -> str:
        lines = [
            f"[1] Project Registry — FY{fy}",
            f"[2] ID    | Name              | Status   | Lead",
        ]
        for i, (proj, status, lead) in enumerate(zip(projects, statuses, leads)):
            pid = f"P-{100 + i + 1}"
            lines.append(f"[{i + 3}] {pid} | {proj:<17} | {status:<8} | {lead}")
        last = len(projects) + 3
        lines.append(f"[{last}]")
        lines.append(
            f"[{last + 1}] Note: {target} scope expanded. See board notes."
        )
        return "\n".join(lines) + "\n"

    def _generate_spec(self, target: str, fy: int, questions: list[dict]) -> str:
        q_lines = "\n".join(
            f"{i + 1}. {q['question']}" for i, q in enumerate(questions)
        )
        return f"""# IR1: Offline Browse — Evidence-Required QA

## Goal
Answer the questions using ONLY the provided offline corpus. No internet access.
The answers require cross-referencing multiple documents.

## Questions
{q_lines}

## Hard Requirements

1. Produce `answer.json` with the answer to Question 1 and evidence citations:
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
3. Evidence line ranges must contain information supporting the answer.
4. The answer must be a dollar amount string (e.g., "$4.2M").
5. Verifier must create `attestation.json` with `verdict="pass"`.

## Corpus
Located at `corpus/`:
- `budget_summary.txt` — High-level budget allocations
- `meeting_notes.txt` — Board meeting notes with approval details
- `project_list.txt` — Project registry with status info

## Note
The answer requires combining information from at least two documents.
No single document contains the complete answer with full context.
"""

    def _generate_brief(self, target: str, fy: int) -> str:
        return f"""# IR1: Evidence-Required QA (Brief)

Find the final approved budget for the {target} project (FY{fy}).
Use the offline corpus in `corpus/`.
Submit your findings in `answer.json`.
"""
