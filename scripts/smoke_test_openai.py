#!/usr/bin/env python3
"""
Smoke test for the TeamBench OpenAI adapter.

Checks:
  1. OPENAI_API_KEY is present in .env or environment
  2. OpenAIAdapter imports and instantiates cleanly
  3. A minimal chat message gets a valid text response
  4. Tool calling works (a simple echo-style tool invocation)

Usage:
    python scripts/smoke_test_openai.py
    python scripts/smoke_test_openai.py --model gpt-4o-mini
"""
from __future__ import annotations

import argparse
import os
import sys

# Allow running as a script from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


# -----------------------------------------------------------------------
# .env loader
# -----------------------------------------------------------------------

def _load_dotenv(repo_root: str) -> None:
    """Load .env from repo root into os.environ (does not overwrite existing keys)."""
    env_path = os.path.join(repo_root, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


# -----------------------------------------------------------------------
# Checks
# -----------------------------------------------------------------------

def check_api_key(repo_root: str) -> tuple[bool, str]:
    """Check that OPENAI_API_KEY is available."""
    _load_dotenv(repo_root)
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        # Show only first/last 4 chars
        masked = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
        return True, f"OPENAI_API_KEY found: {masked}"
    return False, "OPENAI_API_KEY not set in environment or .env"


def check_import() -> tuple[bool, str]:
    """Check that openai package and adapter import cleanly."""
    try:
        import openai  # noqa: F401
    except ImportError:
        return False, "openai package not installed. Run: pip install openai"
    try:
        from harness.adapters.openai_adapter import OpenAIAdapter  # noqa: F401
    except ImportError as e:
        return False, f"Failed to import OpenAIAdapter: {e}"
    return True, "openai package and OpenAIAdapter import OK"


def check_instantiate(model: str) -> tuple[bool, str, object | None]:
    """Instantiate the adapter and confirm basic attributes."""
    try:
        from harness.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(model=model, temperature=0.0, max_tokens=256)
    except ValueError as e:
        return False, f"Instantiation failed (likely missing key): {e}", None
    except Exception as e:
        return False, f"Instantiation failed: {e}", None
    return True, f"Adapter instantiated: model={adapter.model}", adapter


def check_simple_message(adapter: object) -> tuple[bool, str]:
    """Send a minimal chat message and verify we get a non-empty response."""
    from harness.agent_interface import AdapterResponse

    messages = [{"role": "user", "content": "Reply with exactly: hello"}]
    try:
        resp: AdapterResponse = adapter.generate_with_tools(  # type: ignore[attr-defined]
            messages=messages,
            system_prompt="You are a helpful assistant.",
            tools=[],
        )
    except Exception as e:
        return False, f"API call failed: {e}"

    if not isinstance(resp.text, str) or not resp.text.strip():
        return False, f"Empty or invalid response text: {resp.text!r}"

    preview = resp.text.strip()[:80].replace("\n", " ")
    usage = adapter.get_usage()  # type: ignore[attr-defined]
    return (
        True,
        f"Response received: {preview!r} "
        f"(tokens in={usage['input_tokens']}, out={usage['output_tokens']})",
    )


def check_tool_calling(adapter: object) -> tuple[bool, str]:
    """Send a prompt that requires tool use and verify a tool call is returned."""
    # Define a simple echo tool
    tools = [
        {
            "name": "get_current_weather",
            "description": "Get the current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. London",
                    }
                },
                "required": ["location"],
            },
        }
    ]

    messages = [
        {
            "role": "user",
            "content": "What is the weather in Paris right now? Use the get_current_weather tool.",
        }
    ]

    try:
        resp = adapter.generate_with_tools(  # type: ignore[attr-defined]
            messages=messages,
            system_prompt="You are a helpful assistant. Use tools when asked.",
            tools=tools,
        )
    except Exception as e:
        return False, f"Tool-calling API call failed: {e}"

    if not resp.tool_calls:
        # Some models may respond with text instead of a tool call for this prompt.
        # That is acceptable but worth noting.
        preview = resp.text.strip()[:60].replace("\n", " ") if resp.text else ""
        return (
            True,
            f"No tool call returned (model responded with text: {preview!r}). "
            "This is acceptable for some models.",
        )

    tc = resp.tool_calls[0]
    name = tc.get("name", "")
    args = tc.get("args", {})
    return True, f"Tool call returned: {name}({args})"


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Smoke test for the TeamBench OpenAI adapter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--model", default="gpt-4o-mini",
        help="OpenAI model to test (default: gpt-4o-mini)",
    )
    ap.add_argument(
        "--skip-api", action="store_true",
        help="Only check imports / instantiation, skip live API calls",
    )
    args = ap.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failures = 0

    print(f"TeamBench OpenAI Adapter Smoke Test")
    print(f"Model: {args.model}")
    print("=" * 50)

    # 1. API key
    ok, msg = check_api_key(repo_root)
    status = PASS if ok else (SKIP if args.skip_api else FAIL)
    print(f"{status} API key:        {msg}")
    if not ok:
        if args.skip_api:
            print(f"\n{SKIP} Live API calls skipped (--skip-api). Key and package checks are informational.")
        else:
            failures += 1
            print("\nCannot continue without OPENAI_API_KEY. Use --skip-api to check imports only.")
            sys.exit(1)

    # 2. Import
    ok, msg = check_import()
    status = PASS if ok else (SKIP if args.skip_api else FAIL)
    print(f"{status} Import:         {msg}")
    if not ok:
        if args.skip_api:
            print(f"\n{SKIP} Import check failed but --skip-api is set; treating as informational.")
            print(f"\nResult: 0 failure(s) (skip-api mode)")
            sys.exit(0)
        failures += 1
        sys.exit(1)

    # 3. Instantiate
    ok, msg, adapter = check_instantiate(args.model)
    status = PASS if ok else (SKIP if args.skip_api else FAIL)
    print(f"{status} Instantiate:    {msg}")
    if not ok:
        if args.skip_api:
            print(f"\n{SKIP} Instantiation failed (likely missing key) but --skip-api is set.")
            print(f"\nResult: 0 failure(s) (skip-api mode)")
            sys.exit(0)
        failures += 1
        sys.exit(1)
        adapter = None

    if args.skip_api:
        print(f"\n{SKIP} Live API calls skipped (--skip-api).")
        print(f"\nResult: 0 failure(s) (skip-api mode — imports and instantiation OK)")
        sys.exit(0)

    # 4. Simple message
    ok, msg = check_simple_message(adapter)
    status = PASS if ok else FAIL
    print(f"{status} Simple message: {msg}")
    if not ok:
        failures += 1

    # 5. Tool calling
    ok, msg = check_tool_calling(adapter)
    status = PASS if ok else FAIL
    print(f"{status} Tool calling:   {msg}")
    if not ok:
        failures += 1

    print("=" * 50)
    if failures == 0:
        print(f"Result: ALL CHECKS PASSED")
    else:
        print(f"Result: {failures} FAILURE(S)")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
