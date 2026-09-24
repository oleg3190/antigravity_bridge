from __future__ import annotations

from fastapi import FastAPI

from .api import build_router
from .config import Settings
from .jobs import JobManager
from .logging import configure_logging

configure_logging()
settings = Settings.from_env()
manager = JobManager(
    max_concurrent=settings.max_concurrent_jobs,
    timeout=settings.job_timeout_seconds,
)

app = FastAPI(
    title="Antigravity Bridge",
    version="3.2.8",
)
app.include_router(build_router(manager))
