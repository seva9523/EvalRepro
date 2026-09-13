from __future__ import annotations

from pathlib import Path

import pytest

from evalrepro.adapters.jsonl import jsonl_source
from evalrepro.errors import AdapterError
from evalrepro.manifest import build_manifest


def test_jsonl_adapter_ignores_blank_lines_and_tracks_source(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text('{"id":"1","input":"a"}\n\n{"id":"2","input":"b"}\n')

    source = jsonl_source(path, name="demo")
    manifest = build_manifest(source)

    assert manifest["scope"]["identity"]["name"] == "demo"
    assert manifest["coverage"]["processed_count"] == 2
    assert manifest["provenance"]["source_line_numbers"] == [1, 3]
    assert len(manifest["provenance"]["file_sha256"]) == 64


def test_jsonl_adapter_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text('{"ok": true}\nnot-json\n')

    with pytest.raises(AdapterError, match=r"broken\.jsonl:2"):
        jsonl_source(path)


def test_jsonl_adapter_reports_missing_source(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"

    with pytest.raises(
        AdapterError,
        match=r"Cannot read JSONL source .*missing\.jsonl",
    ):
        jsonl_source(path)


def test_jsonl_adapter_reports_non_utf8_source(tmp_path: Path) -> None:
    path = tmp_path / "invalid_utf8.jsonl"
    path.write_bytes(b'{"id": "1", "input": "\xff\xfe"}\n')

    with pytest.raises(
        AdapterError,
        match=r"Cannot decode JSONL source .*invalid_utf8\.jsonl as UTF-8",
    ):
        jsonl_source(path)


def test_jsonl_adapter_empty_and_whitespace_only_sources(tmp_path: Path) -> None:
    for filename, content in [("empty.jsonl", ""), ("whitespace.jsonl", "\n  \n\t\n")]:
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")

        source = jsonl_source(path, name="empty-check")
        manifest = build_manifest(source)

        assert manifest["scope"]["identity"]["name"] == "empty-check"
        assert manifest["coverage"]["declared_count"] == 0
        assert manifest["coverage"]["processed_count"] == 0
        assert manifest["coverage"]["complete"] is True
        assert manifest["coverage"]["sample_limit"] is None
        assert manifest["provenance"]["source_line_numbers"] == []
        assert manifest["samples"]["ordered_hashes"] == []
        assert manifest["samples"]["top_level_type_summary"] == {}


def test_jsonl_adapter_scalar_records_and_stable_ordered_hashes(tmp_path: Path) -> None:
    path = tmp_path / "scalars.jsonl"
    # Blank lines before, between, and after scalar records (lines 2, 4, 5, 7)
    path.write_text(
        "\n\"sample string\"\n\n42\ntrue\n\n3.14159\n\n",
        encoding="utf-8",
    )

    source1 = jsonl_source(path, name="scalars-check")
    manifest1 = build_manifest(source1)

    assert manifest1["coverage"]["declared_count"] == 4
    assert manifest1["coverage"]["processed_count"] == 4
    assert manifest1["coverage"]["complete"] is True
    assert manifest1["provenance"]["source_line_numbers"] == [2, 4, 5, 7]
    assert manifest1["samples"]["top_level_type_summary"] == {
        "__sample__": {"bool": 1, "float": 1, "int": 1, "string": 1}
    }
    assert len(manifest1["samples"]["ordered_hashes"]) == 4

    # Verify stable ordered hashes across rebuilds from the same source
    source2 = jsonl_source(path, name="scalars-check")
    manifest2 = build_manifest(source2)
    assert manifest1["samples"]["ordered_hashes"] == manifest2["samples"]["ordered_hashes"]
    assert manifest1["samples"]["ordered_digest"] == manifest2["samples"]["ordered_digest"]
