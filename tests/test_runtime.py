from __future__ import annotations

import subprocess
from pathlib import Path

from evalrepro.runtime import discover_git_root, git_state, package_version, runtime_versions


def test_package_and_runtime_versions() -> None:
    assert package_version("a-distribution-that-does-not-exist-xyz") is None
    versions = runtime_versions(("a-distribution-that-does-not-exist-xyz",))
    assert versions["python"]
    assert versions["platform"]
    assert versions["a-distribution-that-does-not-exist-xyz"] is None


def test_discover_git_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "src" / "package"
    nested.mkdir(parents=True)
    (root / ".git").mkdir()
    source = nested / "module.py"
    source.write_text("pass\n")

    assert discover_git_root(source) == root
    assert discover_git_root(tmp_path / "outside") is None


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
