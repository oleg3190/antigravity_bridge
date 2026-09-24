from __future__ import annotations

import asyncio
from pathlib import Path


async def run_tests(
    workspace: Path,
    command: list[str],
    timeout: float = 300,
) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=workspace,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, "TEST TIMEOUT"
    output = stdout.decode("utf-8", errors="replace")
    return proc.returncode == 0, output
