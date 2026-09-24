from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TEST_FAILED = "test_failed"
    CANCELED = "canceled"


class CreateJobRequest(BaseModel):
    task: str = Field(min_length=1, max_length=100_000)
    workspace: str = Field(min_length=1)
    run_tests: bool = True
    test_command: list[str] | None = None
    stream: bool = False


class JobResult(BaseModel):
    summary: str = ""
    changed_files: list[str] = Field(default_factory=list)
    diff: str = ""
    tests_passed: bool | None = None
    test_output: str = ""
    usage: dict[str, Any] = Field(default_factory=dict)
    agent_metadata: dict[str, Any] = Field(default_factory=dict)


class Job(BaseModel):
    id: str
    status: JobStatus
    workspace: str
    task: str
    error: str | None = None
    result: JobResult | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
