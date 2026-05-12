"""Orchestrate the chunked-with-overlap question generation strategy.

Flow per job:

1. Parse the input into pages (PDF or plain text).
2. Build page-aware chunks with overlap.
3. For each chunk: ask the candidate agent for up to N grounded questions.
4. Pool all candidates and run the reducer agent to pick exactly 10 final,
   non-overlapping questions.

The function is an async generator that yields :class:`ProgressEvent`
payloads suitable for direct forwarding over SSE; the final event before
``done`` carries the serialised result via a side-channel callback so the API
layer can persist it in the in-memory job store.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING

from examinator.core.agent import build_candidate_agent, build_reducer_agent
from examinator.core.chunking import Chunk, chunk_pages
from examinator.core.pdf_parser import (
    PageText,
    PdfParseError,
    extract_pages_from_bytes,
    pages_from_plaintext,
)
from examinator.core.schemas import (
    JobConfig,
    PageQuestions,
    ProgressEvent,
    TaskType,
    qa_pair_type_for,
)

if TYPE_CHECKING:
    from pydantic_ai.models import Model

_logger = logging.getLogger(__name__)

_MAX_CANDIDATES_FORWARDED = 40

ResultCallback = Callable[[PageQuestions], Awaitable[None]]  # type: ignore[type-arg]


def parse_input(
    *,
    pdf_bytes: bytes | None,
    plaintext: str | None,
    max_chunks: int,
) -> list[Chunk]:
    """Parse PDF/plaintext into chunks. Pure-CPU, no LLM."""
    pages: list[PageText]
    if pdf_bytes is not None:
        pages = extract_pages_from_bytes(pdf_bytes)
    elif plaintext:
        pages = pages_from_plaintext(plaintext)
    else:
        raise ValueError("Either pdf_bytes or plaintext must be provided.")
    return chunk_pages(pages, max_chunks=max_chunks)


def _format_chunk_user_prompt(chunk: Chunk) -> str:
    return (
        f"{chunk.header()}\n\n"
        "Use the following study material chunk as your single source of "
        "truth for grounding `source_page` values. The chunk covers pages "
        f"{chunk.start_page}-{chunk.end_page}. Generate candidate questions "
        "drawn from this chunk only.\n\n"
        f"---\n{chunk.text}\n---"
    )


def _format_reducer_user_prompt(candidates: PageQuestions) -> str:  # type: ignore[type-arg]
    payload = candidates.model_dump_json(indent=2)
    return (
        "Below is a pool of candidate questions generated from different "
        "chunks of the same study material. Select and refine exactly 10 "
        "final questions that together cover distinct conceptual aspects, "
        "with no near-duplicates. Preserve the existing `source_page` of "
        "whichever candidate you retain (or merge from).\n\n"
        "Candidates JSON:\n"
        f"{payload}"
    )


async def run_generation(
    config: JobConfig,
    *,
    pdf_bytes: bytes | None,
    plaintext: str | None,
    max_chunks: int = 8,
    on_result: ResultCallback | None = None,
    model: "str | Model | None" = None,
) -> AsyncIterator[ProgressEvent]:
    """Run the full pipeline and yield progress events.

    The function is intentionally written as an async generator so the FastAPI
    handler can simply ``async for ev in run_generation(...)`` and forward each
    event into an SSE stream. The final :class:`PageQuestions` result is
    delivered via ``on_result`` rather than yielded so the SSE channel stays
    homogeneous (progress events only).
    """
    yield ProgressEvent(stage="parsing", message="Parse Eingabe ...")

    try:
        chunks = parse_input(
            pdf_bytes=pdf_bytes,
            plaintext=plaintext,
            max_chunks=max_chunks,
        )
    except (ValueError, PdfParseError) as exc:
        yield ProgressEvent(stage="error", message=str(exc))
        return

    if not chunks:
        yield ProgressEvent(stage="error", message="Keine Inhalte zum Verarbeiten.")
        return

    yield ProgressEvent(
        stage="chunking",
        message=f"{len(chunks)} Chunks erzeugt.",
        total=len(chunks),
    )

    candidate_agent = build_candidate_agent(config, model=model)
    qa_type = qa_pair_type_for(TaskType(config.task_type))

    all_candidates: list[object] = []  # narrowed below at append site
    for i, chunk in enumerate(chunks, start=1):
        yield ProgressEvent(
            stage="chunk_started",
            message=f"Chunk {i}/{len(chunks)} (Seiten {chunk.start_page}-{chunk.end_page})",
            current=i,
            total=len(chunks),
        )
        try:
            run = await candidate_agent.run(_format_chunk_user_prompt(chunk))
        except Exception as exc:  # noqa: BLE001 - LLM/network errors vary by provider
            _logger.exception("candidate run failed", extra={"chunk_index": i})
            yield ProgressEvent(
                stage="error",
                message=f"Chunk {i} fehlgeschlagen: {exc}",
            )
            return
        output: PageQuestions = run.output  # type: ignore[assignment]
        for q in output.questions:
            if isinstance(q, qa_type):
                all_candidates.append(q)
        yield ProgressEvent(
            stage="chunk_done",
            message=f"Chunk {i}/{len(chunks)} fertig ({len(output.questions)} Kandidaten).",
            current=i,
            total=len(chunks),
        )

    if not all_candidates:
        yield ProgressEvent(stage="error", message="Keine Kandidatenfragen erzeugt.")
        return

    # Cap the candidate pool we forward to the reducer — very large pools waste
    # tokens and rarely improve quality.
    pool = all_candidates[:_MAX_CANDIDATES_FORWARDED]
    pool_container: PageQuestions = PageQuestions(questions=pool)  # type: ignore[arg-type]

    yield ProgressEvent(
        stage="reducing",
        message=f"Reduziere {len(pool)} Kandidaten auf 10 finale Fragen ...",
        total=len(pool),
    )

    reducer = build_reducer_agent(config, model=model)
    try:
        reduce_run = await reducer.run(_format_reducer_user_prompt(pool_container))
    except Exception as exc:  # noqa: BLE001
        _logger.exception("reducer run failed")
        yield ProgressEvent(stage="error", message=f"Reduce-Schritt fehlgeschlagen: {exc}")
        return

    final: PageQuestions = reduce_run.output  # type: ignore[assignment]

    # Enforce the contract: trim if the LLM ignored the "exactly 10" instruction.
    if len(final.questions) > 10:
        final = PageQuestions(questions=final.questions[:10])  # type: ignore[arg-type]

    if on_result is not None:
        await on_result(final)

    yield ProgressEvent(
        stage="done",
        message=f"Fertig. {len(final.questions)} Fragen generiert.",
        current=len(final.questions),
        total=10,
    )
