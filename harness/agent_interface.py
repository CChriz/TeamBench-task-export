"""
TeamBench Agent Driver Interface.

Any LLM (OpenAI, Gemini, Claude, OSS) can be plugged in by implementing ModelAdapter
or ToolCallAdapter.
RoleAgent wraps a ModelAdapter with role-specific constraints and tool access.

This is the standard contract for running automated evaluations.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import json
import os
import subprocess


class ModelAdapter(ABC):
    """
    Minimal interface for any LLM backend.
    Implement this for OpenAI, Anthropic, Google, vLLM, etc.
    """

    @abstractmethod
    def generate(self, messages: list[dict], **kwargs) -> str:
        """
        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        Returns:
            Assistant response text.
        """
        raise NotImplementedError


@dataclass
class AdapterResponse:
    """Standardized response from any model adapter."""
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # [{"name": "...", "args": {...}}]
    done: bool = False  # True if model signaled completion


class ToolCallAdapter(ABC):
    """Interface for LLM backends that support tool calling."""

    @abstractmethod
    def generate_with_tools(
        self,
        messages: list[dict],  # {"role": "user"|"assistant"|"tool", "content": ...}
        system_prompt: str,
        tools: list[dict],  # Tool declarations in standard format
    ) -> AdapterResponse:
        """Generate a response, potentially with tool calls."""
        raise NotImplementedError

    @abstractmethod
    def get_usage(self) -> dict:
        """Return token usage stats."""
        raise NotImplementedError


def tools_to_standard_declarations(tools: "list[Tool]") -> list[dict]:
    """Convert Tool objects to a model-agnostic tool declaration format.

    Produces JSON-Schema-style dicts that each adapter converts to its
    provider-specific format (Gemini FunctionDeclaration, OpenAI functions, etc.).
    """
    schema_map = {
        "run": {
            "name": "run",
            "description": "Execute a shell command in the workspace. Returns stdout, stderr, and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["cmd"],
            },
        },
        "read": {
            "name": "read",
            "description": "Read the contents of a file. Path must be within allowed directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                },
                "required": ["path"],
            },
        },
        "write": {
            "name": "write",
            "description": "Write content to a file. Path must be within allowed directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                },
                "required": ["path", "content"],
            },
        },
        "send_message": {
            "name": "send_message",
            "description": "Send a message to another agent role (planner, executor, or verifier).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Target role: planner, executor, or verifier"},
                    "content": {"type": "string", "description": "Message content"},
                },
                "required": ["to", "content"],
            },
        },
    }
    result = []
    for tool in tools:
        if tool.name in schema_map:
            result.append(schema_map[tool.name])
    return result


@dataclass
class ToolResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


class Tool(ABC):
    """Base class for tools available to agents."""
    name: str

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError


class RunCommandTool(Tool):
    """Execute a shell command in the workspace."""
    name = "run"

    def __init__(self, cwd: str, allowed: bool = True, allowed_commands: list[str] | None = None):
        self.cwd = cwd
        self.allowed = allowed
        self.allowed_commands = allowed_commands

    def execute(self, cmd: str = "", **kwargs) -> ToolResult:
        if not cmd:
            return ToolResult(stderr="Error: 'cmd' parameter is required", exit_code=1)
        if not self.allowed:
            return ToolResult(stderr="Permission denied: this role cannot execute commands.", exit_code=1)
        if self.allowed_commands is not None:
            import shlex
            try:
                first_token = shlex.split(cmd)[0] if cmd.strip() else ""
            except ValueError:
                first_token = ""
            if first_token not in self.allowed_commands:
                return ToolResult(
                    stderr=f"Permission denied: command '{first_token}' not in analysis allow-list. "
                           f"Allowed: {', '.join(self.allowed_commands)}",
                    exit_code=1,
                )
        try:
            res = subprocess.run(
                cmd, shell=True, cwd=self.cwd,
                text=True, capture_output=True, timeout=60,
            )
            return ToolResult(stdout=res.stdout, stderr=res.stderr, exit_code=res.returncode)
        except subprocess.TimeoutExpired:
            return ToolResult(stderr="Command timed out (60s).", exit_code=124)


class ReadFileTool(Tool):
    """Read a file from an allowed path."""
    name = "read"

    def __init__(self, allowed_roots: list[str], path_map: dict[str, str] | None = None, base_dir: str = ""):
        self.allowed_roots = [os.path.abspath(r) for r in allowed_roots]
        self.path_map = path_map or {}
        self.base_dir = os.path.abspath(base_dir) if base_dir else self.allowed_roots[0]

    def _resolve(self, path: str) -> str:
        # Apply path mapping (e.g., /shared/workspace -> actual run dir)
        for prefix, replacement in self.path_map.items():
            if path.startswith(prefix):
                return os.path.join(replacement, path[len(prefix):].lstrip("/"))
        # Resolve relative paths against base_dir
        if not os.path.isabs(path):
            return os.path.join(self.base_dir, path)
        return os.path.abspath(path)

    def execute(self, path: str = "", **kwargs) -> ToolResult:
        if not path:
            return ToolResult(stderr="Error: 'path' parameter is required", exit_code=1)
        abs_path = self._resolve(path)
        if not any(abs_path.startswith(root) for root in self.allowed_roots):
            return ToolResult(stderr=f"Permission denied: cannot read {path}", exit_code=1)
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                return ToolResult(stdout=f.read())
        except Exception as e:
            return ToolResult(stderr=str(e), exit_code=1)


class WriteFileTool(Tool):
    """Write a file to an allowed path."""
    name = "write"

    def __init__(self, allowed_roots: list[str], path_map: dict[str, str] | None = None, base_dir: str = ""):
        self.allowed_roots = [os.path.abspath(r) for r in allowed_roots]
        self.path_map = path_map or {}
        self.base_dir = os.path.abspath(base_dir) if base_dir else self.allowed_roots[0]

    def _resolve(self, path: str) -> str:
        for prefix, replacement in self.path_map.items():
            if path.startswith(prefix):
                return os.path.join(replacement, path[len(prefix):].lstrip("/"))
        if not os.path.isabs(path):
            return os.path.join(self.base_dir, path)
        return os.path.abspath(path)

    def execute(self, path: str = "", content: str = "", **kwargs) -> ToolResult:
        if not path:
            return ToolResult(stderr="Error: 'path' parameter is required", exit_code=1)
        if not content and content != "":
            return ToolResult(stderr="Error: 'content' parameter is required", exit_code=1)
        abs_path = self._resolve(path)
        if not any(abs_path.startswith(root) for root in self.allowed_roots):
            return ToolResult(stderr=f"Permission denied: cannot write {path}", exit_code=1)
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(stdout=f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(stderr=str(e), exit_code=1)


class SendMessageTool(Tool):
    """Send a message to another role via the shared message log."""
    name = "send_message"

    def __init__(self, messages_dir: str, sender_role: str):
        self.messages_dir = messages_dir
        self.sender_role = sender_role

    def execute(self, to: str = "", content: str = "", **kwargs) -> ToolResult:
        if not to:
            return ToolResult(stderr="Error: 'to' parameter is required (e.g., 'executor', 'verifier')", exit_code=1)
        if not content:
            return ToolResult(stderr="Error: 'content' parameter is required", exit_code=1)
        from datetime import datetime, timezone
        msg = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": self.sender_role,
            "type": "message",
            "to": to,
            "content": content,
        }
        log_path = os.path.join(self.messages_dir, "dialogue.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return ToolResult(stdout=f"Message sent to {to}")


@dataclass
class RoleConfig:
    """Configuration for a role agent's permissions and tools."""
    role: str  # planner | executor | verifier
    system_prompt: str
    tools: list[Tool]


