"""Agent factories for the four task types.

We expose two factories per call site:

* :func:`build_candidate_agent` — per-chunk run with the candidate prompt;
* :func:`build_reducer_agent` — final reduction call asking for exactly 10
  questions across all candidates.

Model selection (via env vars, so the same code services every provider):

* ``EXAMINATOR_LLM_PROVIDER``
    - ``openai`` (default): model string from ``PYDANTIC_AI_MODEL`` (default
      ``openai:gpt-5.2``) — pydantic-ai routes that to the matching SDK so
      the same code works against OpenAI, Anthropic, Gemini, ...
    - ``ollama``: talks to a locally hosted Ollama daemon via its
      OpenAI-compatible ``/v1`` API. ``OLLAMA_BASE_URL`` and ``OLLAMA_MODEL``
      configure the endpoint and model name (e.g. ``gemma4:31b``).

Structured-output strategy is controlled by ``EXAMINATOR_OUTPUT_MODE``:

* ``tool`` (default) — pydantic-ai's native tool-calling. Best for OpenAI,
  Anthropic, Gemini.
* ``prompted`` — the JSON schema is inlined into the system prompt and the
  model is asked to return raw JSON. Robust fallback for local models
  without reliable tool-calling (e.g. Gemma).
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
DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434/v1"
DEFAULT_OLLAMA_MODEL = "gemma4:31b"


def _is_ollama() -> bool:
    return os.getenv("EXAMINATOR_LLM_PROVIDER", "openai").lower() == "ollama"


def _is_prompted() -> bool:
    return os.getenv("EXAMINATOR_OUTPUT_MODE", "tool").lower() == "prompted"


def _build_model() -> "str | Model":
    """Pick a pydantic-ai model object/string based on env vars.

    ``EXAMINATOR_LLM_PROVIDER=ollama`` switches to a locally hosted Ollama
    server (OpenAI-compatible API on ``/v1``); everything else falls back to
    the string-based ``PYDANTIC_AI_MODEL`` route, which pydantic-ai resolves
    against whichever provider SDK matches.
    """
    if _is_ollama():
        # Local imports so the OpenAI SDK is only required on the lokal branch.
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        model_name = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        # pydantic-ai requires a non-empty API key string; Ollama ignores it.
        return OpenAIChatModel(
            model_name=model_name,
            provider=OpenAIProvider(base_url=base_url, api_key="ollama"),
        )
    return os.getenv("PYDANTIC_AI_MODEL") or DEFAULT_MODEL


def _selected_model(model: "str | Model | None") -> "str | Model":
    if model is not None:
        return model
    return _build_model()


def _qa_pair_schema(task: TaskType) -> type[PageQuestions]:  # type: ignore[type-arg]
    match task:
        case TaskType.HAUSARBEIT:
            return cast("type[PageQuestions]", PageQuestions[HausarbeitQAPair])
        case TaskType.PROJEKTARBEIT:
            return cast("type[PageQuestions]", PageQuestions[ProjektarbeitQAPair])
        case TaskType.KLAUSUR:
            return cast("type[PageQuestions]", PageQuestions[KlausurQAPair])
        case TaskType.EINSENDEAUFGABE:
            return cast("type[PageQuestions]", PageQuestions[EinsendeaufgabeQAPair])


def _output_type_for(task: TaskType) -> object:
    """Return the concrete output specification for ``task``.

    Honours ``EXAMINATOR_OUTPUT_MODE``: ``tool`` (default) returns the bare
    ``PageQuestions[T]`` class so pydantic-ai issues a native tool call;
    ``prompted`` wraps it in ``PromptedOutput`` which inlines the JSON
    schema into the system prompt instead — essential for local models
    without robust tool-calling.
    """
    schema_cls = _qa_pair_schema(task)
    if _is_prompted():
        # Local import so we don't pay the cost when running in tool mode.
        from pydantic_ai.output import PromptedOutput

        return PromptedOutput(schema_cls)
    return schema_cls


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
