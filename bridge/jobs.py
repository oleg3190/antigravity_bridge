from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field

from .models import CreateJobRequest, Job, JobStatus
from .orchestrator import Orchestrator

log = logging.getLogger(__name__)


@dataclass
class RuntimeJob:
    job: Job
    task: asyncio.Task | None = None
    subscribers: list[asyncio.Queue] = field(default_factory=list)


class JobManager:
    def __init__(self, max_concurrent: int = 2, timeout: int = 900):
        self.jobs: dict[str, RuntimeJob] = {}
        self.sem = asyncio.Semaphore(max_concurrent)
        self.orchestrator = Orchestrator(timeout)

    async def create(self, req: CreateJobRequest) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            status=JobStatus.QUEUED,
            workspace=req.workspace,
            task=req.task,
        )
        runtime = RuntimeJob(job=job)
        self.jobs[job_id] = runtime
        runtime.task = asyncio.create_task(self._run(runtime, req))
        return job

    async def _publish(self, runtime: RuntimeJob, event: dict):
        runtime.job.events.append(event)
        for q in list(runtime.subscribers):
            await q.put(event)

    async def _run(self, runtime: RuntimeJob, req: CreateJobRequest):
        async with self.sem:
            runtime.job.status = JobStatus.RUNNING
            await self._publish(runtime, {"type": "status", "status": "running"})

            async def sink(kind, data):
                await self._publish(runtime, {"type": kind, "data": data})

            try:
                result = await asyncio.wait_for(
                    self.orchestrator.execute(
                        req.workspace,
                        req.task,
                        run_verification=req.run_tests,
                        test_command=req.test_command,
                        event_sink=sink,
                    ),
                    timeout=self.orchestrator.job_timeout,
                )
                runtime.job.result = result
                if result.tests_passed is False:
                    runtime.job.status = JobStatus.TEST_FAILED
                else:
                    runtime.job.status = JobStatus.SUCCEEDED
                await self._publish(
                    runtime,
                    {"type": "status", "status": runtime.job.status.value},
                )
            except asyncio.CancelledError:
                runtime.job.status = JobStatus.CANCELED
                await self._publish(runtime, {"type": "status", "status": "canceled"})
                raise
            except Exception as exc:
                runtime.job.status = JobStatus.FAILED
                runtime.job.error = str(exc)
                await self._publish(
                    runtime,
                    {"type": "error", "error": str(exc)},
                )

    def get(self, job_id: str) -> Job | None:
        r = self.jobs.get(job_id)
        return r.job if r else None

    async def cancel(self, job_id: str) -> bool:
        r = self.jobs.get(job_id)
        if not r or not r.task or r.task.done():
            return False
        r.task.cancel()
        return True

    async def subscribe(self, job_id: str):
        r = self.jobs.get(job_id)
        if not r:
            raise KeyError(job_id)
        q: asyncio.Queue = asyncio.Queue()
        r.subscribers.append(q)
        try:
            for event in r.job.events:
                yield event
            while True:
                event = await q.get()
                yield event
                if event.get("type") in {"error"} or (
                    event.get("type") == "status"
                    and event.get("status") in {
                        "succeeded", "failed", "test_failed", "canceled"
                    }
                ):
                    break
        finally:
            if q in r.subscribers:
                r.subscribers.remove(q)
