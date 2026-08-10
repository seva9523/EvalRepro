from __future__ import annotations

import json
from pathlib import Path

import pytest

from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import ManifestError
from evalrepro.manifest import (
    build_manifest,
    read_manifest,
    validate_manifest,
    write_manifest,
)


def _source(records: list[dict[str, object]], *, name: str = "fixture") -> SnapshotSource:
    return SnapshotSource(
        adapter="fixture",
        identity={"name": name},
        parameters={"mode": "test"},
        records=records,
        declared_count=len(records),
        runtime={"python": "test"},
        provenance={"fixture": True},
    )


def test_manifest_contains_hashes_not_raw_sample_text() -> None:
    manifest = build_manifest(
        _source([{"id": "1", "input": "private prompt", "target": "private answer"}])
    )
    serialized = json.dumps(manifest)

    assert manifest["coverage"]["complete"] is True
    assert manifest["coverage"]["processed_count"] == 1
    assert "private prompt" not in serialized
    assert "private answer" not in serialized
    assert len(manifest["samples"]["ordered_hashes"][0]) == 64


def test_partial_manifest_records_coverage() -> None:
    manifest = build_manifest(
        _source([{"id": str(index), "input": index} for index in range(3)]),
        sample_limit=2,
    )

    assert manifest["coverage"] == {
        "declared_count": 3,
        "processed_count": 2,
        "complete": False,
        "sample_limit": 2,
    }


def test_empty_dataset_is_representable() -> None:
    manifest = build_manifest(_source([]))

    assert manifest["coverage"]["processed_count"] == 0
    assert manifest["coverage"]["complete"] is True
    assert manifest["samples"]["ordered_hashes"] == []


def test_id_preview_can_be_disabled_without_changing_sample_digests() -> None:
    source = _source(
        [{"id": f"customer-{index}", "input": f"prompt-{index}"} for index in range(12)]
    )

    with_preview = build_manifest(source)
    without_preview = build_manifest(source, include_id_preview=False)

    assert without_preview["samples"]["id_preview"] == {"first": [], "last": []}
    assert without_preview["samples"]["ordered_hashes"] == with_preview["samples"]["ordered_hashes"]
    assert without_preview["samples"]["ordered_digest"] == with_preview["samples"]["ordered_digest"]
    assert (
        without_preview["samples"]["unordered_digest"]
        == with_preview["samples"]["unordered_digest"]
    )
    assert without_preview["samples"]["field_digests"] == with_preview["samples"]["field_digests"]


def test_write_and_read_manifest_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    manifest = build_manifest(_source([{"id": "1", "input": "hello"}]))

    write_manifest(path, manifest)

    assert read_manifest(path) == manifest


def test_validation_rejects_scope_tampering() -> None:
    manifest = build_manifest(_source([{"id": "1", "input": "hello"}]))
    manifest["scope"]["identity"]["name"] = "changed"

    with pytest.raises(ManifestError, match="scope_digest"):
        validate_manifest(manifest)


def test_limit_must_be_positive() -> None:
    with pytest.raises(ManifestError, match="positive"):
        build_manifest(_source([]), sample_limit=0)
