"""Compare two EvalRepro manifests and classify drift."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from evalrepro.manifest import read_manifest


class Verdict(str, Enum):
    REPRODUCIBLE = "reproducible"
    ORDER_DRIFT = "order_drift"
    SEMANTIC_DRIFT = "semantic_drift"
    COVERAGE_MISMATCH = "coverage_mismatch"
    SCOPE_MISMATCH = "scope_mismatch"


@dataclass(frozen=True, slots=True)
class Comparison:
    verdict: Verdict
    reproducible: bool
    scope_match: bool
    coverage_match: bool
    ordered_samples_match: bool
    unordered_samples_match: bool
    top_level_types_match: bool
    field_matches: dict[str, dict[str, bool]]
    added_sample_hashes: int
    removed_sample_hashes: int
    first_ordered_mismatch: int | None
    baseline_runtime: dict[str, Any]
    candidate_runtime: dict[str, Any]
    baseline_coverage: dict[str, Any]
    candidate_coverage: dict[str, Any]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["verdict"] = self.verdict.value
        result["notes"] = list(self.notes)
        return result


def _first_mismatch(left: list[str], right: list[str]) -> int | None:
    for index, (left_hash, right_hash) in enumerate(zip(left, right)):
        if left_hash != right_hash:
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return None


def _coverage_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["complete"] != right["complete"]:
        return False
    if left["processed_count"] != right["processed_count"]:
        return False
    if left["complete"]:
        declared = (left["declared_count"], right["declared_count"])
        return None in declared or declared[0] == declared[1]
    return left["sample_limit"] == right["sample_limit"]


def compare_manifest_data(left: dict[str, Any], right: dict[str, Any]) -> Comparison:
    scope_match = left["scope_digest"] == right["scope_digest"]
    coverage_match = _coverage_match(left["coverage"], right["coverage"])
    left_samples = left["samples"]
    right_samples = right["samples"]

    ordered_match = left_samples["ordered_digest"] == right_samples["ordered_digest"]
    unordered_match = left_samples["unordered_digest"] == right_samples["unordered_digest"]
    types_match = left_samples["top_level_type_summary"] == right_samples["top_level_type_summary"]

    fields = sorted(set(left_samples["field_digests"]) | set(right_samples["field_digests"]))
    field_matches: dict[str, dict[str, bool]] = {}
    for field in fields:
        left_field = left_samples["field_digests"].get(field)
        right_field = right_samples["field_digests"].get(field)
        field_matches[field] = {
            "ordered": bool(
                left_field and right_field and left_field["ordered"] == right_field["ordered"]
            ),
            "unordered": bool(
                left_field and right_field and left_field["unordered"] == right_field["unordered"]
            ),
        }

    left_counter = Counter(left_samples["ordered_hashes"])
    right_counter = Counter(right_samples["ordered_hashes"])
    added = sum((right_counter - left_counter).values())
    removed = sum((left_counter - right_counter).values())
    first_mismatch = _first_mismatch(
        left_samples["ordered_hashes"], right_samples["ordered_hashes"]
    )

    notes: list[str] = []
    if not scope_match:
        notes.append("The manifests describe different evaluation contracts or adapter parameters.")
    if not coverage_match:
        notes.append("The manifests do not cover the same number/range of records.")
    if unordered_match and not ordered_match:
        notes.append("Sample membership is unchanged, but sample ordering moved.")
    if not unordered_match:
        notes.append("Sample membership or sample content changed.")
    if not types_match:
        notes.append("Top-level field type distributions changed.")
    changed_fields = [field for field, match in field_matches.items() if not match["unordered"]]
    if changed_fields:
        notes.append(f"Semantic fields changed: {', '.join(changed_fields)}.")

    all_field_ordered = all(match["ordered"] for match in field_matches.values())
    all_field_unordered = all(match["unordered"] for match in field_matches.values())

    if not scope_match:
        verdict = Verdict.SCOPE_MISMATCH
    elif not coverage_match:
        verdict = Verdict.COVERAGE_MISMATCH
    elif not unordered_match or not types_match or not all_field_unordered:
        verdict = Verdict.SEMANTIC_DRIFT
    elif not ordered_match or not all_field_ordered:
        verdict = Verdict.ORDER_DRIFT
    else:
        verdict = Verdict.REPRODUCIBLE

    return Comparison(
        verdict=verdict,
        reproducible=verdict is Verdict.REPRODUCIBLE,
        scope_match=scope_match,
        coverage_match=coverage_match,
        ordered_samples_match=ordered_match,
        unordered_samples_match=unordered_match,
        top_level_types_match=types_match,
        field_matches=field_matches,
        added_sample_hashes=added,
        removed_sample_hashes=removed,
        first_ordered_mismatch=first_mismatch,
        baseline_runtime=left["runtime"],
        candidate_runtime=right["runtime"],
        baseline_coverage=left["coverage"],
        candidate_coverage=right["coverage"],
        notes=tuple(notes),
    )


def compare_manifests(baseline: Path, candidate: Path) -> Comparison:
    return compare_manifest_data(read_manifest(baseline), read_manifest(candidate))
