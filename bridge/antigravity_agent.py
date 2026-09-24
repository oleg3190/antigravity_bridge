from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, types
from google.antigravity.hooks import policy


FINISH_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "changed_files": {"type": "array", "items": {"type": "string"}},
        "tests_run": {"type": "array", "items": {"type": "string"}},
        "tests_passed": {"type": "boolean"},
        "needs_review": {"type": "boolean"},
    },
    "required": ["summary", "changed_files", "tests_run", "tests_passed", "needs_review"],
}


@dataclass
class AgentEvent:
    type: str
    data: dict[str, Any]


class AntigravityCodingAgent:
    """Thin adapter over the public Antigravity SDK.

    The SDK owns the agentic loop. This class only supplies task-specific
    configuration and converts SDK events into bridge-neutral events.
    """

    def __init__(self, workspace: str, timeout_seconds: float = 300):
        self.workspace = workspace
        self.timeout_seconds = timeout_seconds

    def _config(self) -> LocalAgentConfig:
        capabilities = CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=[
                types.BuiltinTools.LIST_DIR,
                types.BuiltinTools.SEARCH_DIR,
                types.BuiltinTools.FIND_FILE,
                types.BuiltinTools.VIEW_FILE,
                types.BuiltinTools.CREATE_FILE,
                types.BuiltinTools.EDIT_FILE,
                types.BuiltinTools.RUN_COMMAND,
                types.BuiltinTools.FINISH,
            ],
            enable_subagents=False,
            run_command_config=types.RunCommandConfig(
                timeout_seconds=self.timeout_seconds,
                enable_daemons=False,
                enable_sandbox=False,
            ),
            finish_tool_schema_json=json.dumps(FINISH_SCHEMA),
        )

        # Workspace scoping is a runtime policy. The exact SDK policy helper
        # is public and is intentionally kept in one place.
        policies = [
            # Workspace scoping is applied by the SDK for file tools.
            policy.workspace_only([self.workspace]),
            policy.deny("run_command", when=self._deny_dangerous_command),
        ]

        return LocalAgentConfig(
            system_instructions=(
                "You are a senior software engineer working inside an isolated coding workspace. "
                "Inspect relevant files before editing. Make only "
                "task-relevant changes. Never expose secrets. Do not modify "
                ".git, .env, credentials, SSH keys, CI secrets, or unrelated "
                "files. Use the available tools to implement and verify the task. "
                "Run focused tests when appropriate. Finish with a concise "
                "structured summary."
            ),
            capabilities=capabilities,
            workspaces=[self.workspace],
            policies=policies,
            response_schema=FINISH_SCHEMA,
        )

    @staticmethod
    def _deny_dangerous_command(args: dict[str, Any]) -> bool:
        command = str(
            args.get("CommandLine")
            or args.get("command")
            or args.get("command_line")
            or ""
        )
        lowered = command.lower()
        dangerous = (
            "rm -rf /" in lowered
            or "git reset --hard" in lowered
            or "git clean -fd" in lowered
            or "git clean -fdx" in lowered
            or "mkfs" in lowered
            or "dd if=" in lowered
            or "| bash" in lowered
            or "| sh" in lowered
        )
        return dangerous

    async def run(self, task: str) -> AsyncIterator[AgentEvent]:
        config = self._config()
        async with Agent(config) as agent:
            prompt = (
                f"Work only inside this workspace: {self.workspace}\n\n"
                f"Task:\n{task}\n\n"
                "First inspect relevant files. Then implement the task, run "
                "appropriate verification, and finish using the structured "
                "finish output."
            )
            response = await agent.chat(prompt)

            # Resolve the high-level response before inspecting secondary streams.
            try:
                await response.resolve()
            except AttributeError:
                pass

            try:
                text = await response.text()
            except Exception:
                text = ""
            if text:
                yield AgentEvent("text", {"text": text})

            try:
                async for call in response.tool_calls:
                    yield AgentEvent(
                        "tool_call",
                        {"name": str(call.name), "args": dict(call.args)},
                    )
            except Exception:
                pass

            try:
                structured = await response.structured_output()
            except Exception:
                structured = None

            if structured is not None:
                yield AgentEvent("structured", {"output": structured})

            try:
                usage = response.usage_metadata
            except Exception:
                usage = None
            if usage is not None:
                try:
                    usage_dict = usage.model_dump()
                except Exception:
                    usage_dict = {}
                yield AgentEvent("usage", usage_dict)
