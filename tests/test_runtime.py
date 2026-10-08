from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from evalrepro.runtime import discover_git_root, git_state, package_version, runtime_versions


def test_package_and_runtime_versions() -> None:
    assert package_version("a-distribution-that-does-not-exist-xyz") is None
    versions = runtime_versions(("a-distribution-that-does-not-exist-xyz",))
    assert versions["python"]
    assert versions["platform"]
    assert versions["a-distribution-that-does-not-exist-xyz"] is None


def test_discover_git_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_exists = Path.exists

    def isolated_exists(self: Path) -> bool:
        if self.name == ".git" and not self.is_relative_to(tmp_path):
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", isolated_exists)

    parent_repo = tmp_path / "parent_repo"
    parent_repo_src = parent_repo / "src"
    parent_repo_src.mkdir(parents=True)
    (parent_repo / ".git").mkdir()
    parent_source = parent_repo_src / "module.py"
    parent_source.write_text("pass\n")

    assert discover_git_root(parent_source) == parent_repo

    inner_repo = parent_repo_src / "inner"
    inner_repo.mkdir()
    (inner_repo / ".git").mkdir()
    inner_source = inner_repo / "inner_module.py"
    inner_source.write_text("pass\n")
    assert discover_git_root(inner_source) == inner_repo

    worktree_repo = tmp_path / "worktree_repo"
    worktree_repo.mkdir()
    (worktree_repo / ".git").write_text("gitdir:/fake/path")
    worktree_source = worktree_repo / "module.py"
    worktree_source.write_text("pass\n")
    assert discover_git_root(worktree_source) == worktree_repo

    assert discover_git_root(tmp_path) is None


def test_git_state_none_and_real_repository(tmp_path: Path) -> None:
    assert git_state(None) == {"git_commit": None, "tracked_diff_digest": None}

    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("baseline\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repository, check=True)

    clean = git_state(repository)
    assert len(clean["git_commit"]) == 40
    assert len(clean["tracked_diff_digest"]) == 64

    tracked.write_text("changed\n")
    changed = git_state(repository)
    assert changed["git_commit"] == clean["git_commit"]
    assert changed["tracked_diff_digest"] != clean["tracked_diff_digest"]


def test_git_state_non_repository(tmp_path: Path) -> None:
    assert git_state(tmp_path) == {"git_commit": None, "tracked_diff_digest": None}
