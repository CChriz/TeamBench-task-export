"""
Multi-agent orchestrator for TeamBench.

Implements the 3-phase sequential protocol:
1. Planning: Planner reads spec → sends plan to Executor
2. Execution: Executor reads brief + messages → fixes workspace → tells Verifier
3. Verification: Verifier reads spec + workspace → writes attestation
4. Remediation: If verdict=fail → Executor gets feedback → re-verify (max 2 loops)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from harness.agent_interface import (
    make_planner_config,
    make_executor_config,
    make_verifier_config,
    make_analysis_planner_config,
    make_expertise_verifier_config,
    RoleConfig,
)
from harness.agent_interface import ToolCallAdapter
from harness.agent_loop import AgentLoop, AgentTurn


@dataclass
class PhaseResult:
    phase: str
    turns: list[AgentTurn] = field(default_factory=list)
    success: bool = True


@dataclass
class OrchestratorResult:
    task_id: str
    phases: list[PhaseResult] = field(default_factory=list)
    verdict: str = "fail"
    remediation_loops: int = 0
    total_turns: int = 0


def _relay_planner_text(turns: list[AgentTurn], messages_dir: str) -> None:
    """If planner produced text but never called send_message, inject it as a message."""
    sent_any = any(
        tc.get("name") == "send_message"
        for t in turns
        for tc in t.tool_calls
    )
    if sent_any:
        return

    # Collect all planner text
    text = "\n".join(t.text for t in turns if t.text).strip()
    if not text:
        return

    # Remove trailing DONE markers
    for marker in ["DONE", "TASK_COMPLETE"]:
        if text.endswith(marker):
            text = text[: -len(marker)].strip()

    print("  [orchestrator] Planner did not use send_message — relaying text to executor")
    msg = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "role": "planner",
        "type": "message",
        "to": "executor",
        "content": text,
    }
    log_path = os.path.join(messages_dir, "dialogue.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")


class TaskOrchestrator:
    """Coordinate Planner → Executor → Verifier for a single task."""

    def __init__(
        self,
        task_dir: str,
        run_dir: str,
        adapter: ToolCallAdapter,
        max_turns_per_phase: int = 20,
        max_remediation_loops: int = 2,
    ):
        self.task_dir = task_dir
        self.run_dir = run_dir
        self.adapter = adapter
        self.max_turns_per_phase = max_turns_per_phase
        self.max_remediation_loops = max_remediation_loops

        # Run directories
        self.workspace = os.path.join(run_dir, "workspace")
        self.reports = os.path.join(run_dir, "reports")
        self.messages = os.path.join(run_dir, "messages")
        self.submission = os.path.join(run_dir, "submission")

        # Task files
        self.spec_path = os.path.join(task_dir, "spec.md")
        self.brief_path = os.path.join(task_dir, "brief.md")

    def run(self) -> OrchestratorResult:
        """Execute the full 3-phase protocol with remediation loop."""
        task_id = os.path.basename(self.task_dir)
        result = OrchestratorResult(task_id=task_id)

        # Read task files for prompts
        spec_text = self._read_file(self.spec_path)
        brief_text = self._read_file(self.brief_path)

        # === Phase 1: Planning ===
        print(f"\n{'='*50}")
        print(f"  PHASE 1: PLANNING")
        print(f"{'='*50}")

        planner_config = make_planner_config(
            spec_path=self.spec_path,
            messages_dir=self.messages,
            task_dir=self.task_dir,
        )
        planner_loop = AgentLoop(
            role_config=planner_config,
            adapter=self.adapter,
            messages_dir=self.messages,
            log_dir=os.path.join(self.run_dir, "logs", "planner"),
            max_turns=self.max_turns_per_phase,
        )

        planner_prompt = (
            f"You are the Planner for task: {task_id}\n\n"
            f"## Full Specification\n{spec_text}\n\n"
            f"## Instructions\n"
            f"1. Read and understand all requirements in the specification.\n"
            f"2. Create a detailed plan for the Executor.\n"
            f"3. IMPORTANT: Send the plan to the Executor by calling: "
            f"send_message(to='executor', content='<your detailed plan>')\n"
            f"4. Include ALL specific requirements, exact values, edge cases, and constraints.\n"
            f"5. The Executor only has a brief summary — they need YOUR detailed instructions.\n"
            f"6. When done sending the plan, output DONE."
        )

        planner_turns = planner_loop.run(planner_prompt)
        phase1 = PhaseResult(phase="planning", turns=planner_turns)
        result.phases.append(phase1)
        result.total_turns += len(planner_turns)

        # Safety: relay planner text as message if it forgot to use send_message
        _relay_planner_text(planner_turns, self.messages)

        # === Phase 2: Execution ===
        print(f"\n{'='*50}")
        print(f"  PHASE 2: EXECUTION")
        print(f"{'='*50}")

        executor_config = make_executor_config(
            brief_path=self.brief_path,
            workspace_dir=self.workspace,
            reports_dir=self.reports,
            messages_dir=self.messages,
            submission_dir=self.submission,
            task_dir=self.task_dir,
        )
        executor_loop = AgentLoop(
            role_config=executor_config,
            adapter=self.adapter,
            messages_dir=self.messages,
            log_dir=os.path.join(self.run_dir, "logs", "executor"),
            max_turns=self.max_turns_per_phase,
        )

        executor_prompt = (
            f"You are the Executor for task: {task_id}\n\n"
            f"## Brief\n{brief_text}\n\n"
            f"## Instructions\n"
            f"1. Check messages from the Planner for detailed instructions.\n"
            f"2. Explore the workspace using run(cmd='ls -R') or read(path='<relative_path>').\n"
            f"3. Use relative paths for files (e.g., read(path='app/main.py')).\n"
            f"4. Follow the Planner's instructions to fix the code/config.\n"
            f"5. Write files using write(path='<relative_path>', content='...').\n"
            f"6. Run tests or validation using run(cmd='...').\n"
            f"7. Send a completion message to the Verifier: "
            f"send_message(to='verifier', content='Work complete.').\n"
            f"8. When done, output DONE."
        )

        executor_turns = executor_loop.run(executor_prompt)
        phase2 = PhaseResult(phase="execution", turns=executor_turns)
        result.phases.append(phase2)
        result.total_turns += len(executor_turns)

        # === Phase 3: Verification + Remediation Loop ===
        for loop_num in range(self.max_remediation_loops + 1):
            print(f"\n{'='*50}")
            print(f"  PHASE 3: VERIFICATION (attempt {loop_num + 1})")
            print(f"{'='*50}")

            verifier_config = make_verifier_config(
                spec_path=self.spec_path,
                workspace_dir=self.workspace,
                reports_dir=self.reports,
                messages_dir=self.messages,
                submission_dir=self.submission,
                task_dir=self.task_dir,
            )
            verifier_loop = AgentLoop(
                role_config=verifier_config,
                adapter=self.adapter,
                messages_dir=self.messages,
                log_dir=os.path.join(self.run_dir, "logs", "verifier", f"attempt_{loop_num}"),
                max_turns=self.max_turns_per_phase,
            )

            verifier_prompt = (
                f"You are the Verifier for task: {task_id}\n\n"
                f"## Full Specification\n{spec_text}\n\n"
                f"## Instructions\n"
                f"1. Read the specification carefully.\n"
                f"2. Check the workspace files to verify all requirements are met.\n"
                f"   Use read(path='app/main.py') etc. with relative paths to workspace.\n"
                f"3. For EACH requirement, verify compliance.\n"
                f"4. Write attestation.json. IMPORTANT: The content MUST be valid JSON.\n"
                f"   Do NOT use quotes or special characters inside note strings.\n"
                f"   Example:\n"
                f"   write(path='attestation.json', content='{{"
                f"\"task_id\":\"{task_id}\","
                f"\"verdict\":\"pass\","
                f"\"checklist\":["
                f"{{\"id\":\"req_1\",\"ok\":true,\"note\":\"requirement met\"}},"
                f"{{\"id\":\"req_2\",\"ok\":true,\"note\":\"verified correct\"}}"
                f"]}}')\n"
                f"5. If verdict is 'fail', send feedback to executor via send_message.\n"
                f"6. Output DONE when finished."
            )

            verifier_turns = verifier_loop.run(verifier_prompt)
            phase3 = PhaseResult(phase=f"verification_{loop_num}", turns=verifier_turns)
            result.phases.append(phase3)
            result.total_turns += len(verifier_turns)

            # Check attestation
            verdict = self._check_attestation()
            if verdict == "pass":
                result.verdict = "pass"
                result.remediation_loops = loop_num
                print(f"\n  VERDICT: PASS (after {loop_num} remediation loops)")
                return result

            # If fail and we have remediation attempts left
            if loop_num < self.max_remediation_loops:
                print(f"\n  VERDICT: FAIL — starting remediation loop {loop_num + 1}")
                result.remediation_loops = loop_num + 1

                # Re-run executor with feedback
                executor_loop2 = AgentLoop(
                    role_config=executor_config,
                    adapter=self.adapter,
                    messages_dir=self.messages,
                    log_dir=os.path.join(self.run_dir, "logs", "executor", f"remediation_{loop_num}"),
                    max_turns=self.max_turns_per_phase,
                )

                remediation_prompt = (
                    f"You are the Executor for task: {task_id}\n\n"
                    f"## Brief\n{brief_text}\n\n"
                    f"## Instructions\n"
                    f"The Verifier found issues with your work. Check messages for feedback.\n"
                    f"Use relative paths for file reads/writes (e.g., 'app/main.py').\n"
                    f"Fix the issues and notify the Verifier when done.\n"
                    f"Output DONE when finished."
                )

                executor_turns2 = executor_loop2.run(remediation_prompt)
                phase_fix = PhaseResult(phase=f"remediation_{loop_num}", turns=executor_turns2)
                result.phases.append(phase_fix)
                result.total_turns += len(executor_turns2)

        print(f"\n  FINAL VERDICT: FAIL (exhausted {self.max_remediation_loops} remediation attempts)")
        return result

    def _read_file(self, path: str) -> str:
        """Read a text file, return empty string if missing."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def _check_attestation(self) -> str:
        """Check attestation.json verdict. Returns 'pass', 'fail', or 'missing'."""
        att_path = os.path.join(self.submission, "attestation.json")
        try:
            with open(att_path, "r", encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            return "missing"

        # Try direct parse
        try:
            att = json.loads(raw)
            return att.get("verdict", "fail")
        except json.JSONDecodeError:
            pass

        # Attempt repair: extract verdict via regex
        import re
        m = re.search(r'"verdict"\s*:\s*"(pass|fail)"', raw)
        if m:
            verdict = m.group(1)
            print(f"  [orchestrator] Repaired invalid attestation JSON, verdict={verdict}")
            # Rewrite a clean attestation
            clean = {"task_id": os.path.basename(self.task_dir), "verdict": verdict, "checklist": []}
            with open(att_path, "w", encoding="utf-8") as f:
                json.dump(clean, f)
            return verdict

        return "missing"


class ExpertiseOrchestrator:
    """
    Expertise-Asymmetry orchestrator for TeamBench.

    3-phase protocol:
    Phase 1a: Planner runs static analysis (max 15 turns), writes analysis/planner_report.md
    Phase 2+1b: Executor implementation (up to 20 turns) interleaved with Planner Q&A
               (up to 2 Q&A rounds of 5 turns each after every 5 executor turns)
    Phase 3: Verifier runs tests to verify (max 15 turns) + remediation loop (max 2)
    """

    def __init__(
        self,
        task_dir: str,
        run_dir: str,
        adapter: ToolCallAdapter,
        max_planner_turns: int = 15,
        max_executor_turns: int = 20,
        max_verifier_turns: int = 15,
        max_remediation_loops: int = 2,
        qa_interval: int = 5,
        max_qa_rounds: int = 2,
        qa_turns_per_round: int = 5,
    ):
        self.task_dir = task_dir
        self.run_dir = run_dir
        self.adapter = adapter
        self.max_planner_turns = max_planner_turns
        self.max_executor_turns = max_executor_turns
        self.max_verifier_turns = max_verifier_turns
        self.max_remediation_loops = max_remediation_loops
        self.qa_interval = qa_interval
        self.max_qa_rounds = max_qa_rounds
        self.qa_turns_per_round = qa_turns_per_round

        # Run directories
        self.workspace = os.path.join(run_dir, "workspace")
        self.reports = os.path.join(run_dir, "reports")
        self.messages = os.path.join(run_dir, "messages")
        self.submission = os.path.join(run_dir, "submission")
        self.analysis = os.path.join(run_dir, "analysis")

        # Task files
        self.spec_path = os.path.join(task_dir, "spec.md")
        self.brief_path = os.path.join(task_dir, "brief.md")

    def run(self) -> OrchestratorResult:
        """Execute the full expertise protocol with concurrent Q&A."""
        task_id = os.path.basename(self.task_dir)
        result = OrchestratorResult(task_id=task_id)

        spec_text = self._read_file(self.spec_path)
        brief_text = self._read_file(self.brief_path)

        # Ensure analysis directory exists
        self._ensure_analysis_dir()

        # === Phase 1a: Planner Analysis ===
        print(f"\n{'='*50}")
        print(f"  PHASE 1a: PLANNER ANALYSIS")
        print(f"{'='*50}")

        planner_config = make_analysis_planner_config(
            spec_path=self.spec_path,
            messages_dir=self.messages,
            workspace_dir=self.workspace,
            analysis_dir=self.analysis,
            task_dir=self.task_dir,
        )
        planner_loop = AgentLoop(
            role_config=planner_config,
            adapter=self.adapter,
            messages_dir=self.messages,
            log_dir=os.path.join(self.run_dir, "logs", "planner_analysis"),
            max_turns=self.max_planner_turns,
        )

        planner_analysis_prompt = (
            f"You are the Planner for task: {task_id}\n\n"
            f"## Full Specification\n{spec_text}\n\n"
            f"## Instructions\n"
            f"PHASE 1 — Perform static analysis of the workspace:\n"
            f"1. Explore the workspace structure\n"
            f"2. Run static analysis tools (bandit, ruff, mypy, etc.)\n"
            f"3. Write your findings to /analysis/planner_report.md\n"
            f"4. Send a summary of key findings to the executor\n"
            f"Output DONE when your analysis report is written."
        )

        planner_analysis_turns = planner_loop.run(planner_analysis_prompt)
        phase1a = PhaseResult(phase="planner_analysis", turns=planner_analysis_turns)
        result.phases.append(phase1a)
        result.total_turns += len(planner_analysis_turns)

        # Safety relay if planner didn't use send_message
        _relay_planner_text(planner_analysis_turns, self.messages)

        # === Phase 2+1b: Executor + Planner Q&A (interleaved) ===
        print(f"\n{'='*50}")
        print(f"  PHASE 2: EXECUTION (with Planner Q&A)")
        print(f"{'='*50}")

        executor_config = make_executor_config(
            brief_path=self.brief_path,
            workspace_dir=self.workspace,
            reports_dir=self.reports,
            messages_dir=self.messages,
            submission_dir=self.submission,
            task_dir=self.task_dir,
        )

        # Build executor prompt — include analysis report hint
        analysis_report_path = os.path.join(self.analysis, "planner_report.md")
        analysis_hint = ""
        if os.path.isfile(analysis_report_path):
            analysis_hint = (
                f"\nThe Planner has written a static analysis report at /analysis/planner_report.md — "
                f"read it for pre-computed findings before starting work.\n"
            )

        executor_prompt = (
            f"You are the Executor for task: {task_id}\n\n"
            f"## Brief\n{brief_text}\n"
            f"{analysis_hint}\n"
            f"## Instructions\n"
            f"1. Read the Planner's analysis report (if available) for pre-computed findings.\n"
            f"2. Check messages from the Planner for their summary.\n"
            f"3. Explore the workspace and implement the required fixes.\n"
            f"4. You can ask the Planner questions via send_message(to='planner', content='...')\n"
            f"5. When done, send a completion message to the Verifier.\n"
            f"Output DONE when finished."
        )

        all_executor_turns = []
        qa_rounds_done = 0

        # Create a single executor loop but run it in intervals
        executor_loop = AgentLoop(
            role_config=executor_config,
            adapter=self.adapter,
            messages_dir=self.messages,
            log_dir=os.path.join(self.run_dir, "logs", "executor"),
            max_turns=self.max_executor_turns,
        )
        executor_turns = executor_loop.run(executor_prompt)
        all_executor_turns.extend(executor_turns)

        # Check if executor asked questions and run Q&A rounds
        # (simplified: run up to max_qa_rounds of planner Q&A after executor finishes)
        for qa_round in range(self.max_qa_rounds):
            qa_turns = self._run_planner_qa_round(
                qa_round=qa_round,
                spec_text=spec_text,
                planner_config=planner_config,
                task_id=task_id,
            )
            if qa_turns:
                phase_qa = PhaseResult(phase=f"planner_qa_{qa_round}", turns=qa_turns)
                result.phases.append(phase_qa)
                result.total_turns += len(qa_turns)
                qa_rounds_done += 1
            else:
                break  # No messages to answer

        phase2 = PhaseResult(phase="execution", turns=all_executor_turns)
        result.phases.append(phase2)
        result.total_turns += len(all_executor_turns)

        # === Phase 3: Verifier Test Execution + Remediation ===
        for loop_num in range(self.max_remediation_loops + 1):
            print(f"\n{'='*50}")
            print(f"  PHASE 3: VERIFICATION (attempt {loop_num + 1})")
            print(f"{'='*50}")

            verifier_config = make_expertise_verifier_config(
                spec_path=self.spec_path,
                workspace_dir=self.workspace,
                reports_dir=self.reports,
                messages_dir=self.messages,
                submission_dir=self.submission,
                task_dir=self.task_dir,
            )
            verifier_loop = AgentLoop(
                role_config=verifier_config,
                adapter=self.adapter,
                messages_dir=self.messages,
                log_dir=os.path.join(self.run_dir, "logs", "verifier", f"attempt_{loop_num}"),
                max_turns=self.max_verifier_turns,
            )

            verifier_prompt = (
                f"You are the Verifier for task: {task_id}\n\n"
                f"## Full Specification\n{spec_text}\n\n"
                f"## Instructions\n"
                f"1. Read the specification carefully.\n"
                f"2. Run the test suite to verify correctness.\n"
                f"3. Check each requirement against test results.\n"
                f"4. Write attestation.json with evidence (test pass/fail counts).\n"
                f"   Example: write(path='attestation.json', content='"
                f'{{"task_id":"{task_id}","verdict":"pass","checklist":[],"test_results":"all passed"}}'
                f"')\n"
                f"5. If fail, send test output to executor.\n"
                f"Output DONE when finished."
            )

            verifier_turns = verifier_loop.run(verifier_prompt)
            phase3 = PhaseResult(phase=f"verification_{loop_num}", turns=verifier_turns)
            result.phases.append(phase3)
            result.total_turns += len(verifier_turns)

            verdict = self._check_attestation()
            if verdict == "pass":
                result.verdict = "pass"
                result.remediation_loops = loop_num
                print(f"\n  VERDICT: PASS (after {loop_num} remediation loops)")
                return result

            if loop_num < self.max_remediation_loops:
                print(f"\n  VERDICT: FAIL — starting remediation loop {loop_num + 1}")
                result.remediation_loops = loop_num + 1

                executor_loop2 = AgentLoop(
                    role_config=executor_config,
                    adapter=self.adapter,
                    messages_dir=self.messages,
                    log_dir=os.path.join(self.run_dir, "logs", "executor", f"remediation_{loop_num}"),
                    max_turns=self.max_executor_turns,
                )
                remediation_prompt = (
                    f"You are the Executor for task: {task_id}\n\n"
                    f"## Brief\n{brief_text}\n\n"
                    f"## Instructions\n"
                    f"The Verifier found issues. Check messages for test failure details.\n"
                    f"Fix the failing tests and notify the Verifier when done.\n"
                    f"Output DONE when finished."
                )
                executor_turns2 = executor_loop2.run(remediation_prompt)
                phase_fix = PhaseResult(phase=f"remediation_{loop_num}", turns=executor_turns2)
                result.phases.append(phase_fix)
                result.total_turns += len(executor_turns2)

        print(f"\n  FINAL VERDICT: FAIL (exhausted {self.max_remediation_loops} remediation attempts)")
        return result

    def _run_planner_qa_round(
        self,
        qa_round: int,
        spec_text: str,
        planner_config: "RoleConfig",
        task_id: str,
    ) -> list:
        """Check for unanswered executor messages and run Planner Q&A round."""
        # Check if there are any messages TO planner not yet answered
        dialogue_path = os.path.join(self.messages, "dialogue.jsonl")
        if not os.path.isfile(dialogue_path):
            return []

        messages_to_planner = []
        answered_by_planner = set()

        with open(dialogue_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            try:
                msg = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            if msg.get("to") == "planner" and msg.get("role") != "planner":
                messages_to_planner.append((i, msg))
            elif msg.get("role") == "planner" and msg.get("to") == "executor":
                # Planner responded — track by round number
                answered_by_planner.add(qa_round - 1)

        if not messages_to_planner:
            return []  # No questions to answer

        print(f"\n  Q&A ROUND {qa_round + 1}: Planner answering {len(messages_to_planner)} executor question(s)")

        qa_loop = AgentLoop(
            role_config=planner_config,
            adapter=self.adapter,
            messages_dir=self.messages,
            log_dir=os.path.join(self.run_dir, "logs", f"planner_qa_{qa_round}"),
            max_turns=self.qa_turns_per_round,
        )

        qa_prompt = (
            f"You are the Planner for task: {task_id} — Q&A Phase\n\n"
            f"The Executor has sent you questions. Check your messages and answer them.\n"
            f"Reference the spec and your analysis report as needed.\n"
            f"Send answers via send_message(to='executor', content='...')\n"
            f"Output DONE when done answering."
        )

        return qa_loop.run(qa_prompt)

    def _ensure_analysis_dir(self) -> None:
        """Create the analysis directory before planner runs."""
        os.makedirs(self.analysis, exist_ok=True)

    def _read_file(self, path: str) -> str:
        """Read a text file, return empty string if missing."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def _check_attestation(self) -> str:
        """Check attestation.json verdict. Returns 'pass', 'fail', or 'missing'."""
        att_path = os.path.join(self.submission, "attestation.json")
        try:
            with open(att_path, "r", encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            return "missing"

        try:
            att = json.loads(raw)
            return att.get("verdict", "fail")
        except json.JSONDecodeError:
            pass

        import re
        m = re.search(r'"verdict"\s*:\s*"(pass|fail)"', raw)
        if m:
            verdict = m.group(1)
            print(f"  [expertise-orchestrator] Repaired invalid attestation JSON, verdict={verdict}")
            clean = {"task_id": os.path.basename(self.task_dir), "verdict": verdict, "checklist": []}
            with open(att_path, "w", encoding="utf-8") as f:
                json.dump(clean, f)
            return verdict

        return "missing"
