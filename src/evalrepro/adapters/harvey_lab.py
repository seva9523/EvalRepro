"""Harvey LAB task-contract adapter."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import AdapterError
from evalrepro.hashing import digest
from evalrepro.runtime import git_state, runtime_versions

ADAPTER_CONTRACT_VERSION = 1

_KNOWN_TASK_FIELDS = {
    "title",
    "instructions",
    "criteria",
    "deliverables",
    "work_type",
    "tags",
    "docs_dir",
}
_KNOWN_CRITERION_FIELDS = {
    "id",
    "title",
    "match_criteria",
    "deliverables",
    "sources",
}

DocumentInventory = dict[str, int | str]


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AdapterError(f"Cannot read Harvey LAB task config {path}: {exc}") from exc

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"Invalid JSON in Harvey LAB task config {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise AdapterError(f"Harvey LAB task config {path} must contain a JSON object.")
    return value


def _required_text(value: Any, *, label: str, source: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(f"{source}: {label} must be a non-empty string.")
    return value


def _string_list(value: Any, *, label: str, source: Path) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AdapterError(f"{source}: {label} must be a list of strings.")
    return list(value)


def _deliverables(value: Any, *, source: Path) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise AdapterError(f"{source}: deliverables must be an object mapping strings to strings.")
    return dict(cast(Mapping[str, str], value))


def _file_digest(path: Path) -> tuple[int, str]:
    try:
        size = path.stat().st_size
        result = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                result.update(chunk)
    except OSError as exc:
        raise AdapterError(f"Cannot read Harvey LAB source document {path}: {exc}") from exc
    return size, result.hexdigest()


def _relative_to_root(root: Path, path: Path, *, label: str) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise AdapterError(f"Harvey LAB {label} escapes repository root: {path}") from exc


def _reject_symlink_components(root: Path, path: Path, *, label: str) -> Path:
    lexical_path = Path(os.path.abspath(path))
    try:
        relative = lexical_path.relative_to(root)
    except ValueError as exc:
        raise AdapterError(f"Harvey LAB {label} escapes repository root: {path}") from exc

    current = root
    for part in relative.parts:
        current /= part
        try:
            if current.is_symlink():
                raise AdapterError(f"Harvey LAB {label} must not use symbolic links: {current}")
        except OSError as exc:
            raise AdapterError(f"Cannot inspect Harvey LAB {label} path {current}: {exc}") from exc
    return lexical_path


def _effective_instructions(config: dict[str, Any], task_dir: Path, config_path: Path) -> str:
    inline = config.get("instructions")
    if inline is not None and not isinstance(inline, str):
        raise AdapterError(f"{config_path}: instructions must be a string when present.")
    if isinstance(inline, str) and inline.strip():
        return inline

    fallback = task_dir / "instructions.md"
    if fallback.is_symlink():
        raise AdapterError(f"Harvey LAB instructions must not be a symbolic link: {fallback}")
    try:
        instructions = fallback.read_text(encoding="utf-8")
    except OSError as exc:
        raise AdapterError(
            f"No readable instructions found in {config_path} or {fallback}: {exc}"
        ) from exc
    if not instructions.strip():
        raise AdapterError(f"{fallback}: instructions must be non-empty.")
    return instructions


def _criteria(config: dict[str, Any], config_path: Path) -> list[dict[str, Any]]:
    value = config.get("criteria")
    if not isinstance(value, list) or not value:
        raise AdapterError(f"{config_path}: criteria must be a non-empty list.")

    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise AdapterError(f"{config_path}: criterion {index} must be an object.")
        result.append(
            {
                "id": _required_text(
                    item.get("id"), label=f"criterion {index} id", source=config_path
                ),
                "title": _required_text(
                    item.get("title"), label=f"criterion {index} title", source=config_path
                ),
                "match_criteria": _required_text(
                    item.get("match_criteria"),
                    label=f"criterion {index} match_criteria",
                    source=config_path,
                ),
                "deliverables": _string_list(
                    item.get("deliverables"),
                    label=f"criterion {index} deliverables",
                    source=config_path,
                ),
                "sources": _string_list(
                    item.get("sources"),
                    label=f"criterion {index} sources",
                    source=config_path,
                ),
                "extra": {
                    key: extra_value
                    for key, extra_value in item.items()
                    if key not in _KNOWN_CRITERION_FIELDS
                },
            }
        )
    return result


def _document_inventory(
    root: Path,
    docs_dir: Path,
    cache: dict[Path, DocumentInventory],
) -> DocumentInventory:
    cached = cache.get(docs_dir)
    if cached is not None:
        return cached

    try:
        paths = sorted(
            docs_dir.rglob("*"),
            key=lambda item: item.relative_to(docs_dir).as_posix(),
        )
    except OSError as exc:
        raise AdapterError(
            f"Cannot inventory Harvey LAB documents directory {docs_dir}: {exc}"
        ) from exc

    entries: list[dict[str, Any]] = []
    total_bytes = 0
    for path in paths:
        _reject_symlink_components(root, path, label="source document")
        try:
            is_file = path.is_file()
        except OSError as exc:
            raise AdapterError(f"Cannot inspect Harvey LAB source path {path}: {exc}") from exc
        if not is_file:
            continue
        size, content_digest = _file_digest(path)
        total_bytes += size
        entries.append(
            {
                "path": _relative_to_root(root, path.resolve(), label="source document"),
                "size_bytes": size,
                "content_sha256": content_digest,
            }
        )

    inventory: DocumentInventory = {
        "count": len(entries),
        "total_bytes": total_bytes,
        "ordered_digest": digest(entries),
    }
    cache[docs_dir] = inventory
    return inventory


def _task_record(
    root: Path,
    tasks_root: Path,
    config_path: Path,
    inventory_cache: dict[Path, DocumentInventory],
) -> dict[str, Any]:
    task_dir = config_path.parent
    task_id = task_dir.relative_to(tasks_root).as_posix()
    if len(Path(task_id).parts) < 2:
        raise AdapterError(f"Harvey LAB task ID must have at least two path segments: {task_id}")

    config = _read_json_object(config_path)
    raw_docs_dir = config.get("docs_dir") or "documents"
    if not isinstance(raw_docs_dir, str):
        raise AdapterError(f"{config_path}: docs_dir must be a string when present.")
    if Path(raw_docs_dir).is_absolute() or PureWindowsPath(raw_docs_dir).is_absolute():
        raise AdapterError(f"{config_path}: docs_dir must be relative to the task directory.")

    docs_path = task_dir / raw_docs_dir
    _reject_symlink_components(root, docs_path, label="documents directory")
    try:
        docs_dir = docs_path.resolve(strict=True)
    except OSError as exc:
        raise AdapterError(f"Harvey LAB documents directory not found: {docs_path}") from exc
    if not docs_dir.is_dir():
        raise AdapterError(f"Harvey LAB documents path is not a directory: {docs_dir}")

    docs_dir_semantic = _relative_to_root(root, docs_dir, label="documents directory")
    work_type = config.get("work_type")
    if work_type is not None and not isinstance(work_type, str):
        raise AdapterError(f"{config_path}: work_type must be a string when present.")

    return {
        "id": task_id,
        "input": {
            "title": _required_text(config.get("title"), label="title", source=config_path),
            "instructions": _effective_instructions(config, task_dir, config_path),
            "work_type": work_type,
            "tags": _string_list(config.get("tags"), label="tags", source=config_path),
            "docs_dir": docs_dir_semantic,
            "deliverables": _deliverables(config.get("deliverables"), source=config_path),
        },
        "target": {"criteria": _criteria(config, config_path)},
        "choices": None,
        "metadata": {
            "source_documents": _document_inventory(root, docs_dir, inventory_cache),
            "task_extra": {
                key: extra_value
                for key, extra_value in config.items()
                if key not in _KNOWN_TASK_FIELDS
            },
        },
    }


def _canonical_selector(selector: str) -> str:
    value = selector.strip().replace("\\", "/").strip("/")
    parts = [part for part in value.split("/") if part not in {"", "."}]
    if not parts:
        raise AdapterError("Harvey LAB task selector must not be empty.")
    if any(part == ".." for part in parts):
        raise AdapterError("Harvey LAB task selector must not contain '..' segments.")
    return "/".join(parts)


def _discover(root: Path, selector: str) -> tuple[Path, list[Path]]:
    tasks_root = root / "tasks"
    if tasks_root.is_symlink():
        raise AdapterError(f"Harvey LAB tasks directory must not be a symbolic link: {tasks_root}")
    if not tasks_root.is_dir():
        raise AdapterError(f"Harvey LAB tasks directory not found: {tasks_root}")

    try:
        discovered = list(tasks_root.rglob("task.json"))
    except OSError as exc:
        raise AdapterError(f"Cannot discover Harvey LAB tasks under {tasks_root}: {exc}") from exc

    configs: list[Path] = []
    for path in discovered:
        _reject_symlink_components(root, path, label="task config")
        try:
            is_file = path.is_file()
        except OSError as exc:
            raise AdapterError(f"Cannot inspect Harvey LAB task config {path}: {exc}") from exc
        if is_file:
            configs.append(path)
    configs.sort(key=lambda path: path.parent.relative_to(tasks_root).as_posix())

    selected: list[Path] = []
    seen: set[str] = set()
    for path in configs:
        task_id = path.parent.relative_to(tasks_root).as_posix()
        if task_id in seen:
            raise AdapterError(f"Duplicate Harvey LAB task ID: {task_id}")
        seen.add(task_id)
        if selector == "all" or task_id == selector or task_id.startswith(f"{selector}/"):
            selected.append(path)

    if not selected:
        raise AdapterError(f"No Harvey LAB tasks matched selector {selector!r} under {tasks_root}.")
    return tasks_root, selected


def _run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _sanitise_remote(value: str | None) -> str | None:
    if not value:
        return value
    if "://" not in value:
        prefix, separator, remainder = value.partition("@")
        if separator and ":" in remainder and prefix:
            return remainder
        return value

    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if not host:
        return None
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def _project_version(root: Path) -> str | None:
    path = root / "pyproject.toml"
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return None
    project = value.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    return version if isinstance(version, str) else None


def _provenance(root: Path, selected_count: int) -> dict[str, Any]:
    git_root = root if (root / ".git").exists() else None
    status = (
        _run_git(root, "status", "--porcelain", "--untracked-files=normal") if git_root else None
    )
    tags = _run_git(root, "tag", "--points-at", "HEAD") if git_root else None
    return {
        "source": "harvey-lab-checkout",
        "harvey_lab_version": _project_version(root),
        "repository_origin": _sanitise_remote(
            _run_git(root, "config", "--get", "remote.origin.url") if git_root else None
        ),
        "git_tags": sorted(tag for tag in (tags or "").splitlines() if tag),
        "git_dirty": bool(status),
        "git_status_digest": (
            hashlib.sha256((status or "").encode("utf-8")).hexdigest()
            if status is not None
            else None
        ),
        "task_root": "tasks",
        "selected_task_count": selected_count,
        **git_state(git_root),
    }


def harvey_lab_source(path: Path, *, task: str = "all") -> SnapshotSource:
    """Load Harvey LAB task contracts without importing or executing its harness."""
    try:
        root = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise AdapterError(f"Harvey LAB repository path does not exist: {path}") from exc
    if not root.is_dir():
        raise AdapterError(f"Harvey LAB repository path is not a directory: {root}")

    selector = _canonical_selector(task)
    tasks_root, configs = _discover(root, selector)
    inventory_cache: dict[Path, DocumentInventory] = {}
    records = [
        _task_record(root, tasks_root, config_path, inventory_cache) for config_path in configs
    ]
    return SnapshotSource(
        adapter="harvey-lab",
        identity={"benchmark": "Harvey LAB", "task_root": "tasks"},
        parameters={
            "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
            "task_selector": selector,
            "document_content": "sha256",
            "document_paths_semantic": True,
            "unknown_task_fields": "included",
        },
        records=records,
        declared_count=len(records),
        runtime=runtime_versions(),
        provenance=_provenance(root, len(records)),
    )
