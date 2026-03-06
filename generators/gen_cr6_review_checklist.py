"""
Parameterized generator for CR6: Code Review with False Positives.

Each seed produces:
- A pull_request.diff file showing a ~300-line Python PR
- A REVIEW_GUIDELINES.md defining severity levels and criteria
- 12 potential issues in the diff: 8 real (2 critical, 3 major, 3 minor),
  4 false positives that look bad but are correct per guidelines
- Agent must produce review_report.json classifying all 12

Seed variation:
  - Different PR domains (web app, CLI tool, data pipeline, etc.)
  - Different which issues are real vs FP
  - Different severity thresholds
  - Different code content

TNI driver (Pattern B + C):
  - Brief: "Review the PR diff and produce a review report"
  - Spec: Full guidelines + list of expected findings for Planner
"""
from __future__ import annotations

import json
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── PR domain pools ────────────────────────────────────────────────────────

PR_DOMAINS = [
    {
        "name": "web_api",
        "title": "User Authentication API",
        "desc": "Adds login/register endpoints with JWT tokens",
        "module": "auth_handler.py",
    },
    {
        "name": "data_pipeline",
        "title": "ETL Pipeline Enhancement",
        "desc": "Adds CSV ingestion with validation and transformation",
        "module": "pipeline.py",
    },
    {
        "name": "cli_tool",
        "title": "CLI Config Manager",
        "desc": "Adds config file parsing and environment variable expansion",
        "module": "config_manager.py",
    },
]

# Issue pool: (id, severity, is_real, category, title, code_context_template)
# We build 8 real + 4 FP = 12 per seed, drawn from these templates.

REAL_ISSUES = [
    # Critical (always pick 2)
    {
        "id": "SQL_INJECTION",
        "severity": "critical",
        "category": "security",
        "title": "SQL injection via string interpolation",
        "explanation": "User input is interpolated directly into SQL query without parameterization",
        "code": 'query = f"SELECT * FROM users WHERE name = \'{user_input}\'"',
        "fix": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE name = ?', (user_input,))",
    },
    {
        "id": "MISSING_AUTH",
        "severity": "critical",
        "category": "security",
        "title": "Endpoint missing authentication decorator",
        "explanation": "The /admin/delete endpoint has no @require_auth or @login_required decorator",
        "code": "@app.route('/admin/delete', methods=['POST'])\ndef admin_delete():",
        "fix": "Add @require_auth decorator before the route handler",
    },
    {
        "id": "COMMAND_INJECTION",
        "severity": "critical",
        "category": "security",
        "title": "OS command injection via subprocess with shell=True",
        "explanation": "User input passed to subprocess.call with shell=True allows arbitrary command execution",
        "code": "subprocess.call(f'grep {pattern} {filename}', shell=True)",
        "fix": "Use subprocess.call(['grep', pattern, filename]) without shell=True",
    },
    # Major (always pick 3)
    {
        "id": "RESOURCE_LEAK",
        "severity": "major",
        "category": "reliability",
        "title": "File handle not closed on exception path",
        "explanation": "File is opened but not wrapped in try/finally or context manager; exception skips close()",
        "code": "f = open(path, 'r')\ndata = json.load(f)\nf.close()",
        "fix": "Use 'with open(path) as f:' context manager",
    },
    {
        "id": "RACE_CONDITION",
        "severity": "major",
        "category": "reliability",
        "title": "TOCTOU race condition in file check",
        "explanation": "Checks os.path.exists() then opens file — another process may delete between check and open",
        "code": "if os.path.exists(path):\n    with open(path) as f:\n        data = f.read()",
        "fix": "Use try/except FileNotFoundError instead of exists() check",
    },
    {
        "id": "UNHANDLED_EXCEPTION",
        "severity": "major",
        "category": "error_handling",
        "title": "Broad except clause swallows all exceptions",
        "explanation": "except Exception silently catches and ignores all errors including KeyboardInterrupt",
        "code": "try:\n    process(data)\nexcept Exception:\n    pass",
        "fix": "Catch specific exceptions and log/re-raise appropriately",
    },
    {
        "id": "MISSING_VALIDATION",
        "severity": "major",
        "category": "reliability",
        "title": "Missing input validation on numeric field",
        "explanation": "User-provided 'amount' is cast to float without bounds checking; negative values cause issues",
        "code": "amount = float(request.form['amount'])",
        "fix": "Validate amount is positive and within acceptable range before processing",
    },
    {
        "id": "HARDCODED_SECRET",
        "severity": "major",
        "category": "security",
        "title": "Hardcoded API key in source code",
        "explanation": "Secret API key is embedded directly in the source file rather than loaded from environment",
        "code": 'API_KEY = "sk-live-abc123def456ghi789"',
        "fix": "Load from environment variable: API_KEY = os.environ['API_KEY']",
    },
    # Minor (always pick 3)
    {
        "id": "BAD_NAMING",
        "severity": "minor",
        "category": "style",
        "title": "Variable name 'x' is non-descriptive",
        "explanation": "Single-letter variable name reduces readability in a 20-line function",
        "code": "x = calculate_total(items)",
        "fix": "Rename to 'total_amount' or similar descriptive name",
    },
    {
        "id": "UNUSED_IMPORT",
        "severity": "minor",
        "category": "style",
        "title": "Unused import: 'from datetime import timedelta'",
        "explanation": "timedelta is imported but never referenced in the module",
        "code": "from datetime import datetime, timedelta",
        "fix": "Remove unused import: 'from datetime import datetime'",
    },
    {
        "id": "MISSING_DOCSTRING",
        "severity": "minor",
        "category": "documentation",
        "title": "Public function missing docstring",
        "explanation": "The function process_batch() has no docstring explaining its parameters or behavior",
        "code": "def process_batch(items, batch_size=100):\n    results = []",
        "fix": "Add a docstring describing parameters, return value, and exceptions",
    },
    {
        "id": "MAGIC_NUMBER",
        "severity": "minor",
        "category": "style",
        "title": "Magic number 3600 used without explanation",
        "explanation": "Hardcoded 3600 (seconds in hour) used without a named constant",
        "code": "if elapsed > 3600:\n    expire_session()",
        "fix": "Define SESSION_TIMEOUT_SECONDS = 3600 as a module-level constant",
    },
    {
        "id": "PRINT_DEBUGGING",
        "severity": "minor",
        "category": "style",
        "title": "Debug print statement left in production code",
        "explanation": "print() calls should be replaced with proper logging",
        "code": "print(f'DEBUG: processing {item_id}')",
        "fix": "Use logging.debug() instead of print()",
    },
]

