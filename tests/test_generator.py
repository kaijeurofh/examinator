"""Tests for `examinator.core.generator`.

We mock the LLM by monkeypatching :func:`build_candidate_agent` and
:func:`build_reducer_agent` so the orchestration logic runs end-to-end
without ever touching a real provider — see ``AGENTS.md`` for the rule.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from examinator.core import generator as gen_module
from examinator.core.generator import run_generation
from examinator.core.schemas import (
    AcademicLevel,
    HausarbeitJobConfig,
    HausarbeitQAPair,
    PageQuestions,
    ProgressEvent,
    TaskType,
)


def _pair(idx: int, page: int = 1) -> HausarbeitQAPair:
    return HausarbeitQAPair(
        question=f"Frage {idx}",
        question_type="Analytische Frage",
        academic_level=AcademicLevel.BACHELOR,
        scope="3.500-4.500 Woerter",
        core_topic="Topic",
        guideline_examiner="ex",
        guideline_student="st",
        bewertungsschema_rubric="rub",
        source_page=page,
    )


@dataclass
class _StubResult:
    output: PageQuestions[HausarbeitQAPair]


class _StubAgent:
    """Drop-in replacement for `pydantic_ai.Agent` with a fixed response."""

    def __init__(self, response_factory: Callable[[str], PageQuestions[HausarbeitQAPair]]) -> None:
        self._factory = response_factory

    async def run(self, user_prompt: str) -> _StubResult:
        return _StubResult(output=self._factory(user_prompt))


@pytest.fixture
def stub_agents(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace candidate + reducer factories with deterministic stubs.

    Returns a list that records every user prompt the stubs saw, which lets
    tests assert on the orchestration order.
    """
    seen: list[str] = []

    def candidate_factory(prompt: str) -> PageQuestions[HausarbeitQAPair]:
        seen.append(f"candidate:{prompt[:30]}")
        return PageQuestions[HausarbeitQAPair](questions=[_pair(idx=i) for i in range(2)])

    def reducer_factory(prompt: str) -> PageQuestions[HausarbeitQAPair]:
        seen.append(f"reducer:{prompt[:30]}")
        return PageQuestions[HausarbeitQAPair](
            questions=[_pair(idx=i) for i in range(12)]  # 12 > 10 -> must be trimmed
        )

    def fake_candidate(config: Any, model: Any = None) -> _StubAgent:  # noqa: ARG001
        return _StubAgent(candidate_factory)

    def fake_reducer(config: Any, model: Any = None) -> _StubAgent:  # noqa: ARG001
        return _StubAgent(reducer_factory)

    monkeypatch.setattr(gen_module, "build_candidate_agent", fake_candidate)
    monkeypatch.setattr(gen_module, "build_reducer_agent", fake_reducer)
    return seen


async def _collect(iterable: AsyncIterator[ProgressEvent]) -> list[ProgressEvent]:
    events: list[ProgressEvent] = []
    async for ev in iterable:
        events.append(ev)
    return events


async def test_run_generation_yields_expected_stages_and_caps_at_ten(
    stub_agents: list[str],
) -> None:
    config = HausarbeitJobConfig(task_type=TaskType.HAUSARBEIT)
    captured_result: dict[str, PageQuestions[HausarbeitQAPair]] = {}

    async def on_result(result: PageQuestions[HausarbeitQAPair]) -> None:
        captured_result["x"] = result

    text = "Lorem ipsum dolor sit amet. " * 400  # enough for multiple chunks
    events = await _collect(
        run_generation(
            config,
            pdf_bytes=None,
            plaintext=text,
            max_chunks=3,
            on_result=on_result,
        )
    )

    stages = [e.stage for e in events]
    assert stages[0] == "parsing"
    assert "chunking" in stages
    assert "reducing" in stages
    assert stages[-1] == "done"
    assert "error" not in stages

    # Reducer trimmed 12 -> 10.
    assert "x" in captured_result
    assert len(captured_result["x"].questions) == 10
    # Both factories were invoked.
    assert any(s.startswith("candidate:") for s in stub_agents)
    assert any(s.startswith("reducer:") for s in stub_agents)


async def test_run_generation_requires_some_input() -> None:
    config = HausarbeitJobConfig(task_type=TaskType.HAUSARBEIT)
    events = await _collect(run_generation(config, pdf_bytes=None, plaintext=None, max_chunks=2))
    assert events[-1].stage == "error"