def _build_path_map(
    workspace_dir: str = "",
    reports_dir: str = "",
    messages_dir: str = "",
    submission_dir: str = "",
    task_dir: str = "",
) -> dict[str, str]:
    """Build Docker-path → actual-path mapping for non-Docker agent runs."""
    m: dict[str, str] = {}
    if workspace_dir:
        m["/shared/workspace/"] = os.path.abspath(workspace_dir)
        m["/shared/workspace"] = os.path.abspath(workspace_dir)
    if reports_dir:
        m["/shared/reports/"] = os.path.abspath(reports_dir)
        m["/shared/reports"] = os.path.abspath(reports_dir)
    if messages_dir:
        m["/shared/messages/"] = os.path.abspath(messages_dir)
        m["/shared/messages"] = os.path.abspath(messages_dir)
    if submission_dir:
        m["/shared/submission/"] = os.path.abspath(submission_dir)
        m["/shared/submission"] = os.path.abspath(submission_dir)
    if task_dir:
        m["/task/"] = os.path.abspath(task_dir)
        m["/task"] = os.path.abspath(task_dir)
    return m


def make_planner_config(
    spec_path: str,
    messages_dir: str,
    task_dir: str = "",
) -> RoleConfig:
    """Create Planner role config: can read spec, send messages, no execution."""
    if not task_dir:
        task_dir = os.path.dirname(spec_path)
    pm = _build_path_map(messages_dir=messages_dir, task_dir=task_dir)
    return RoleConfig(
        role="planner",
        system_prompt=(
            "You are the Planner. You have access to the full task specification.\n"
            "Your job is to understand the requirements, decompose the goal, and create a clear plan.\n"
            "You CANNOT execute commands or modify the workspace.\n"
            "You MUST communicate your plan to the Executor by calling the send_message tool.\n"
            "Do NOT just write the plan as text — you MUST use send_message(to='executor', content=...).\n"
            "Highlight hidden constraints and edge cases the Executor might miss."
        ),
        tools=[
            ReadFileTool(allowed_roots=[os.path.dirname(spec_path), messages_dir], path_map=pm),
            SendMessageTool(messages_dir=messages_dir, sender_role="planner"),
        ],
    )


