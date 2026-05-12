"""Tests for the example agent.

We use ``pydantic_ai.models.test.TestModel`` so no provider is contacted.
This is the pattern to copy when you add new agents — never let a unit
test reach a real LLM.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.test import TestModel

from llm_uv_template.agent import CityInfo, build_agent


async def test_build_agent_returns_structured_output() -> None:
    agent = build_agent()
    with agent.override(model=TestModel(call_tools=["current_utc_time"])):
        result = await agent.run("Where is the Eiffel Tower?")
    assert isinstance(result.output, CityInfo)
    assert result.output.city
    assert result.output.country
    assert result.output.rationale


async def test_current_utc_time_tool_is_callable_and_returns_iso8601() -> None:
    """Exercises the `current_utc_time` tool via ``TestModel``.

    ``TestModel(call_tools=[name])`` makes the fake model invoke the named
    tool exactly once before answering, so any breakage in the tool's
    signature, return type, or its `datetime.now(UTC).isoformat()`
    implementation surfaces here instead of at real-agent runtime.
    """
    agent = build_agent()
    with agent.override(model=TestModel(call_tools=["current_utc_time"])):
        result = await agent.run("What time is it?")

    tool_returns = [
        part.content
        for message in result.all_messages()
        for part in getattr(message, "parts", [])
        if isinstance(part, ToolReturnPart) and part.tool_name == "current_utc_time"
    ]
    assert tool_returns, "TestModel did not call the current_utc_time tool"

    for raw in tool_returns:
        parsed = datetime.fromisoformat(str(raw))
        assert parsed.tzinfo is not None, "tool must return a tz-aware datetime"


@pytest.mark.parametrize(
    "model_str",
    [
        "openai:gpt-5.2",
        "anthropic:claude-4.6-sonnet",
        "google-gla:gemini-3-pro",
    ],
)
def test_agent_accepts_multi_provider_model_strings(model_str: str) -> None:
    # Construction must not call the network; we never run the agent.
    agent = build_agent(model_str)
    assert agent is not None
