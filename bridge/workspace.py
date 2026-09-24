from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from difflib import unified_diff


class WorkspaceError(RuntimeError):
    pass


def _run_git(args: list[str], cwd: Path) -> str:
    p = subprocess.run(
        ["git", *args], cwd=cwd, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if p.returncode:
        raise WorkspaceError(p.stderr.strip() or "git command failed")
    return p.stdout


class GitWorktree:
    """Disposable Git worktree. Source repository is never edited directly."""
    is_git = True

    def __init__(self, repo: str):
        self.repo = Path(repo).expanduser().resolve()
        self.path: Path | None = None

    async def __aenter__(self) -> "GitWorktree":
        if not self.repo.exists() or not self.repo.is_dir():
            raise WorkspaceError(f"Workspace is not a directory: {self.repo}")
        try:
            base = _run_git(["rev-parse", "--show-toplevel"], self.repo).strip()
        except WorkspaceError as exc:
            raise WorkspaceError(f"Not a Git repository: {self.repo}") from exc
        self.repo = Path(base).resolve()
        self.path = Path(tempfile.mkdtemp(prefix="ag-worktree-"))
        self.path.rmdir()
        _run_git(["worktree", "add", "--detach", str(self.path), "HEAD"], self.repo)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.path:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(self.path)],
                cwd=self.repo, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
            self.path = None

    def diff(self) -> str:
        if not self.path:
            raise WorkspaceError("Worktree is not active")
        return _run_git(["diff", "--no-ext-diff", "--binary", "HEAD", "--"], self.path)

    def changed_files(self) -> list[str]:
        if not self.path:
            raise WorkspaceError("Worktree is not active")
        out = _run_git(["status", "--porcelain", "--untracked-files=all"], self.path)
        files = []
        for line in out.splitlines():
            if len(line) >= 4:
                files.append(line[3:])
        return files


class DirectoryWorkspace:
    """Non-Git workspace with a before/after filesystem snapshot."""
    is_git = False

    def __init__(self, workspace: str):
        self.root = Path(workspace).expanduser().resolve()
        self.path = self.root
        self._before: dict[str, tuple[str, int]] = {}
        self._before_text: dict[str, str] = {}

    async def __aenter__(self) -> "DirectoryWorkspace":
        if not self.root.exists():
            raise WorkspaceError(f"Workspace does not exist: {self.root}")
        if not self.root.is_dir():
            raise WorkspaceError(f"Workspace is not a directory: {self.root}")
        self._snapshot()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def _snapshot(self) -> None:
        self._before.clear()
        self._before_text.clear()
        for p in self.root.rglob("*"):
            if not p.is_file() or ".git" in p.parts:
                continue
            rel = p.relative_to(self.root).as_posix()
            data = p.read_bytes()
            self._before[rel] = (hashlib.sha256(data).hexdigest(), p.stat().st_mode & 0o777)
            try:
                self._before_text[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                pass

    def changed_files(self) -> list[str]:
        after: dict[str, tuple[str, int]] = {}
        for p in self.root.rglob("*"):
            if not p.is_file() or ".git" in p.parts:
                continue
            rel = p.relative_to(self.root).as_posix()
            data = p.read_bytes()
            after[rel] = (hashlib.sha256(data).hexdigest(), p.stat().st_mode & 0o777)
        return sorted((set(self._before) ^ set(after)) | {
            k for k in set(self._before) & set(after) if self._before[k] != after[k]
        })

    def diff(self) -> str:
        chunks: list[str] = []
        for rel in self.changed_files():
            old = self._before_text.get(rel, "")
            p = self.root / rel
            if p.exists():
                try:
                    new = p.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    chunks.append(f"Binary files differ: {rel}\n")
                    continue
            else:
                new = ""
            old_lines = old.splitlines(keepends=True)
            new_lines = new.splitlines(keepends=True)
            chunks.extend(unified_diff(old_lines, new_lines, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        return "".join(chunks)



def workspace_for(path: str):
    """Return Git isolation when possible, otherwise safe non-Git directory mode."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise WorkspaceError(f"Workspace is not a directory: {p}")
    try:
        _run_git(["rev-parse", "--show-toplevel"], p)
        return GitWorktree(str(p))
    except WorkspaceError:
        return DirectoryWorkspace(str(p))
