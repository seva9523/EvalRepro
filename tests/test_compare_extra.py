from __future__ import annotations

from evalrepro.adapters.base import SnapshotSource
from evalrepro.compare import Verdict, compare_manifest_data
from evalrepro.manifest import build_manifest


def _source(records: list[dict[str, object]], fields: tuple[str, ...]) -> SnapshotSource:
    return SnapshotSource(
        adapter="fixture",
        identity={"name": "x"},
        parameters={},
        records=records,
        declared_count=len(records),
        fields=fields,
    )


def test_different_field_contract_is_scope_mismatch() -> None:
    records = [{"input": "a", "target": "b"}]
    left = build_manifest(_source(records, ("input",)))
    right = build_manifest(_source(records, ("input", "target")))

    assert compare_manifest_data(left, right).verdict is Verdict.SCOPE_MISMATCH


def test_complete_unknown_declared_count_can_match_known_count() -> None:
    left_source = _source([{"input": "a"}], ("input",))
    left_source.declared_count = None
    right_source = _source([{"input": "a"}], ("input",))

    result = compare_manifest_data(
        build_manifest(left_source), build_manifest(right_source)
    )
    assert result.reproducible
