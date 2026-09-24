import subprocess
from pathlib import Path

import pytest

from bridge.workspace import DirectoryWorkspace, GitWorktree, workspace_for


@pytest.mark.asyncio
async def test_worktree_does_not_edit_source(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    (repo / "a.txt").write_text("before")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    async with GitWorktree(str(repo)) as wt:
        assert wt.path is not None
        (wt.path / "a.txt").write_text("after")
        assert (repo / "a.txt").read_text() == "before"
        assert "a.txt" in wt.changed_files()


@pytest.mark.asyncio
async def test_non_git_workspace_is_supported(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    async with workspace_for(str(ws)) as work:
        assert isinstance(work, DirectoryWorkspace)
        (ws / "smoke.txt").write_text("ANTIGRAVITY_OK\n")
        assert work.changed_files() == ["smoke.txt"]
        assert "+++ b/smoke.txt" in work.diff()

@pytest.mark.asyncio
async def test_non_git_workspace_exposes_path_and_allows_file_change(tmp_path):
    from bridge.workspace import DirectoryWorkspace
    async with DirectoryWorkspace(str(tmp_path)) as ws:
        assert ws.path == tmp_path.resolve()
        (tmp_path / "smoke.txt").write_text("ANTIGRAVITY_OK\n", encoding="utf-8")
        assert "smoke.txt" in ws.changed_files()
        assert "ANTIGRAVITY_OK" in ws.diff()
