from __future__ import annotations

import asyncio
import logging
from typing import Any

from .antigravity_agent import AntigravityCodingAgent
from .models import JobResult
from .policy import validate_diff_paths
from .tests_runner import run_tests
from .workspace import workspace_for

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, job_timeout: int = 900):
        self.job_timeout = job_timeout

    async def execute(
        self,
        workspace: str,
        task: str,
        run_verification: bool = True,
        test_command: list[str] | None = None,
        event_sink=None,
    ) -> JobResult:
        async with workspace_for(workspace) as wt:
            if wt.path is None:
                raise RuntimeError("Workspace backend did not provide an execution path")

            agent = AntigravityCodingAgent(
                str(wt.path),
                timeout_seconds=min(self.job_timeout, 600),
            )

            structured: dict[str, Any] = {}
            usage: dict[str, Any] = {}
            text_parts: list[str] = []

            async for event in agent.run(task):
                if event.type == "text":
                    text_parts.append(event.data.get("text", ""))
                elif event.type == "structured":
                    raw = event.data.get("output")
                    if isinstance(raw, dict):
                        structured = raw
                elif event.type == "usage":
                    usage = event.data
                if event_sink:
                    await event_sink(event.type, event.data)

            changed = wt.changed_files()
            validate_diff_paths(changed)
            diff = wt.diff()

            tests_passed = None
            test_output = ""
            if run_verification and test_command:
                tests_passed, test_output = await run_tests(
                    wt.path,
                    test_command,
                    timeout=min(self.job_timeout, 600),
                )

            summary = structured.get("summary") or "".join(text_parts).strip()
            return JobResult(
                summary=summary,
                changed_files=changed,
                diff=diff,
                tests_passed=tests_passed if test_command else structured.get("tests_passed"),
                test_output=test_output,
                usage=usage,
                agent_metadata={
                    "structured_output": structured,
                },
            )
