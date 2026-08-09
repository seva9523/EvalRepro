from __future__ import annotations

import json
from pathlib import Path

import pytest

from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import ManifestError
from evalrepro.manifest import build_manifest, read_manifest, validate_manifest


def _source(records: object, declared_count: int | None = None) -> SnapshotSource:
    return SnapshotSource(
        adapter="fixture",
        identity={"name": "extra"},
        parameters={},
        records=records,  # type: ignore[arg-type]
        declared_count=declared_count,
    )


def test_unknown_length_iterables_can_be_complete_or_partial() -> None:
    complete = build_manifest(_source(iter([{"input": 1}, {"input": 2}])))
    partial = build_manifest(_source(iter([{"input": 1}, {"input": 2}])), sample_limit=1)

    assert complete["coverage"]["complete"] is True
    assert partial["coverage"]["complete"] is False


def test_non_mapping_sample_and_large_id_preview() -> None:
    records = [{"id": str(index), "input": index} for index in range(12)]
    manifest = build_manifest(_source(records, declared_count=12))
    scalar = build_manifest(_source(["sample"], declared_count=1))

    assert manifest["samples"]["id_preview"] == {
        "first": ["0", "1", "2", "3", "4"],
        "last": ["7", "8", "9", "10", "11"],
    }
    assert scalar["samples"]["top_level_type_summary"] == {"__sample__": {"string": 1}}


def test_type_summary_covers_json_types() -> None:
    manifest = build_manifest(
        _source(
            [
                {
                    "id": "1",
                    "null": None,
                    "bool": True,
                    "int": 1,
                    "float": 1.5,
                    "string": "x",
                    "list": [],
                    "object": {},
                }
            ],
            declared_count=1,
        )
    )
    summary = manifest["samples"]["top_level_type_summary"]

    assert summary["null"] == {"null": 1}
    assert summary["bool"] == {"bool": 1}
    assert summary["int"] == {"int": 1}
    assert summary["float"] == {"float": 1}
    assert summary["string"] == {"string": 1}
    assert summary["list"] == {"list": 1}
    assert summary["object"] == {"object": 1}


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: "not-an-object", "JSON object"),
        (lambda value: {**value, "manifest_schema_version": 999}, "unsupported manifest schema"),
        (
            lambda value: {key: item for key, item in value.items() if key != "scope"},
            "missing object",
        ),
        (
            lambda value: {
                **value,
                "scope": {
                    key: item
                    for key, item in value["scope"].items()
                    if key != "adapter"
                },
            },
            "missing scope fields",
        ),
        (
            lambda value: {**value, "coverage": {**value["coverage"], "complete": "yes"}},
            "must be boolean",
        ),
        (
            lambda value: {**value, "coverage": {**value["coverage"], "processed_count": -1}},
            "non-negative integer",
        ),
        (
            lambda value: {**value, "samples": {**value["samples"], "ordered_hashes": [1]}},
            "list of strings",
        ),
        (
            lambda value: {**value, "coverage": {**value["coverage"], "processed_count": 99}},
            "does not match",
        ),
    ],
)
def test_validation_error_paths(mutator: object, message: str) -> None:
    manifest = build_manifest(_source([{"input": "x"}], declared_count=1))
    changed = mutator(manifest)  # type: ignore[operator]

    with pytest.raises(ManifestError, match=message):
        validate_manifest(changed)


def test_read_manifest_error_paths(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="Cannot read"):
        read_manifest(tmp_path / "missing.json")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(ManifestError, match="Invalid JSON"):
        read_manifest(invalid)

    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps([]))
    with pytest.raises(ManifestError, match="JSON object"):
        read_manifest(wrong)
