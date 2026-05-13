"""Integration tests for the FastAPI app using `TestClient`.

The generator is monkeypatched to a deterministic in-memory pipeline so the
HTTP, multipart, SSE, and Excel-download wiring is exercised without ever
calling a real LLM.
"""

from __future__ import annotations

import io
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from examinator.api import app as app_module
from examinator.core.schemas import (
    AcademicLevel,
    HausarbeitQAPair,
    PageQuestions,
    ProgressEvent,
)


def _pair(i: int) -> HausarbeitQAPair:
    return HausarbeitQAPair(
        question=f"Frage {i}",
        question_type="Analytische Frage",
        academic_level=AcademicLevel.BACHELOR,
        scope="3.500-4.500 Woerter",
        core_topic="Topic",
        guideline_examiner="ex",
        guideline_student="st",
        bewertungsschema_rubric="rub",
        source_page=i,
    )


@pytest.fixture
def patched_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_generation(
        config: Any,
        *,
        pdf_bytes: bytes | None,
        plaintext: str | None,
        max_chunks: int = 8,
        on_result: Callable[[PageQuestions[HausarbeitQAPair]], Awaitable[None]] | None = None,
        model: Any = None,
    ) -> AsyncIterator[ProgressEvent]:
        # Keep arguments referenced so the linter is happy and so a future
        # refactor that drops one immediately fails this test.
        _ = (config, pdf_bytes, plaintext, max_chunks, model)
        yield ProgressEvent(stage="parsing", message="parse")
        yield ProgressEvent(stage="chunking", total=1, message="1 chunk")
        yield ProgressEvent(stage="chunk_started", current=1, total=1)
        yield ProgressEvent(stage="chunk_done", current=1, total=1)
        if on_result is not None:
            await on_result(
                PageQuestions[HausarbeitQAPair](questions=[_pair(i) for i in range(1, 11)])
            )
        yield ProgressEvent(stage="done", current=10, total=10)

    monkeypatch.setattr(app_module, "run_generation", fake_run_generation)


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Use TestClient as a context manager so FastAPI's lifespan runs and
    # ``app.state.job_store`` is populated. Without this, every route that
    # depends on ``get_store`` raises ``AttributeError``.
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_job_rejects_missing_material(client: TestClient) -> None:
    res = client.post(
        "/api/jobs",
        data={"config": json.dumps({"task_type": "hausarbeit"})},
    )
    assert res.status_code == 400


def test_create_job_rejects_invalid_config_json(client: TestClient) -> None:
    res = client.post(
        "/api/jobs",
        data={"config": "{not json"},
    )
    assert res.status_code == 400


def test_create_job_rejects_unknown_task_type(client: TestClient) -> None:
    res = client.post(
        "/api/jobs",
        data={"config": json.dumps({"task_type": "made-up"}), "text": "hello"},
    )
    assert res.status_code == 422


def test_end_to_end_flow_with_plaintext(
    client: TestClient,
    patched_generator: None,  # noqa: ARG001 - fixture activates monkeypatch
) -> None:
    payload = {
        "task_type": "hausarbeit",
        "language": "Deutsch",
        "core_topics": ["Marketing"],
        "academic_level": "Bachelor",
    }
    res = client.post(
        "/api/jobs",
        data={"config": json.dumps(payload), "text": "Studienmaterial..."},
    )
    assert res.status_code == 202, res.text
    job_id = res.json()["job_id"]

    # Stream SSE events until "done" appears.
    with client.stream("GET", f"/api/jobs/{job_id}/events") as stream:
        seen_stages: list[str] = []
        for line in stream.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                seen_stages.append(line.split(":", 1)[1].strip())
            if "done" in seen_stages:
                break
    assert "done" in seen_stages

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "done"
    assert len(final["result"]["questions"]) == 10

    download = client.get(f"/api/jobs/{job_id}/excel")
    assert download.status_code == 200
    assert download.content[:2] == b"PK"
    assert "attachment" in download.headers["content-disposition"]


def test_pdf_upload_too_large(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    patched_generator: None,  # noqa: ARG001
) -> None:
    monkeypatch.setenv("EXAMINATOR_MAX_PDF_MB", "1")
    big = b"x" * (2 * 1024 * 1024)
    res = client.post(
        "/api/jobs",
        data={"config": json.dumps({"task_type": "hausarbeit"})},
        files={"pdf": ("doc.pdf", io.BytesIO(big), "application/pdf")},
    )
    assert res.status_code == 413


def test_excel_endpoint_404_for_unknown_job(
    client: TestClient,
) -> None:
    res = client.get("/api/jobs/non-existent/excel")
    assert res.status_code == 404
