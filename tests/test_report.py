from __future__ import annotations

from evalrepro.adapters.base import SnapshotSource
from evalrepro.compare import compare_manifest_data
from evalrepro.manifest import build_manifest
from evalrepro.report import render_markdown, render_text


def test_reports_include_verdict_and_fields() -> None:
    source = SnapshotSource(
        adapter="fixture",
        identity={"name": "x"},
        parameters={},
        records=[{"input": "a", "target": "b"}],
        declared_count=1,
    )
    comparison = compare_manifest_data(build_manifest(source), build_manifest(source))

    assert "reproducible" in render_text(comparison)
    assert "Semantic fields" in render_markdown(comparison)
    assert "`target`" in render_markdown(comparison)
