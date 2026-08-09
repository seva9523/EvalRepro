"""Runtime and source-provenance helpers."""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import subprocess
from pathlib import Path
from typing import Any


def package_version(distribution_name: str) -> str | None:
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def runtime_versions(extra_distributions: tuple[str, ...] = ()) -> dict[str, str | None]:
    values: dict[str, str | None] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for distribution in extra_distributions:
        values[distribution] = package_version(distribution)
    return values


def discover_git_root(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def git_state(root: Path | None) -> dict[str, Any]:
    if root is None:
        return {"git_commit": None, "tracked_diff_digest": None}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        tracked_diff = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--binary", "HEAD", "--"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return {"git_commit": None, "tracked_diff_digest": None}
    if commit.returncode != 0 or tracked_diff.returncode != 0:
        return {"git_commit": None, "tracked_diff_digest": None}
    return {
        "git_commit": commit.stdout.strip(),
        "tracked_diff_digest": hashlib.sha256(tracked_diff.stdout.encode("utf-8")).hexdigest(),
    }
