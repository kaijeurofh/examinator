"""Agent factories for the four task types.

We expose two factories per call site:

* :func:`build_candidate_agent` — per-chunk run with the candidate prompt;
* :func:`build_reducer_agent` — final reduction call asking for exactly 10
  questions across all candidates.

The model is selected via ``$PYDANTIC_AI_MODEL`` (default ``openai:gpt-5.2``)
so the same code works against OpenAI, Anthropic, Gemini, etc.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from pydantic_ai import Agent

from examinator.core.prompts import candidate_prompt_for, reducer_prompt_for
from examinator.core.schemas import (
    EinsendeaufgabeQAPair,
    HausarbeitQAPair,
    JobConfig,
    KlausurQAPair,
    PageQuestions,
    ProjektarbeitQAPair,
    TaskType,
)

if TYPE_CHECKING:
    from pydantic_ai.models import Model

DEFAULT_MODEL = "openai:gpt-5.2"


def _selected_model(model: "str | Model | None") -> "str | Model":
    if model is not None:
        return model
    return os.getenv("PYDANTIC_AI_MODEL") or DEFAULT_MODEL


def _output_type_for(task: TaskType) -> type[PageQuestions]:  # type: ignore[type-arg]
    """Return the concrete `PageQuestions[T]` parametrisation for ``task``."""
    match task:
        case TaskType.HAUSARBEIT:
            return cast("type[PageQuestions]", PageQuestions[HausarbeitQAPair])
        case TaskType.PROJEKTARBEIT:
            return cast("type[PageQuestions]", PageQuestions[ProjektarbeitQAPair])
        case TaskType.KLAUSUR:
            return cast("type[PageQuestions]", PageQuestions[KlausurQAPair])
        case TaskType.EINSENDEAUFGABE:
            return cast("type[PageQuestions]", PageQuestions[EinsendeaufgabeQAPair])


def build_candidate_agent(
    config: JobConfig,
    *,
    model: "str | Model | None" = None,
) -> Agent[None, PageQuestions]:  # type: ignore[type-arg]
    """Build the per-chunk candidate-generation agent for the given job."""
    return Agent(
        _selected_model(model),
        output_type=_output_type_for(TaskType(config.task_type)),
        system_prompt=candidate_prompt_for(config),
    )


def build_reducer_agent(
    config: JobConfig,
    *,
    model: "str | Model | None" = None,
) -> Agent[None, PageQuestions]:  # type: ignore[type-arg]
    """Build the final reducer agent that selects exactly 10 questions."""
    return Agent(
        _selected_model(model),
        output_type=_output_type_for(TaskType(config.task_type)),
        system_prompt=reducer_prompt_for(config),
    )


def build_agent_for_task(
    config: JobConfig,
    *,
    stage: str = "candidate",
    model: "str | Model | None" = None,
) -> Agent[None, PageQuestions]:  # type: ignore[type-arg]
    """Convenience entry-point used in tests and from the public package API."""
    if stage == "reducer":
        return build_reducer_agent(config, model=model)
    return build_candidate_agent(config, model=model)
