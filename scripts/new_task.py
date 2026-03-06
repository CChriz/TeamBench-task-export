#!/usr/bin/env python3
"""
Scaffold generator for new TeamBench tasks.

Creates the directory structure and template files for a new task:
  - tasks/{task_id}/task.yaml
  - tasks/{task_id}/spec.md
  - tasks/{task_id}/brief.md
  - tasks/{task_id}/grade.sh
  - generators/gen_{task_id_lower}.py

Usage:
    python scripts/new_task.py --id MULTI2_microservice_debug \
        --category Multi-language --difficulty hard \
        --languages python go javascript sql \
        --tni-pattern A \
        --description "4 bugs across Python API + Go worker + Node frontend + Postgres schema"
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
import textwrap


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(task_id: str) -> str:
    """Convert task_id to snake_case for generator filename."""
    return task_id.lower().replace("-", "_")


def create_task_yaml(task_dir: str, args: argparse.Namespace) -> None:
    langs = "[" + ", ".join(args.languages) + "]"
    content = textwrap.dedent(f"""\
        task_id: {args.id}
        category: {args.category}
        difficulty: {args.difficulty}
        languages: {langs}
        description: "{args.description}"
        tni_pattern: {args.tni_pattern}
        parameterized: true
        seeds: [0, 1, 2]
    """)
    path = os.path.join(task_dir, "task.yaml")
    with open(path, "w") as f:
        f.write(content)
    print(f"  Created {path}")


def create_spec_md(task_dir: str, args: argparse.Namespace) -> None:
    content = textwrap.dedent(f"""\
        # {args.id}: [Title]

        ## Goal

        [Describe the high-level objective. What does the agent need to accomplish?]

        ## Requirements

        1. [Requirement 1 — be specific and testable]
        2. [Requirement 2]
        3. [Requirement 3]
        4. All tests must pass after changes

        ## Supporting Documents

        - [List files the agent should read for context]
        - [e.g., CHANGELOG.md, api_spec.yaml, ARCHITECTURE.md]

        ## Contradiction / Hidden Complexity

        [Describe the trap, hidden constraint, or cross-system mismatch that makes
        this task require teamwork. What would a naive single agent get wrong?]

        ## Important Notes

        - [False positives to preserve]
        - [Authoritative sources when documents conflict]
        - [Budget/resource constraints if applicable]
    """)
    path = os.path.join(task_dir, "spec.md")
    with open(path, "w") as f:
        f.write(content)
    print(f"  Created {path}")


def create_brief_md(task_dir: str, args: argparse.Namespace) -> None:
    content = textwrap.dedent(f"""\
        # {args.id}: [Title]

        [1-3 sentence summary of what needs fixing. Do NOT include specifics
        about which bugs are real vs false positives, or which documents to
        trust. The Planner will provide that guidance.]

        Follow the Planner's guidance precisely.
    """)
    path = os.path.join(task_dir, "brief.md")
    with open(path, "w") as f:
        f.write(content)
    print(f"  Created {path}")


def create_grade_sh(task_dir: str, args: argparse.Namespace) -> None:
    content = textwrap.dedent("""\
        #!/usr/bin/env bash
        # {task_id} grader
        set -euo pipefail

        WORKSPACE="${{1:-${{WORKSPACE_DIR:-/workspace}}}}"
        REPORTS="${{2:-${{REPORTS_DIR:-/reports}}}}"
        SUBMISSION="${{3:-/submission}}"
        TASK_DIR="${{4:-/task}}"

        source /usr/local/lib/venv/bin/activate 2>/dev/null || true

        pass=true
        partial=0
        total=10
        findings=""

        check() {{
            local id="$1"
            local desc="$2"
            local result="$3"
            if [ "$result" = "pass" ]; then
                partial=$((partial + 1))
                findings="${{findings}}{{\\\"id\\\":\\\"${{id}}\\\",\\\"ok\\\":true,\\\"note\\\":\\\"${{desc}}\\\"}},"
            else
                pass=false
                findings="${{findings}}{{\\\"id\\\":\\\"${{id}}\\\",\\\"ok\\\":false,\\\"note\\\":\\\"${{desc}}\\\"}},"
            fi
        }}

        cd "${{WORKSPACE}}"

        # ── Install dependencies ──────────────────────────────────────────────
        # pip install <deps> --quiet 2>/dev/null || true

        # ── C1: [First check description] ─────────────────────────────────────
        # check "C1" "description" "pass"

        # ── C2-C10: [Additional checks] ───────────────────────────────────────
        # Add check() calls here. Each check should test one specific requirement.
        # Use inline Python heredocs for complex checks:
        #
        # result=$(python3 -c "
        # import ast, sys
        # # ... analysis code ...
        # print('pass' if condition else 'fail')
        # " 2>/dev/null || echo "fail")
        # check "C2" "description" "$result"

        partial_score=$(python3 -c "print(round($partial / $total, 2))")
        findings="${{findings%,}}"

        mkdir -p "${{REPORTS}}"
        cat > "${{REPORTS}}/score.json" <<EOF
        {{
          "pass": $( [ "$pass" = "true" ] && echo "true" || echo "false" ),
          "secondary": {{
            "partial_score": $partial_score,
            "checks_passed": $partial,
            "checks_total": $total
          }},
          "failure_modes": [],
          "checklist": [$findings]
        }}
        EOF
    """).format(task_id=args.id)
    path = os.path.join(task_dir, "grade.sh")
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    print(f"  Created {path}")


def create_generator(gen_dir: str, args: argparse.Namespace) -> None:
    slug = slugify(args.id)
    langs_repr = repr(args.languages)
    content = textwrap.dedent(f'''\
        """
        Parameterized generator for {args.id}.

        Each seed produces a different instance with varied parameters.
        [Describe what varies across seeds.]
        """
        from __future__ import annotations
        import os
        from generators.base import TaskGenerator, GeneratedTask
        from generators.primitives import SeededRandom


        # ── Seed-parameterized pools ──────────────────────────────────────────────
        # Define pools of values that vary per seed. At least 3 entries per pool
        # to support seeds [0, 1, 2] with distinct instances.

        # EXAMPLE_POOL = ["variant_a", "variant_b", "variant_c"]


        class Generator(TaskGenerator):
            task_id = "{args.id}"
            domain = "{args.category}"
            difficulty = "{args.difficulty}"
            languages = {langs_repr}

            def generate(self, seed: int) -> GeneratedTask:
                rng = SeededRandom(seed)
                # idx = seed % len(EXAMPLE_POOL)

                # Pick seed-specific parameters
                # variant = EXAMPLE_POOL[idx]

                workspace_files = self._make_workspace()

                tasks_dir = os.path.join(
                    os.path.dirname(__file__), "..", "tasks", "{args.id}"
                )
                with open(os.path.join(tasks_dir, "spec.md")) as f:
                    spec_md = f.read()
                with open(os.path.join(tasks_dir, "brief.md")) as f:
                    brief_md = f.read()

                return GeneratedTask(
                    task_id="{args.id}",
                    seed=seed,
                    spec_md=spec_md,
                    brief_md=brief_md,
                    expected={{
                        "seed": seed,
                        # Add ground-truth values for grading
                    }},
                    workspace_files=workspace_files,
                    metadata={{"difficulty": "{args.difficulty}", "category": "{args.category}"}},
                )

            def _make_workspace(self) -> dict:
                """Generate all workspace files."""
                files = {{}}

                # TODO: Add workspace files with embedded bugs
                # files["app/main.py"] = f\'\'\'...\'\'\'
                # files["tests/test_main.py"] = f\'\'\'...\'\'\'

                return files
    ''')
    path = os.path.join(gen_dir, f"gen_{slug}.py")
    with open(path, "w") as f:
        f.write(content)
    print(f"  Created {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new TeamBench task"
    )
    parser.add_argument("--id", required=True, help="Task ID (e.g., MULTI2_microservice_debug)")
    parser.add_argument("--category", required=True, help="Category (e.g., Multi-language)")
    parser.add_argument("--difficulty", default="hard", choices=["easy", "medium", "hard", "expert"])
    parser.add_argument("--languages", nargs="+", default=["python"], help="Languages involved")
    parser.add_argument("--tni-pattern", default="A", help="TNI pattern (A-F)")
    parser.add_argument("--description", default="", help="Short task description")
    args = parser.parse_args()

    task_dir = os.path.join(REPO_ROOT, "tasks", args.id)
    gen_dir = os.path.join(REPO_ROOT, "generators")

    if os.path.exists(task_dir):
        print(f"Error: task directory already exists: {task_dir}", file=sys.stderr)
        sys.exit(1)

    slug = slugify(args.id)
    gen_path = os.path.join(gen_dir, f"gen_{slug}.py")
    if os.path.exists(gen_path):
        print(f"Error: generator already exists: {gen_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Creating scaffold for {args.id}...")
    os.makedirs(task_dir, exist_ok=True)

    create_task_yaml(task_dir, args)
    create_spec_md(task_dir, args)
    create_brief_md(task_dir, args)
    create_grade_sh(task_dir, args)
    create_generator(gen_dir, args)

    print(f"\nScaffold complete! Next steps:")
    print(f"  1. Edit tasks/{args.id}/spec.md — full specification")
    print(f"  2. Edit tasks/{args.id}/brief.md — executor summary")
    print(f"  3. Edit generators/gen_{slug}.py — workspace generation")
    print(f"  4. Edit tasks/{args.id}/grade.sh — grading checks")
    print(f"  5. Validate: python -c \"from generators.registry import get_generator; g = get_generator('{args.id}'); t = g.generate(0); print(len(t.workspace_files), 'files')\"")
    print(f"  6. Cross-seed: python -c \"from generators.registry import get_generator; g = get_generator('{args.id}'); print(g.validate_cross_seed(0, 1))\"")


if __name__ == "__main__":
    main()