FALSE_POSITIVE_POOL = [
    {
        "id": "FP_ASSERT_PROD",
        "looks_like": "Using assert in production code",
        "why_ok": "Per REVIEW_GUIDELINES: assert is acceptable in internal CLI tools that are not customer-facing",
        "code": "assert config is not None, 'Config must be loaded first'",
    },
    {
        "id": "FP_EVAL_SAFE",
        "looks_like": "Use of eval() — potential code injection",
        "why_ok": "Per REVIEW_GUIDELINES: ast.literal_eval() is safe for parsing literal expressions; not the same as eval()",
        "code": "value = ast.literal_eval(raw_string)",
    },
    {
        "id": "FP_WILDCARD_IMPORT",
        "looks_like": "Wildcard import 'from constants import *'",
        "why_ok": "Per REVIEW_GUIDELINES: wildcard imports from project-internal constants modules are permitted",
        "code": "from .constants import *",
    },
    {
        "id": "FP_BARE_EXCEPT",
        "looks_like": "Bare except clause",
        "why_ok": "Per REVIEW_GUIDELINES: bare except with explicit logging and re-raise is acceptable in top-level error boundaries",
        "code": "except:\n    logger.exception('Unhandled error')\n    raise",
    },
    {
        "id": "FP_MUTABLE_DEFAULT",
        "looks_like": "Mutable default argument: def func(items=[])",
        "why_ok": "Per REVIEW_GUIDELINES: the function uses 'if items is None: items = []' pattern inside, the default is intentionally used as sentinel",
        "code": "def process(items=None):\n    if items is None:\n        items = []",
    },
    {
        "id": "FP_GLOBAL_STATE",
        "looks_like": "Module-level mutable global state",
        "why_ok": "Per REVIEW_GUIDELINES: module-level caches with explicit thread-safety (Lock) are accepted for performance",
        "code": "_cache = {}\n_cache_lock = threading.Lock()",
    },
]


