"""A/B benchmark harness for local LLM model + output-mode combinations.

Runs the examinator pipeline against the cross-product of configured Ollama
models and pydantic-ai output modes, recording wall-clock time, success
status, and the number of final questions produced. Emits a Markdown table
for at-a-glance comparison so the lokal-branch default can be picked from
data instead of by guesswork.

Usage:
    uv run python scripts/benchmark_local.py --pdf path/to/sample.pdf
    uv run python scripts/benchmark_local.py --text-file sample.txt --task klausur

Prerequisites:
    - Ollama daemon reachable (default http://localhost:11434).
    - The configured model tags pulled (`ollama pull gemma4:31b`, ...).
    - The examinator package is importable in the current env (i.e. run via
      `uv run python ...` after a `uv sync`).

The script is intentionally not part of CI; it requires a live local Ollama
daemon and is meant to be run by the developer when comparing model/mode
combinations on their own hardware.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from examinator.core.generator import run_generation
from examinator.core.schemas import (
    EinsendeaufgabeJobConfig,
    HausarbeitJobConfig,
    JobConfig,
    KlausurJobConfig,
    PageQuestions,
    ProjektarbeitJobConfig,
    TaskType,
)

DEFAULT_MODELS: tuple[str, ...] = ("gemma4:31b", "qwen3:32b-q4_K_M")
DEFAULT_MODES: tuple[str, ...] = ("tool", "prompted", "native")


@dataclass(slots=True)
class BenchmarkResult:
    """Captured metrics for one (model, mode) combination."""

    model: str
    mode: str
    success: bool
    seconds: float
    final_questions: int
    chunks_processed: int
    error: str | None


def _build_job_config(task: TaskType) -> JobConfig:
    """Construct a minimal, schema-valid :class:`JobConfig` for ``task``.

    All optional fields fall back to their schema defaults; the benchmark
    deliberately exercises the *default* prompt configuration so results
    reflect what a vanilla deployment would see.
    """
    match task:
        case TaskType.HAUSARBEIT:
            return HausarbeitJobConfig()
        case TaskType.PROJEKTARBEIT:
            return ProjektarbeitJobConfig()
        case TaskType.KLAUSUR:
            return KlausurJobConfig()
        case TaskType.EINSENDEAUFGABE:
            return EinsendeaufgabeJobConfig()


async def _run_one(
    *,
    config: JobConfig,
    pdf_bytes: bytes | None,
    plaintext: str | None,
    max_chunks: int,
) -> BenchmarkResult:
    """Drive ``run_generation`` once and collect the metrics we care about."""
    model_name = os.environ.get("OLLAMA_MODEL", "?")
    mode = os.environ.get("EXAMINATOR_OUTPUT_MODE", "tool")

    final_questions = 0
    chunks_processed = 0
    error: str | None = None

    async def _capture(final: PageQuestions) -> None:  # type: ignore[type-arg]
        nonlocal final_questions
        final_questions = len(final.questions)

    started = time.perf_counter()
    try:
        async for event in run_generation(
            config,
            pdf_bytes=pdf_bytes,
            plaintext=plaintext,
            max_chunks=max_chunks,
            on_result=_capture,
        ):
            if event.stage == "chunk_done":
                chunks_processed += 1
            if event.stage == "error":
                error = event.message
                break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - started

    return BenchmarkResult(
        model=model_name,
        mode=mode,
        success=error is None and final_questions > 0,
        seconds=elapsed,
        final_questions=final_questions,
        chunks_processed=chunks_processed,
        error=error,
    )


async def run_matrix(
    *,
    models: Sequence[str],
    modes: Sequence[str],
    config: JobConfig,
    pdf_bytes: bytes | None,
    plaintext: str | None,
    max_chunks: int,
    base_url: str,
) -> list[BenchmarkResult]:
    """Iterate over ``models x modes`` and benchmark each pair sequentially.

    Sequential by design: parallel runs would compete for the same GPU and
    distort wall-clock numbers. The progress lines on stderr keep the
    developer informed during the (typically minutes-long) run.
    """
    results: list[BenchmarkResult] = []
    for model in models:
        for mode in modes:
            os.environ["EXAMINATOR_LLM_PROVIDER"] = "ollama"
            os.environ["OLLAMA_BASE_URL"] = base_url
            os.environ["OLLAMA_MODEL"] = model
            os.environ["EXAMINATOR_OUTPUT_MODE"] = mode
            print(f"-> {model} | {mode} ...", file=sys.stderr, flush=True)
            result = await _run_one(
                config=config,
                pdf_bytes=pdf_bytes,
                plaintext=plaintext,
                max_chunks=max_chunks,
            )
            results.append(result)
            status = "OK" if result.success else "FAIL"
            suffix = f"  error={result.error}" if result.error else ""
            print(
                f"   {status} in {result.seconds:.1f}s "
                f"(final={result.final_questions}, chunks={result.chunks_processed})"
                f"{suffix}",
                file=sys.stderr,
                flush=True,
            )
    return results


def render_markdown(results: Sequence[BenchmarkResult]) -> str:
    """Render the benchmark matrix as a Markdown table."""
    rows = [
        "| Model | Mode | Status | Wall-clock (s) | Final Questions | Chunks | Error |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for r in results:
        status = "OK" if r.success else "FAIL"
        rows.append(
            f"| `{r.model}` | `{r.mode}` | {status}"
            f" | {r.seconds:.1f} | {r.final_questions} | {r.chunks_processed}"
            f" | {r.error or ''} |"
        )
    return "\n".join(rows) + "\n"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Benchmark local Ollama (model, output_mode) combinations against "
            "the examinator pipeline and print a Markdown comparison table."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--pdf", type=Path, help="Path to a PDF file to run through the pipeline.")
    src.add_argument("--text-file", type=Path, help="Path to a plaintext file.")
    p.add_argument(
        "--task",
        choices=[t.value for t in TaskType],
        default=TaskType.KLAUSUR.value,
        help="Which task type to benchmark (affects schemas/prompts).",
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="Ollama model tags to benchmark (cross-product with --modes).",
    )
    p.add_argument(
        "--modes",
        nargs="+",
        choices=["tool", "prompted", "native"],
        default=list(DEFAULT_MODES),
        help="EXAMINATOR_OUTPUT_MODE values to benchmark.",
    )
    p.add_argument(
        "--max-chunks",
        type=int,
        default=2,
        help="Cap on chunks per run (smaller = faster benchmark). Default: 2.",
    )
    p.add_argument(
        "--base-url",
        default="http://localhost:11434/v1",
        help="OpenAI-compatible base URL of your Ollama daemon.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional file path to write the Markdown table to.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    pdf_bytes: bytes | None = None
    plaintext: str | None = None
    if args.pdf is not None:
        pdf_bytes = args.pdf.read_bytes()
    else:
        plaintext = args.text_file.read_text(encoding="utf-8")

    task = TaskType(args.task)
    config = _build_job_config(task)

    results = asyncio.run(
        run_matrix(
            models=args.models,
            modes=args.modes,
            config=config,
            pdf_bytes=pdf_bytes,
            plaintext=plaintext,
            max_chunks=args.max_chunks,
            base_url=args.base_url,
        )
    )

    markdown = render_markdown(results)
    print()
    print(markdown)

    if args.out is not None:
        args.out.write_text(markdown, encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)

    failures = sum(1 for r in results if not r.success)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
