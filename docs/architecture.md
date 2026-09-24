# v3.2 Architecture

## Principle

Antigravity SDK owns the agentic loop. The bridge owns isolation, jobs, API compatibility, auditability and independent verification.

## Data flow

Qwen/client -> FastAPI -> JobManager -> GitWorktree -> Antigravity Agent -> tools -> worktree -> Git diff -> tests -> result.

## Why Git worktrees

The source repository is never handed directly to the agent. The agent works in a detached worktree. This avoids the destructive rollback pattern of resetting the user's live checkout.

## Why SDK policies + bridge policy

SDK `CapabilitiesConfig` removes irrelevant tools from model context. Runtime policies enforce contextual restrictions. Bridge-side validation remains an independent final boundary.

## Why Git diff is authoritative

The final code change is obtained from Git, not from model-generated markdown. Model summaries are advisory metadata.

## Why no custom Antigravity HTTP adapter

The official SDK already manages runtime lifecycle, tool wiring, policies, state and streaming. Duplicating those responsibilities in an HTTP client makes the integration brittle and loses SDK functionality.
