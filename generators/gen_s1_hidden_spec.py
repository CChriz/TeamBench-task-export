"""
Parameterized generator for S1: Hidden Spec — CLI JSON Tool.

Each seed produces:
  - Different endpoint/field naming conventions
  - Different hidden edge-case requirements (empty input, special chars, key ordering)
  - Different error response format details
  - Different expected.json with per-seed ground-truth
  - Seed-specific spec.md (with hidden requirements) and brief.md (only obvious ones)

The task structure stays the same: fix app/main.py to satisfy ALL requirements,
including the hidden ones the brief does not mention.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Possible exit codes for the empty-input condition (hidden requirement)
EMPTY_EXIT_CODES = [2, 3, 4]

# Possible reason strings for the empty meta field
EMPTY_REASONS = ["empty", "no_content", "blank", "empty_input"]

# Possible status strings for error condition
ERROR_STATUSES = ["error", "err", "fail", "failure"]

# Possible key-ordering variants: success response
SUCCESS_KEY_ORDERS = [
    ["status", "items", "meta"],
    ["status", "meta", "items"],
    ["items", "status", "meta"],
]

# Possible key-ordering variants: error response (must match success ordering for status/items/meta)
# We keep the same ordering requirement for both success and error to avoid ambiguity.

# Names for the input CLI argument
INPUT_ARG_NAMES = ["--input", "--file", "--path", "--src"]

# Names for the items field
ITEMS_FIELD_NAMES = ["items", "lines", "entries", "records"]

# Names for the meta field
META_FIELD_NAMES = ["meta", "info", "summary", "stats"]

# Names for the count key inside meta
COUNT_KEY_NAMES = ["count", "total", "num_items", "length"]

# Names for the status field
STATUS_FIELD_NAMES = ["status", "state", "result"]


class Generator(TaskGenerator):
    task_id = "S1_hidden_spec"
    domain = "software"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick per-seed variants
        empty_exit_code = rng.choice(EMPTY_EXIT_CODES)
        empty_reason = rng.choice(EMPTY_REASONS)
        error_status = rng.choice(ERROR_STATUSES)
        key_order = rng.choice(SUCCESS_KEY_ORDERS)
        input_arg = rng.choice(INPUT_ARG_NAMES)
        items_field = rng.choice(ITEMS_FIELD_NAMES)
        meta_field = rng.choice(META_FIELD_NAMES)
        count_key = rng.choice(COUNT_KEY_NAMES)
        status_field = rng.choice(STATUS_FIELD_NAMES)

        # Reorder the key_order based on actual field names chosen
        # key_order gives positional order: ["status","items","meta"] -> [status_field, items_field, meta_field]
        # We map the abstract positions to the concrete names
        abstract_to_concrete = {
            "status": status_field,
            "items": items_field,
            "meta": meta_field,
        }
        concrete_key_order = [abstract_to_concrete[k] for k in key_order]

        # Hidden edge cases: pick 2 out of 4
        all_edge_cases = [
            "special_chars",       # input with special chars must not corrupt output
            "whitespace_only",     # lines with only whitespace must be skipped
            "leading_trailing",    # items must be stripped
            "numeric_overflow",    # large numbers in item count must still work
        ]
        rng2 = SeededRandom(seed + 10)
        hidden_edge_cases = rng2.sample(all_edge_cases, 2)

        # Sample normal input data
        rng3 = SeededRandom(seed + 20)
        normal_lines = [
            "  hello world  ",
            "foo bar",
            "   test line   ",
            "another entry",
            "  final item",
        ]
        rng3.shuffle(normal_lines)
        # Use the first 3 lines to keep it simple and deterministic
        input_lines = normal_lines[:3]
        # Items after stripping non-empty lines
        expected_items = [ln.strip() for ln in input_lines if ln.strip()]
        expected_count = len(expected_items)

        # Build expected ground truth
        expected = {
            "input_arg": input_arg,
            "status_field": status_field,
            "items_field": items_field,
            "meta_field": meta_field,
            "count_key": count_key,
            "key_order": concrete_key_order,
            "success_status": "ok",
            "error_status": error_status,
            "empty_exit_code": empty_exit_code,
            "empty_reason": empty_reason,
            "normal_items": expected_items,
            "normal_count": expected_count,
            "hidden_edge_cases": hidden_edge_cases,
        }

        # Generate workspace files
        main_py = self._generate_buggy_main(
            input_arg, status_field, items_field, meta_field, count_key
        )
        init_py = ""
        input_txt = "\n".join(input_lines) + "\n"
        empty_txt = ""

        workspace_files = {
            "app/__init__.py": init_py,
            "app/main.py": main_py,
            "data/input.txt": input_txt,
            "data/empty.txt": empty_txt,
        }

        spec_md = self._generate_spec(
            input_arg, status_field, items_field, meta_field, count_key,
            concrete_key_order, error_status, empty_exit_code, empty_reason,
            hidden_edge_cases,
        )
        brief_md = self._generate_brief(input_arg, items_field, meta_field, status_field)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_buggy_main(
        self,
        input_arg: str,
        status_field: str,
        items_field: str,
        meta_field: str,
        count_key: str,
    ) -> str:
        """Generate a buggy main.py that the agent must fix.

        Bugs intentionally introduced:
        1. Wrong exit code on empty input (uses 1 instead of the hidden code)
        2. Wrong key order (uses a dict literal with incorrect ordering)
        3. Missing reason field in error meta
        4. Does not strip items
        5. Error status is wrong (uses "empty" string rather than the hidden error status)
        """
        # The arg name without leading dashes for dest
        dest = input_arg.lstrip("-").replace("-", "_")
        return f'''import argparse
import json
import sys
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("{input_arg}", required=True, dest="{dest}")
    args = ap.parse_args()

    p = pathlib.Path(getattr(args, "{dest}"))
    txt = p.read_text() if p.exists() else ""
    if txt.strip() == "":
        # BUG: wrong exit code; should be seed-specific
        # BUG: missing reason field in meta
        # BUG: wrong error status value
        print(json.dumps({{{status_field!r}: "empty", {items_field!r}: [], {meta_field!r}: {{}}}}))
        return 1

    # BUG: does not strip items
    raw_lines = txt.splitlines()
    {items_field} = [x for x in raw_lines if x.strip()]
    # BUG: wrong key order in output dict
    out = {{{meta_field!r}: {{{count_key!r}: len({items_field})}}, {status_field!r}: "ok", {items_field!r}: {items_field}}}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    def _generate_spec(
        self,
        input_arg: str,
        status_field: str,
        items_field: str,
        meta_field: str,
        count_key: str,
        key_order: list[str],
        error_status: str,
        empty_exit_code: int,
        empty_reason: str,
        hidden_edge_cases: list[str],
    ) -> str:
        key_order_str = str(key_order)
        edge_case_docs = []
        if "special_chars" in hidden_edge_cases:
            edge_case_docs.append(
                "- Lines containing special characters (e.g., `!@#$%`) must be included as-is after stripping."
            )
        if "whitespace_only" in hidden_edge_cases:
            edge_case_docs.append(
                "- Lines consisting entirely of whitespace must be excluded from the output list."
            )
        if "leading_trailing" in hidden_edge_cases:
            edge_case_docs.append(
                f"- Each entry in `{items_field}` must be stripped of leading and trailing whitespace."
            )
        if "numeric_overflow" in hidden_edge_cases:
            edge_case_docs.append(
                f"- The `{count_key}` value must be an integer even for large files; no float conversion."
            )
        edge_str = "\n".join(edge_case_docs) if edge_case_docs else "- No additional hidden edge cases."

        return f"""# S1: Hidden Spec — CLI JSON Tool

