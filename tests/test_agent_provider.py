"""Tests for the provider/output-mode switch in :mod:`examinator.core.agent`.

All tests run entirely offline. They never open a socket; they only assert
that ``_build_model`` and ``_output_type_for`` pick the right artefacts for
each combination of ``EXAMINATOR_LLM_PROVIDER``, ``EXAMINATOR_OUTPUT_MODE``,
``PYDANTIC_AI_MODEL``, ``OLLAMA_BASE_URL`` and ``OLLAMA_MODEL``.
"""

from __future__ import annotations

import inspect

import pytest

# Pre-import the symbols we'll need at test time so an ImportError surfaces
# as a collection error rather than a confusing AssertionError later.
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import NativeOutput, PromptedOutput

from examinator.core import agent as agent_module
from examinator.core.agent import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_MODEL,
    _build_model,
    _output_type_for,
    build_candidate_agent,
    build_reducer_agent,
)
from examinator.core.schemas import (
    HausarbeitJobConfig,
    KlausurJobConfig,
    TaskType,
)

# ---------------------------------------------------------------------------
# _build_model
# ---------------------------------------------------------------------------


def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every var the model factory honours, so each test starts clean."""
    for key in (
        "EXAMINATOR_LLM_PROVIDER",
        "EXAMINATOR_OUTPUT_MODE",
        "PYDANTIC_AI_MODEL",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_build_model_defaults_to_openai_model_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    assert _build_model() == DEFAULT_MODEL


def test_build_model_respects_pydantic_ai_model_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("PYDANTIC_AI_MODEL", "anthropic:claude-3-5-sonnet-latest")
    assert _build_model() == "anthropic:claude-3-5-sonnet-latest"


def test_build_model_returns_openai_chat_model_for_ollama_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_LLM_PROVIDER", "ollama")
    model = _build_model()
    assert isinstance(model, OpenAIChatModel)
    # pydantic-ai's OpenAIChatModel.__repr__ drops the model name, so probe
    # the attribute directly to avoid coupling to an undocumented format.
    assert model.model_name == DEFAULT_OLLAMA_MODEL


def test_build_model_uses_ollama_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://other-host:11434/v1")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:14b")
    model = _build_model()
    assert isinstance(model, OpenAIChatModel)
    # See note in the previous test about the repr being unhelpful here.
    assert model.model_name == "qwen2.5:14b"


# ---------------------------------------------------------------------------
# _output_type_for
# ---------------------------------------------------------------------------


def test_output_type_for_tool_mode_returns_a_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    out = _output_type_for(TaskType.HAUSARBEIT)
    # Tool mode hands pydantic-ai a bare Pydantic class (the PageQuestions[T]
    # alias resolves to a concrete subclass in pydantic v2).
    assert inspect.isclass(out)
    assert not isinstance(out, PromptedOutput)
    assert not isinstance(out, NativeOutput)


def test_output_type_for_prompted_mode_wraps_in_prompted_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "prompted")
    out = _output_type_for(TaskType.KLAUSUR)
    assert isinstance(out, PromptedOutput)


def test_output_type_for_native_mode_wraps_in_native_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``native`` mode must produce a :class:`NativeOutput` wrapper so that
    pydantic-ai forwards the JSON schema via ``response_format`` instead of
    inlining it into the prompt.
    """
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "native")
    out = _output_type_for(TaskType.HAUSARBEIT)
    assert isinstance(out, NativeOutput)


def test_output_type_for_unknown_mode_falls_back_to_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A misspelled ``EXAMINATOR_OUTPUT_MODE`` must not silently degrade into
    one of the strict wrappers; it falls back to the bare class (tool mode).
    """
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "definitely-not-a-mode")
    out = _output_type_for(TaskType.KLAUSUR)
    assert inspect.isclass(out)
    assert not isinstance(out, PromptedOutput)
    assert not isinstance(out, NativeOutput)


def test_output_type_for_each_task_type_has_distinct_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each TaskType must map to a different schema class in tool mode."""
    _clear_provider_env(monkeypatch)
    seen = {
        task: _output_type_for(task)
        for task in (
            TaskType.HAUSARBEIT,
            TaskType.PROJEKTARBEIT,
            TaskType.KLAUSUR,
            TaskType.EINSENDEAUFGABE,
        )
    }
    # All four classes should be distinct objects.
    assert len({id(cls) for cls in seen.values()}) == 4


# ---------------------------------------------------------------------------
# Public factories — smoke tests (offline, no SDK round-trip)
# ---------------------------------------------------------------------------


def test_build_candidate_agent_smoke_with_ollama_prompted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Constructing the agent against Ollama in prompted mode is lazy/offline."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "prompted")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example.invalid:11434/v1")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:31b")
    agent = build_candidate_agent(HausarbeitJobConfig(task_type=TaskType.HAUSARBEIT))
    assert agent is not None


def test_build_reducer_agent_smoke_with_ollama_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "tool")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example.invalid:11434/v1")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:31b")
    agent = build_reducer_agent(KlausurJobConfig(task_type=TaskType.KLAUSUR))
    assert agent is not None


def test_is_helpers_react_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_provider_env(monkeypatch)
    assert agent_module._is_ollama() is False
    assert agent_module._is_prompted() is False
    assert agent_module._output_mode() == "tool"

    monkeypatch.setenv("EXAMINATOR_LLM_PROVIDER", "OLLAMA")  # case-insensitive
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "Prompted")
    assert agent_module._is_ollama() is True
    assert agent_module._is_prompted() is True
    assert agent_module._output_mode() == "prompted"


def test_output_mode_recognises_native(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_output_mode`` must accept ``native`` (case-insensitive) and the
    legacy ``_is_prompted`` shim must report ``False`` for it.
    """
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("EXAMINATOR_OUTPUT_MODE", "Native")
    assert agent_module._output_mode() == "native"
    assert agent_module._is_prompted() is False
