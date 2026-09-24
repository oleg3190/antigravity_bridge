from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("BRIDGE_HOST", "127.0.0.1")
    port: int = int(os.getenv("BRIDGE_PORT", "8090"))
    max_concurrent_jobs: int = int(os.getenv("BRIDGE_MAX_CONCURRENT_JOBS", "2"))
    job_timeout_seconds: int = int(os.getenv("BRIDGE_JOB_TIMEOUT_SECONDS", "900"))

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()
