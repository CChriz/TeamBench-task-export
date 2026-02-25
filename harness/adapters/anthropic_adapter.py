"""
Anthropic adapter for TeamBench agent driver.

Implements ToolCallAdapter using the `anthropic` Python SDK.
Supports Claude 3 Opus/Sonnet/Haiku and claude-* model identifiers.

Requires: pip install anthropic
API key:  ANTHROPIC_API_KEY environment variable
"""
from __future__ import annotations

import os
from typing import Any

from harness.agent_interface import AdapterResponse, ToolCallAdapter


def _standard_to_anthropic_tools(tools: list[dict]) -> list[dict]:
    """Convert standard tool declarations to Anthropic tool format."""
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
        }
        for t in tools
    ]


class AnthropicAdapter(ToolCallAdapter):
    """Anthropic Claude adapter for TeamBench.

    Uses the anthropic >= 0.20 SDK with the Messages API and tool use.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicAdapter. "
                "Install it with: pip install anthropic"
            ) from exc

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Provide api_key or set the environment variable."
            )
        self._client = anthropic.Anthropic(api_key=key)

    # ------------------------------------------------------------------
    # ToolCallAdapter interface
    # ------------------------------------------------------------------

    def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
    ) -> AdapterResponse:
        """Call Anthropic Messages API with tools and return AdapterResponse."""
        anthropic_messages = self._build_messages(messages)
        anthropic_tools = _standard_to_anthropic_tools(tools) if tools else []

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": anthropic_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self._client.messages.create(**kwargs)
        self._track_usage(response)
        return self._parse_response(response)

    def get_usage(self) -> dict:
        """Return cumulative token usage."""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "model": self.model,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(self, messages: list[dict]) -> list[dict]:
        """Convert standard message dicts to Anthropic messages format.

        Anthropic requires alternating user/assistant turns.
        "tool" role (tool results already formatted as text) map to "user".
        """
        anthropic_msgs: list[dict] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "tool"):
                anthropic_msgs.append({"role": "user", "content": content})
            elif role == "assistant":
                anthropic_msgs.append({"role": "assistant", "content": content})
        return anthropic_msgs

    def _parse_response(self, response: Any) -> AdapterResponse:
        """Parse an Anthropic Message into AdapterResponse."""
        text = ""
        tool_calls: list[dict] = []

        for block in response.content or []:
            block_type = getattr(block, "type", "")
            if block_type == "text":
                text += block.text or ""
            elif block_type == "tool_use":
                tool_calls.append({
                    "name": block.name,
                    "args": block.input or {},
                })

        done = "DONE" in text or "TASK_COMPLETE" in text
        return AdapterResponse(text=text, tool_calls=tool_calls, done=done)

    def _track_usage(self, response: Any) -> None:
        """Accumulate token counts from response usage."""
        usage = getattr(response, "usage", None)
        if usage:
            self._total_input_tokens += getattr(usage, "input_tokens", 0) or 0
            self._total_output_tokens += getattr(usage, "output_tokens", 0) or 0
