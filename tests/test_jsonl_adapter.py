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