## Goal
Fix the CLI tool so that it satisfies ALL requirements below, including the hidden ones.

## Hard Requirements

1. `python -m app.main {input_arg} <path>` prints a JSON object to stdout.
2. The JSON object must contain keys `{key_order_str}` in **exactly this order**.
3. `{status_field}` must be `"ok"` on success.
4. If the input file is empty, the program must:
   - Exit with code **{empty_exit_code}**
   - Print a JSON error object to stdout with `{status_field}` set to `"{error_status}"`,
     an empty `{items_field}` list, and a `{meta_field}` object whose `reason` field
     is set to `"{empty_reason}"`.
   - Keys in the error object must appear in the same canonical order: `{key_order_str}`.
5. No extra keys are allowed in the top-level object.
6. The `{items_field}` field must be a list of non-empty stripped strings from the input file.
7. The `{meta_field}` field must contain a `{count_key}` key whose value equals the number of items.

## Hidden Edge-Case Requirements

{edge_str}

## Deliverables
- Fixed code in the workspace.
- Executor must ensure all visible tests pass.
- Verifier must confirm hidden spec compliance and produce attestation.
"""

    def _generate_brief(
        self,
        input_arg: str,
        items_field: str,
        meta_field: str,
        status_field: str,
    ) -> str:
        return f"""# S1: CLI JSON Tool (Brief)

Fix the CLI tool so that tests pass.
The tool reads a file and prints JSON to stdout.
Run with: `python -m app.main {input_arg} <path>`

The output must be a JSON object with `{status_field}`, `{items_field}`, and `{meta_field}` fields.
"""
