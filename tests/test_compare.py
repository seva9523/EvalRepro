from __future__ import annotations

from evalrepro.adapters.base import SnapshotSource
from evalrepro.compare import Verdict, compare_manifest_data
from evalrepro.manifest import build_manifest


def _manifest(
    records: list[dict[str, object]],
    *,
    name: str = "fixture",
    declared_count: int | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    source = SnapshotSource(
        adapter="fixture",
        identity={"name": name},
        parameters={},
        records=records,
        declared_count=len(records) if declared_count is None else declared_count,
    )
    return build_manifest(source, sample_limit=limit)


def test_identical_manifests_are_reproducible() -> None:
    records = [
        {"id": "1", "input": "a", "target": "x"},
        {"id": "2", "input": "b", "target": "y"},
    ]

    result = compare_manifest_data(_manifest(records), _manifest(records))

    assert result.verdict is Verdict.REPRODUCIBLE
    assert result.reproducible is True
    assert result.first_ordered_mismatch is None


def test_reordering_is_classified_separately() -> None:
    records = [
        {"id": "1", "input": "a", "target": "x"},
        {"id": "2", "input": "b", "target": "y"},
    ]

    result = compare_manifest_data(_manifest(records), _manifest(list(reversed(records))))

    assert result.verdict is Verdict.ORDER_DRIFT
    assert result.unordered_samples_match is True
    assert result.ordered_samples_match is False
    assert result.first_ordered_mismatch == 0


def test_target_change_is_semantic_drift() -> None:
    baseline = [{"id": "1", "input": "a", "target": "x"}]
    candidate = [{"id": "1", "input": "a", "target": "changed"}]

    result = compare_manifest_data(_manifest(baseline), _manifest(candidate))

    assert result.verdict is Verdict.SEMANTIC_DRIFT
    assert result.field_matches["target"]["unordered"] is False
    assert result.added_sample_hashes == 1
    assert result.removed_sample_hashes == 1


def test_scope_mismatch_precedes_content_comparison() -> None:
    records = [{"id": "1", "input": "a"}]

    result = compare_manifest_data(
        _manifest(records, name="left"), _manifest(records, name="right")
    )

    assert result.verdict is Verdict.SCOPE_MISMATCH
    assert result.scope_match is False


def test_partial_and_complete_runs_do_not_false_match() -> None:
    records = [{"id": str(index), "input": index} for index in range(3)]

    result = compare_manifest_data(_manifest(records, limit=2), _manifest(records[:2]))

    assert result.verdict is Verdict.COVERAGE_MISMATCH
    assert result.coverage_match is False
