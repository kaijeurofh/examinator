"""FastAPI app exposing the question-generation pipeline.

Routes:

* ``POST /api/jobs`` (multipart)  -> queue a generation job.
* ``GET  /api/jobs/{id}/events``  -> SSE stream of progress events.
* ``GET  /api/jobs/{id}``         -> final JSON result.
* ``GET  /api/jobs/{id}/excel``   -> `.xlsx` download.
* ``GET  /api/health``            -> readiness probe.

The app uses a single in-process :class:`JobStore`, so it must be run with
``uvicorn ... --workers 1``. The store enforces a TTL so the process does
not grow unbounded across long-running deployments.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import TypeAdapter, ValidationError
from sse_starlette.sse import EventSourceResponse

from examinator.api.jobs import Job, JobStore
from examinator.core.excel_export import filename_for, to_xlsx_bytes
from examinator.core.generator import run_generation
from examinator.core.schemas import (
    JobConfig,
    JobStatus,
    PageQuestions,
    ProgressEvent,
    TaskType,
)

_logger = logging.getLogger(__name__)


def _max_pdf_bytes() -> int:
    return int(os.getenv("EXAMINATOR_MAX_PDF_MB", "20")) * 1024 * 1024


def _max_chunks() -> int:
    return int(os.getenv("EXAMINATOR_MAX_CHUNKS", "8"))


def _cors_origins() -> list[str]:
    raw = os.getenv("EXAMINATOR_CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


_job_config_adapter: TypeAdapter[JobConfig] = TypeAdapter(JobConfig)


def get_store(request: Request) -> JobStore:
    return request.app.state.job_store  # type: ignore[no-any-return]


@contextlib.asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    store = JobStore()
    app.state.job_store = store
    await store.start_janitor()
    try:
        yield
    finally:
        await store.stop_janitor()


app = FastAPI(
    title="Examinator API",
    version="0.1.0",
    lifespan=_lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    config_json: Annotated[str, Form(alias="config")],
    pdf: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
    store: JobStore = Depends(get_store),  # noqa: B008
) -> dict[str, str]:
    """Create a new generation job. The ``config`` form field carries a JSON
    blob that validates against :data:`JobConfig`; either ``pdf`` or ``text``
    must be supplied as the study material.
    """
    try:
        parsed = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"`config` is not valid JSON: {exc}",
        ) from exc

    try:
        config = _job_config_adapter.validate_python(parsed)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    pdf_bytes: bytes | None = None
    if pdf is not None:
        pdf_bytes = await pdf.read()
        if len(pdf_bytes) > _max_pdf_bytes():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"PDF exceeds {_max_pdf_bytes() // (1024 * 1024)} MB limit.",
            )
        if not pdf_bytes:
            pdf_bytes = None

    plaintext: str | None = text.strip() if text else None
    if pdf_bytes is None and not plaintext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either `pdf` or `text` must be supplied.",
        )

    job = await store.create(config)
    job.task = asyncio.create_task(
        _run_job(job, pdf_bytes=pdf_bytes, plaintext=plaintext),
        name=f"job-{job.id}",
    )
    return {"job_id": job.id}


async def _run_job(
    job: Job,
    *,
    pdf_bytes: bytes | None,
    plaintext: str | None,
) -> None:
    """Drive :func:`run_generation` and fan-out events to subscribers."""
    job.status = JobStatus.RUNNING

    async def on_result(result: PageQuestions) -> None:  # type: ignore[type-arg]
        job.result = result
        job.excel_bytes = to_xlsx_bytes(result, TaskType(job.config.task_type))

    final_stage: str | None = None
    try:
        async for event in run_generation(
            job.config,
            pdf_bytes=pdf_bytes,
            plaintext=plaintext,
            max_chunks=_max_chunks(),
            on_result=on_result,
        ):
            job.fanout(event)
            final_stage = event.stage
            if event.stage == "error":
                job.error = event.message
    except Exception as exc:
        _logger.exception("job %s crashed", job.id)
        job.error = str(exc)
        job.fanout(ProgressEvent(stage="error", message=str(exc)))
        final_stage = "error"

    if final_stage == "done":
        job.status = JobStatus.DONE
    else:
        job.status = JobStatus.ERROR
    job.finished_at = time.time()
    job.close_subscribers()


@app.get("/api/jobs/{job_id}/events")
async def stream_events(
    job_id: str,
    request: Request,
    store: JobStore = Depends(get_store),  # noqa: B008
) -> EventSourceResponse:
    """Server-Sent Events stream of progress events for one job."""
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job id")

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        async for event in store.subscribe(job_id):
            if await request.is_disconnected():
                return
            yield {"event": event.stage, "data": event.model_dump_json()}

    return EventSourceResponse(event_generator())


@app.get("/api/jobs/{job_id}")
async def get_job(
    job_id: str,
    store: JobStore = Depends(get_store),  # noqa: B008
) -> JSONResponse:
    """Return the final result (or current state + recent events) as JSON."""
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job id")

    payload: dict[str, Any] = {
        "job_id": job.id,
        "status": job.status.value,
        "task_type": TaskType(job.config.task_type).value,
        "error": job.error,
        "events": [e.model_dump() for e in job.events[-20:]],
    }
    if job.result is not None:
        payload["result"] = job.result.model_dump()
    return JSONResponse(payload)


@app.get("/api/jobs/{job_id}/excel")
async def download_excel(
    job_id: str,
    store: JobStore = Depends(get_store),  # noqa: B008
) -> Response:
    """Return the generated `.xlsx` workbook as a file download."""
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job id")
    if job.status != JobStatus.DONE or job.excel_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has not produced a result yet.",
        )

    task_type = TaskType(job.config.task_type)
    filename = filename_for(task_type)
    return StreamingResponse(
        iter([job.excel_bytes]),
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
