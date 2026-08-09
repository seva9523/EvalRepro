"""Generic JSON Lines adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import AdapterError
from evalrepro.runtime import runtime_versions


def _file_digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def jsonl_source(
    path: Path,
    *,
    name: str = "jsonl-evaluation",
    fields: tuple[str, ...] = ("input", "target", "choices", "metadata"),
    id_field: str | None = "id",
) -> SnapshotSource:
    """Load one JSON value per non-empty line."""
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AdapterError(f"Cannot read JSONL source {path}: {exc}") from exc

    records: list[Any] = []
    source_line_numbers: list[int] = []
    for line_number, raw_line in enumerate(raw_lines, start=1):
        if not raw_line.strip():
            continue
        try:
            records.append(json.loads(raw_line))
        except json.JSONDecodeError as exc:
            raise AdapterError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
        source_line_numbers.append(line_number)

    return SnapshotSource(
        adapter="jsonl",
        identity={"name": name},
        parameters={"encoding": "utf-8", "blank_lines_ignored": True},
        records=records,
        declared_count=len(records),
        fields=fields,
        id_field=id_field,
        runtime=runtime_versions(),
        provenance={
            "file_name": path.name,
            "file_sha256": _file_digest(path),
            "source_line_numbers": source_line_numbers,
        },
    )