# Allowed commands for analysis planner
_ANALYSIS_PLANNER_COMMANDS = [
    "bandit", "ruff", "pylint", "mypy", "semgrep",
    "find", "ls", "cat", "head", "grep", "wc",
    "python", "python3",
]

_ANALYSIS_PLANNER_PROMPT = """\
You are the Planner. You are a static analysis expert with read-only access to the codebase.

PHASE 1 — ANALYSIS (do this first):
1. Explore workspace: run(cmd='find /workspace -name "*.py" | head -50')
2. Check if /task/analysis_guidance.md exists: read(path='/task/analysis_guidance.md')
   If it exists, read it for task-specific guidance before running tools.
3. Run static analysis:
   - Security: run(cmd='bandit -r /workspace -f json -q 2>/dev/null || bandit -r /workspace -q')
   - Style/bugs: run(cmd='ruff check /workspace 2>/dev/null || echo "ruff not available"')
   - Types: run(cmd='mypy /workspace --ignore-missing-imports 2>&1 | head -50')
4. Read the spec to understand requirements
5. Write a report: write(path='/analysis/planner_report.md', content='# Analysis Report\\n...')
   Include: findings, severity, exact file:line references, false positives to ignore, action priority
6. Send summary: send_message(to='executor', content='Analysis complete. Key findings: ...')

PHASE 2 — Q&A (answer executor questions):
- Monitor for messages from executor
- Answer clarifying questions about requirements or findings
- Do NOT execute commands on their behalf

You CANNOT edit workspace files.
"""


def make_analysis_planner_config(
    spec_path: str,
    messages_dir: str,
    workspace_dir: str,
    analysis_dir: str,
    task_dir: str = "",
) -> RoleConfig:
    """Create Analysis Planner config: static analysis tools + read-only workspace access."""
    if not task_dir:
        task_dir = os.path.dirname(spec_path)
    pm = _build_path_map(
        workspace_dir=workspace_dir,
        messages_dir=messages_dir,
        task_dir=task_dir,
    )
    # Add analysis dir mapping
    pm["/analysis/"] = os.path.abspath(analysis_dir)
    pm["/analysis"] = os.path.abspath(analysis_dir)
    # Add workspace mapping for /workspace path
    pm["/workspace/"] = os.path.abspath(workspace_dir)
    pm["/workspace"] = os.path.abspath(workspace_dir)

    return RoleConfig(
        role="planner",
        system_prompt=_ANALYSIS_PLANNER_PROMPT,
        tools=[
            RunCommandTool(
                cwd=workspace_dir,
                allowed=True,
                allowed_commands=_ANALYSIS_PLANNER_COMMANDS,
            ),
            ReadFileTool(
                allowed_roots=[
                    os.path.dirname(spec_path),
                    workspace_dir,
                    messages_dir,
                    task_dir,
                ],
                path_map=pm,
                base_dir=workspace_dir,
            ),
            WriteFileTool(
                allowed_roots=[os.path.abspath(analysis_dir)],
                path_map=pm,
                base_dir=os.path.abspath(analysis_dir),
            ),
            SendMessageTool(messages_dir=messages_dir, sender_role="planner"),
        ],
    )


# Allowed commands for expertise verifier
_EXPERTISE_VERIFIER_COMMANDS = ["pytest", "python", "python3", "bash", "sh", "mutmut"]

_EXPERTISE_VERIFIER_PROMPT = """\
You are the Verifier. You verify correctness by RUNNING tests, not just reading code.

Workflow:
1. Read the spec to understand all requirements
2. Run the test suite: run(cmd='cd /workspace && python -m pytest -v 2>&1')
   Or if there's a specific test file: run(cmd='cd /workspace && python -m pytest test_*.py -v 2>&1')
3. Check each spec requirement against test results
4. For requirements without tests, inspect the code with read()
5. Write attestation with evidence: include test pass/fail counts in your checklist
   write(path='attestation.json', content='{"task_id":"...","verdict":"pass","checklist":[...]}')
6. If fail: send test failure output to executor so they know exactly what broke
   send_message(to='executor', content='Tests failed: ...')

You CANNOT edit workspace files.
When done, output DONE.
"""