class Generator(TaskGenerator):
    task_id = "CR6_review_checklist"
    domain = "code_review"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        domain = PR_DOMAINS[seed % len(PR_DOMAINS)]

        # Pick 2 critical issues
        criticals = [i for i in REAL_ISSUES if i["severity"] == "critical"]
        crit_picked = rng.sample(criticals, 2)

        # Pick 3 major issues
        majors = [i for i in REAL_ISSUES if i["severity"] == "major"]
        maj_picked = rng.sample(majors, 3)

        # Pick 3 minor issues
        minors = [i for i in REAL_ISSUES if i["severity"] == "minor"]
        min_picked = rng.sample(minors, 3)

        real_issues = crit_picked + maj_picked + min_picked  # 8 total

        # Pick 4 false positives
        fp_picked = rng.sample(FALSE_POSITIVE_POOL, 4)

        # Interleave for the diff: shuffle the combined list
        all_items_order = list(range(12))
        rng.shuffle(all_items_order)

        workspace_files = self._make_workspace(domain, real_issues, fp_picked, all_items_order)

        expected = {
            "seed": seed,
            "domain": domain["name"],
            "real_issues": [
                {"id": r["id"], "severity": r["severity"], "category": r["category"]}
                for r in real_issues
            ],
            "false_positives": [
                {"id": fp["id"], "looks_like": fp["looks_like"]}
                for fp in fp_picked
            ],
            "total_findings": 12,
            "real_count": 8,
            "fp_count": 4,
            "critical_count": 2,
            "major_count": 3,
            "minor_count": 3,
        }

        spec_md = self._generate_spec(domain, real_issues, fp_picked)
        brief_md = self._generate_brief(domain)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_workspace(
        self,
        domain: dict,
        real_issues: list,
        fp_issues: list,
        order: list,
    ) -> dict:
        files = {}

        # Build the diff content
        diff_lines = self._build_diff(domain, real_issues, fp_issues, order)
        files["pull_request.diff"] = diff_lines

        files["REVIEW_GUIDELINES.md"] = self._build_guidelines()

        files["review_report.json"] = "{}"  # Empty — agent fills this in

        files["expected_report_schema.json"] = json.dumps({
            "$schema": "Expected output format for review_report.json",
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "severity": {"enum": ["critical", "major", "minor", "false_positive"]},
                            "category": {"type": "string"},
                            "title": {"type": "string"},
                            "line_range": {"type": "string"},
                            "explanation": {"type": "string"},
                            "recommendation": {"type": "string"},
                        },
                    },
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_findings": {"type": "integer"},
                        "critical": {"type": "integer"},
                        "major": {"type": "integer"},
                        "minor": {"type": "integer"},
                        "false_positives": {"type": "integer"},
                        "verdict": {"enum": ["reject", "request_changes", "approve_with_comments", "approve"]},
                    },
                },
            },
        }, indent=2)

        return files

    def _build_diff(
        self,
        domain: dict,
        real_issues: list,
        fp_issues: list,
        order: list,
    ) -> str:
        module = domain["module"]
        title = domain["title"]

        header = f"""diff --git a/{module} b/{module}
new file mode 100644
index 0000000..abcdef1
--- /dev/null
+++ b/{module}
@@ -0,0 +1,300 @@
+\"\"\"{title}
+
+{domain['desc']}.
+\"\"\"
+import os
+import json
+import logging
+import threading
+import subprocess
+import ast
+from datetime import datetime, timedelta
+from pathlib import Path
+
+logger = logging.getLogger(__name__)
+
"""
        # Build code blocks for each issue
        blocks = []
        combined = []
        for i, idx in enumerate(order):
            if idx < 8:
                issue = real_issues[idx]
                block = f"+# --- Section {i+1}: {issue['category']} ---\n"
                for line in issue["code"].split("\n"):
                    block += f"+{line}\n"
                block += "+\n"
            else:
                fp = fp_issues[idx - 8]
                block = f"+# --- Section {i+1}: pattern ---\n"
                for line in fp["code"].split("\n"):
                    block += f"+{line}\n"
                block += "+\n"
            blocks.append(block)

        # Add some filler code between blocks
        filler_sections = [
            "+\n+\n+def initialize():\n+    \"\"\"Initialize the module.\"\"\"\n+    logger.info('Initializing')\n+    return True\n+\n",
            "+\n+\n+class Config:\n+    \"\"\"Configuration container.\"\"\"\n+    def __init__(self, path):\n+        self.path = path\n+        self.data = {}\n+\n",
            "+\n+\n+def shutdown():\n+    \"\"\"Clean shutdown.\"\"\"\n+    logger.info('Shutting down')\n+\n",
        ]

        diff_body = header
        for i, block in enumerate(blocks):
            diff_body += block
            if i < len(filler_sections):
                diff_body += filler_sections[i]

        # Add final lines
        diff_body += "+\n+if __name__ == '__main__':\n+    initialize()\n"

        return diff_body

    def _build_guidelines(self) -> str:
        return """# Code Review Guidelines

## Severity Levels

### Critical
Issues that MUST be fixed before merge. These represent:
- Security vulnerabilities (SQL injection, command injection, auth bypass)
- Data loss or corruption risks
- Missing authentication/authorization on sensitive endpoints

### Major
Issues that SHOULD be fixed before merge. These represent:
- Resource leaks (file handles, connections, memory)
- Race conditions and concurrency bugs
- Unhandled exceptions that crash the application
- Missing input validation on external data
- Hardcoded secrets or credentials

### Minor
Issues that are nice to fix but do not block merge:
- Naming convention violations
- Unused imports
- Missing documentation/docstrings
- Magic numbers without named constants
- Debug print statements

### False Positive (Not an Issue)
Patterns that LOOK problematic but are CORRECT in context:

1. **assert in non-customer-facing tools**: `assert` is acceptable in internal
   CLI tools and test helpers. Only flag it in production web handlers.

2. **ast.literal_eval()**: This is NOT the same as `eval()`. It safely parses
   Python literal structures (strings, numbers, tuples, lists, dicts, booleans,
   None). Do NOT flag `ast.literal_eval()` as a security issue.

3. **Wildcard imports from internal constants**: `from .constants import *` is
   permitted for project-internal constants modules. Only flag wildcard imports
   from third-party packages.

4. **Bare except with logging and re-raise**: A bare `except:` clause that
   logs the exception AND re-raises is acceptable at top-level error boundaries
   (e.g., main(), CLI entry points). Only flag bare except that silently swallows.

5. **Mutable default with None sentinel**: `def func(items=None)` followed by
   `if items is None: items = []` is the correct pattern. Do NOT flag this as
   a mutable default argument issue.

6. **Thread-safe module-level caches**: Module-level dictionaries used as caches
   are acceptable when accompanied by a threading.Lock for synchronization.

## Review Report Format
Output must be `review_report.json` conforming to `expected_report_schema.json`.

## Verdict Criteria
- **reject**: Any unfixed critical issue
- **request_changes**: Major issues remain
- **approve_with_comments**: Only minor issues remain
- **approve**: No real issues found
"""

    def _generate_spec(
        self, domain: dict, real_issues: list, fp_issues: list
    ) -> str:
        real_list = "\n".join(
            f"  {i+1}. **{r['id']}** ({r['severity']}/{r['category']}): {r['title']}\n"
            f"     Code: `{r['code'].split(chr(10))[0]}`\n"
            f"     Fix: {r['fix']}"
            for i, r in enumerate(real_issues)
        )

        fp_list = "\n".join(
            f"  {i+1}. **{fp['id']}**: Looks like \"{fp['looks_like']}\" but is OK because:\n"
            f"     {fp['why_ok']}"
            for i, fp in enumerate(fp_issues)
        )

        return f"""# CR6: Code Review with False Positive Triage

## Goal
Review the PR diff in `pull_request.diff` and produce `review_report.json` that
correctly classifies all 12 potential issues: 8 real issues and 4 false positives.

## PR Context
**{domain['title']}** — {domain['desc']}

## Review Guidelines
See `REVIEW_GUIDELINES.md` for severity definitions and false positive rules.

## 8 Real Issues (must be flagged with correct severity)

{real_list}

## 4 False Positives (must be classified as false_positive)

{fp_list}

## Output Format
Write `review_report.json` conforming to `expected_report_schema.json`.

## Grading Criteria
- All 8 real issues identified with correct severity
- All 4 false positives correctly dismissed
- No extra false findings (precision matters)
- Severity levels match the guidelines
- Verdict is appropriate given the findings

## Deliverables
1. `review_report.json` with all 12 findings classified
2. Verifier writes `attestation.json`
"""

    def _generate_brief(self, domain: dict) -> str:
        return f"""# CR6: Code Review (Brief)

Review the PR diff in `pull_request.diff` for the **{domain['title']}**.

Read `REVIEW_GUIDELINES.md` for severity criteria and false positive rules.
Write your findings to `review_report.json` (see `expected_report_schema.json` for format).

Some patterns in the diff look problematic but are actually correct per the guidelines.
Classify each finding with the appropriate severity or as a false positive.
"""
