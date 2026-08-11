from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from evalrepro.adapters.base import SnapshotSource
from evalrepro.manifest import build_manifest
from tools.harvey_lab_case_study import (
    DocumentStats,
    RevisionSnapshot,
    _compare_snapshots,
    _document_stats,
)


def _record(task_id: str, *, target: str = "baseline") -> dict[str, Any]:
    return {
        "id": task_id,
        "input": {"instructions": "Review."},
        "target": {"criteria": [target]},
        "choices": None,
        "metadata": {
            "source_documents": {
                "count": 2,
                "total_bytes": 10,
                "ordered_digest": "a" * 64,
            },
            "task_extra": {},
        },
    }


def _snapshot(revision: str, records: list[dict[str, Any]]) -> RevisionSnapshot:
    source = SnapshotSource(
        adapter="harvey-lab",
        identity={"benchmark": "Harvey LAB", "task_root": "tasks"},
        parameters={"adapter_contract_version": 1, "task_selector": "firm-knowledge"},
        records=records,
        declared_count=len(records),
    )
    manifest = build_manifest(source, include_id_preview=False)
    mapping_records: list[Mapping[str, Any]] = records
    return RevisionSnapshot(
        revision=revision,
        task_ids=tuple(record["id"] for record in records),
        documents=_document_stats(mapping_records),
        manifest=manifest,
    )


def test_document_stats_deduplicate_shared_corpora() -> None:
    records = [_record("001"), _record("002")]

    stats = _document_stats(records)

    assert stats == DocumentStats(
        corpus_count=1,
        document_count=2,
        total_bytes=10,
        inventory_digests=("a" * 64,),
    )


def test_compare_snapshots_counts_changed_task_contracts() -> None:
    baseline = _snapshot("1" * 40, [_record("001"), _record("002")])
    candidate = _snapshot(
        "2" * 40,
        [_record("001"), _record("002", target="candidate")],
    )

    comparison, payload = _compare_snapshots(baseline, candidate)

    assert comparison.verdict.value == "semantic_drift"
    assert payload["changed_task_count"] == 1
    assert payload["unchanged_task_count"] == 1
    assert baseline.manifest["samples"]["id_preview"] == {"first": [], "last": []}


def test_compare_snapshots_rejects_task_id_changes() -> None:
    baseline = _snapshot("1" * 40, [_record("001")])
    candidate = _snapshot("2" * 40, [_record("002")])

    with pytest.raises(RuntimeError, match="same ordered task IDs"):
        _compare_snapshots(baseline, candidate)