def make_expertise_verifier_config(
    spec_path: str,
    workspace_dir: str,
    reports_dir: str,
    messages_dir: str,
    submission_dir: str,
    task_dir: str = "",
) -> RoleConfig:
    """Create Expertise Verifier config: can run tests to verify correctness."""
    if not task_dir:
        task_dir = os.path.dirname(spec_path)
    pm = _build_path_map(
        workspace_dir=workspace_dir,
        reports_dir=reports_dir,
        messages_dir=messages_dir,
        submission_dir=submission_dir,
        task_dir=task_dir,
    )
    return RoleConfig(
        role="verifier",
        system_prompt=_EXPERTISE_VERIFIER_PROMPT,
        tools=[
            RunCommandTool(
                cwd=workspace_dir,
                allowed=True,
                allowed_commands=_EXPERTISE_VERIFIER_COMMANDS,
            ),
            ReadFileTool(
                allowed_roots=[
                    os.path.dirname(spec_path),
                    workspace_dir,
                    reports_dir,
                    messages_dir,
                    submission_dir,
                ],
                path_map=pm,
                base_dir=workspace_dir,
            ),
            WriteFileTool(
                allowed_roots=[submission_dir],
                path_map=pm,
                base_dir=submission_dir,
            ),
            SendMessageTool(messages_dir=messages_dir, sender_role="verifier"),
        ],
    )


def make_executor_config(
    brief_path: str,
    workspace_dir: str,
    reports_dir: str,
    messages_dir: str,
    submission_dir: str = "",
    task_dir: str = "",
) -> RoleConfig:
    """Create Executor role config: can execute, edit workspace, read brief only."""
    if not task_dir:
        task_dir = os.path.dirname(brief_path)
    pm = _build_path_map(
        workspace_dir=workspace_dir, reports_dir=reports_dir,
        messages_dir=messages_dir, submission_dir=submission_dir,
        task_dir=task_dir,
    )
    return RoleConfig(
        role="executor",
        system_prompt=(
            "You are the Executor. You can run commands and edit files in the workspace.\n"
            "You only have access to a brief summary of the task (not the full spec).\n"
            "Follow the Planner's instructions carefully.\n"
            "For file reads/writes, use paths relative to the workspace (e.g., 'app/main.py').\n"
            "When done with your work, send a message to the verifier and output DONE.\n"
            "Ask the Planner for clarification if requirements are unclear."
        ),
        tools=[
            RunCommandTool(cwd=workspace_dir, allowed=True),
            ReadFileTool(
                allowed_roots=[workspace_dir, reports_dir, messages_dir, os.path.dirname(brief_path)],
                path_map=pm,
            ),
            WriteFileTool(allowed_roots=[workspace_dir, reports_dir], path_map=pm),
            SendMessageTool(messages_dir=messages_dir, sender_role="executor"),
        ],
    )


def make_verifier_config(
    spec_path: str,
    workspace_dir: str,
    reports_dir: str,
    messages_dir: str,
    submission_dir: str,
    task_dir: str = "",
) -> RoleConfig:
    """Create Verifier role config: can read workspace/reports (read-only), write attestation."""
    if not task_dir:
        task_dir = os.path.dirname(spec_path)
    pm = _build_path_map(
        workspace_dir=workspace_dir, reports_dir=reports_dir,
        messages_dir=messages_dir, submission_dir=submission_dir,
        task_dir=task_dir,
    )
    return RoleConfig(
        role="verifier",
        system_prompt=(
            "You are the Verifier. You independently verify whether the task was completed correctly.\n"
            "You have read-only access to the workspace and reports.\n"
            "You have access to the full task specification for checking compliance.\n"
            "You CANNOT execute commands or modify the workspace.\n"
            "Your job: check every requirement, identify violations, and produce attestation.json.\n"
            "Write attestation using: write(path='attestation.json', content=...)\n"
            "If requirements are not met, send feedback to the Executor and set verdict='fail'.\n"
            "Only set verdict='pass' when ALL requirements are satisfied.\n"
            "When done, output DONE."
        ),
        tools=[
            ReadFileTool(
                allowed_roots=[
                    os.path.dirname(spec_path), workspace_dir, reports_dir, messages_dir, submission_dir,
                ],
                path_map=pm,
                base_dir=workspace_dir,
            ),
            WriteFileTool(allowed_roots=[submission_dir], path_map=pm, base_dir=submission_dir),
            SendMessageTool(messages_dir=messages_dir, sender_role="verifier"),
        ],
    )
