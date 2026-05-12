"""Minimal pydantic-ai agent skeleton.

This module is intentionally small. It exists to show:
  * how to declare a typed `Agent` with a Pydantic output schema,
  * how to register a tool the model can call,
  * how the model is selected via the ``PYDANTIC_AI_MODEL`` env var so the
    same code works against OpenAI, Anthropic, Gemini, or any other provider
    supported by pydantic-ai.

Replace this with your real agent. Keep the test pattern from
``tests/test_agent.py`` so unit tests never hit a live API.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent

DEFAULT_MODEL = "openai:gpt-5.2"


class CityInfo(BaseModel):
    """Structured response describing a city."""

    city: str = Field(description="City name, e.g. 'Chicago'.")
    country: str = Field(description="ISO country name, e.g. 'United States'.")
    rationale: str = Field(description="One-sentence explanation of the choice.")


def build_agent(model: str | None = None) -> Agent[None, CityInfo]:
    """Create a configured agent.

    Args:
        model: Override the model selector. When ``None``, falls back to
            ``$PYDANTIC_AI_MODEL`` and finally to :data:`DEFAULT_MODEL`.

    Returns:
        A pydantic-ai ``Agent`` parameterised on a :class:`CityInfo` output.
    """
    selected = model or os.getenv("PYDANTIC_AI_MODEL") or DEFAULT_MODEL
    agent: Agent[None, CityInfo] = Agent(
        selected,
        output_type=CityInfo,
        system_prompt=(
            "You answer geography questions. Always return a CityInfo. "
            "If unsure, pick the most likely city and say so in `rationale`."
        ),
    )

    @agent.tool_plain
    def current_utc_time() -> str:
        """Return the current UTC time in ISO-8601. Useful when freshness matters."""
        return datetime.now(UTC).isoformat()

    return agent
