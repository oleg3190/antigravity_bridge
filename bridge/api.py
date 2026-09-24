from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .jobs import JobManager
from .models import CreateJobRequest

router = APIRouter()


def build_router(manager: JobManager) -> APIRouter:
    @router.get("/health")
    async def health():
        return {"ok": True, "version": "3.2.8"}

    @router.post("/v1/jobs")
    async def create_job(req: CreateJobRequest):
        return await manager.create(req)

    @router.get("/v1/jobs/{job_id}")
    async def get_job(job_id: str):
        job = manager.get(job_id)
        if not job:
            raise HTTPException(404, "job not found")
        return job

    @router.post("/v1/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str):
        if not await manager.cancel(job_id):
            raise HTTPException(409, "job is not running")
        return {"ok": True}

    @router.get("/v1/jobs/{job_id}/events")
    async def events(job_id: str):
        if not manager.get(job_id):
            raise HTTPException(404, "job not found")

        async def stream():
            async for event in manager.subscribe(job_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
