"""In-memory job store for the stateless single-tenant deployment.

Each job is created when the API receives a POST /api/jobs, then a background
asyncio task drives :func:`examinator.core.generator.run_generation` and
appends every progress event into the job's queue. SSE subscribers consume
from a fan-out copy of the queue. The whole store is process-local; the
FastAPI app must be run with a single worker.

A periodic janitor evicts jobs older than ``ttl`` seconds so the process
does not grow unbounded.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from examinator.core.schemas import JobConfig, JobStatus, PageQuestions, ProgressEvent

_logger = logging.getLogger(__name__)

# Sentinel that closes any active SSE subscriber.
_DONE = object()


@dataclass
class Job:
    """One question-generation job tracked in memory."""

    id: str
    config: JobConfig
    status: JobStatus = JobStatus.QUEUED
    events: list[ProgressEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue[ProgressEvent | object]] = field(default_factory=list)
    result: PageQuestions | None = None  # type: ignore[type-arg]
    excel_bytes: bytes | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    task: asyncio.Task[None] | None = None

    def fanout(self, event: ProgressEvent) -> None:
        """Append ``event`` to history and push it to every live subscriber."""
        self.events.append(event)
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - unbounded queue
                _logger.warning("subscriber queue full; dropping event")

    def close_subscribers(self) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(_DONE)
            except asyncio.QueueFull:  # pragma: no cover
                pass


class JobStore:
    """Process-local job registry plus a TTL janitor."""

    def __init__(self, *, ttl_seconds: float = 60 * 60) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl_seconds
        self._janitor: asyncio.Task[None] | None = None

    async def create(self, config: JobConfig) -> Job:
        async with self._lock:
            job = Job(id=uuid.uuid4().hex, config=config)
            self._jobs[job.id] = job
            return job

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def subscribe(self, job_id: str) -> AsyncIterator[ProgressEvent]:
        """Yield progress events for ``job_id`` until the job terminates.

        Replays any events already in the job's history so a late subscriber
        does not miss the early stages.
        """
        job = await self.get(job_id)
        if job is None:
            raise KeyError(job_id)

        queue: asyncio.Queue[ProgressEvent | object] = asyncio.Queue()
        job.subscribers.append(queue)

        # Replay history before honouring live events.
        history = list(job.events)
        terminal = job.status in {JobStatus.DONE, JobStatus.ERROR}
        try:
            for event in history:
                yield event
            if terminal:
                return
            while True:
                item = await queue.get()
                if item is _DONE:
                    return
                yield item  # type: ignore[misc]
        finally:
            try:
                job.subscribers.remove(queue)
            except ValueError:  # pragma: no cover - already removed
                pass

    async def start_janitor(self) -> None:
        if self._janitor is None or self._janitor.done():
            self._janitor = asyncio.create_task(self._janitor_loop(), name="job-janitor")

    async def stop_janitor(self) -> None:
        if self._janitor is not None and not self._janitor.done():
            self._janitor.cancel()
            try:
                await self._janitor
            except asyncio.CancelledError:
                pass

    async def _janitor_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(min(self._ttl / 4, 300))
                now = time.time()
                async with self._lock:
                    expired = [
                        jid
                        for jid, job in self._jobs.items()
                        if job.finished_at is not None
                        and now - job.finished_at > self._ttl
                    ]
                    for jid in expired:
                        _logger.info("evicting job %s after TTL", jid)
                        del self._jobs[jid]
        except asyncio.CancelledError:
            raise
