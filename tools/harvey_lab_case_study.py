"""Run the pinned Harvey LAB firm-knowledge task-contract case study."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evalrepro import __version__
from evalrepro.adapters.harvey_lab import ADAPTER_CONTRACT_VERSION, harvey_lab_source
from evalrepro.compare import Comparison, Verdict, compare_manifest_data
from evalrepro.manifest import MANIFEST_SCHEMA_VERSION, build_manifest, write_manifest
from evalrepro.report import render_markdown

BASELINE_REVISION = "55510f0e609ffa5cf6f5df17d9a813ce4bb33d0c"
CANDIDATE_REVISION = "60071cc424d6479569626b8c76d90b958fe2d6c0"
DEFAULT_SELECTOR = "firm-knowledge"
SOURCE_REPOSITORY = "https://github.com/harveyai/harvey-labs"
SOURCE_COMPARE = f"{SOURCE_REPOSITORY}/compare/{BASELINE_REVISION}...{CANDIDATE_REVISION}"


@dataclass(frozen=True, slots=True)
class DocumentStats:
    """Aggregate document evidence without retaining document paths or bytes."""

    corpus_count: int
    document_count: int
    total_bytes: int
    inventory_digests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RevisionSnapshot:
    """One in-memory pinned revision snapshot and its aggregate evidence."""

    revision: str
    task_ids: tuple[str, ...]
    documents: DocumentStats
    manifest: dict[str, Any]


def _run_git(repository: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise RuntimeError(f"Cannot run git for Harvey LAB checkout: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "git command failed").strip()
        raise RuntimeError(f"Harvey LAB git command failed: {detail}") from exc
    return result.stdout.strip()


def _checkout_revision(repository: Path, revision: str) -> None:
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise RuntimeError(f"Harvey LAB revision must be a full lowercase commit SHA: {revision}")
    _run_git(repository, "checkout", "--detach", "--force", revision)
    actual = _run_git(repository, "rev-parse", "HEAD")
    if actual != revision:
        raise RuntimeError(f"Harvey LAB checkout mismatch: expected {revision}, got {actual}")
    status = _run_git(repository, "status", "--porcelain", "--untracked-files=normal")
    if status:
        raise RuntimeError("Harvey LAB checkout must be clean before snapshotting.")


def _record_id(record: Mapping[str, Any]) -> str:
    value = record.get("id")
    if not isinstance(value, str) or not value:
        raise RuntimeError("Harvey LAB adapter emitted a record without a stable task ID.")
    return value


def _document_stats(records: Sequence[Mapping[str, Any]]) -> DocumentStats:
    inventories: dict[str, tuple[int, int]] = {}
    for record in records:
        metadata = record.get("metadata")
        if not isinstance(metadata, Mapping):
            raise RuntimeError("Harvey LAB adapter record is missing metadata.")
        inventory = metadata.get("source_documents")
        if not isinstance(inventory, Mapping):
            raise RuntimeError("Harvey LAB adapter record is missing its document inventory.")

        inventory_digest = inventory.get("ordered_digest")
        count = inventory.get("count")
        total_bytes = inventory.get("total_bytes")
        if not isinstance(inventory_digest, str) or len(inventory_digest) != 64:
            raise RuntimeError("Harvey LAB document inventory digest is invalid.")
        if not isinstance(count, int) or count < 0:
            raise RuntimeError("Harvey LAB document inventory count is invalid.")
        if not isinstance(total_bytes, int) or total_bytes < 0:
            raise RuntimeError("Harvey LAB document inventory byte count is invalid.")

        value = (count, total_bytes)
        previous = inventories.setdefault(inventory_digest, value)
        if previous != value:
            raise RuntimeError("A Harvey LAB document digest maps to inconsistent aggregate data.")

    return DocumentStats(
        corpus_count=len(inventories),
        document_count=sum(count for count, _ in inventories.values()),
        total_bytes=sum(total_bytes for _, total_bytes in inventories.values()),
        inventory_digests=tuple(sorted(inventories)),
    )


def _snapshot(
    repository: Path,
    revision: str,
    selector: str,
    output: Path,
) -> RevisionSnapshot:
    _checkout_revision(repository, revision)
    source = harvey_lab_source(repository, task=selector)
    records = list(source.records)
    mapping_records: list[Mapping[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise RuntimeError("Harvey LAB adapter emitted a non-object task record.")
        mapping_records.append(record)
    source.records = records

    task_ids = tuple(_record_id(record) for record in mapping_records)
    if len(task_ids) != len(set(task_ids)):
        raise RuntimeError("Harvey LAB adapter emitted duplicate task IDs.")
    documents = _document_stats(mapping_records)
    manifest = build_manifest(source, include_id_preview=False)
    provenance_revision = manifest["provenance"].get("git_commit")
    if provenance_revision != revision:
        raise RuntimeError(
            "Harvey LAB manifest provenance does not match the pinned revision: "
            f"expected {revision}, got {provenance_revision}"
        )
    if manifest["provenance"].get("git_dirty"):
        raise RuntimeError("Harvey LAB manifest reports a dirty source checkout.")
    write_manifest(output, manifest)
    return RevisionSnapshot(
        revision=revision,
        task_ids=task_ids,
        documents=documents,
        manifest=manifest,
    )


def _public_snapshot(snapshot: RevisionSnapshot) -> dict[str, Any]:
    samples = snapshot.manifest["samples"]
    return {
        "revision": snapshot.revision,
        "task_count": len(snapshot.task_ids),
        "document_corpora": snapshot.documents.corpus_count,
        "source_document_count": snapshot.documents.document_count,
        "source_document_bytes": snapshot.documents.total_bytes,
        "document_inventory_digests": list(snapshot.documents.inventory_digests),
        "scope_digest": snapshot.manifest["scope_digest"],
        "ordered_task_digest": samples["ordered_digest"],
        "unordered_task_digest": samples["unordered_digest"],
    }


def _compare_snapshots(
    baseline: RevisionSnapshot,
    candidate: RevisionSnapshot,
) -> tuple[Comparison, dict[str, Any]]:
    if baseline.task_ids != candidate.task_ids:
        raise RuntimeError(
            "Pinned revisions do not expose the same ordered task IDs; positional changed-task "
            "counting would be unsafe."
        )

    baseline_hashes = baseline.manifest["samples"]["ordered_hashes"]
    candidate_hashes = candidate.manifest["samples"]["ordered_hashes"]
    changed_task_count = sum(
        baseline_hash != candidate_hash
        for baseline_hash, candidate_hash in zip(
            baseline_hashes, candidate_hashes, strict=True
        )
    )
    comparison = compare_manifest_data(baseline.manifest, candidate.manifest)
    payload = comparison.to_dict()
    payload.update(
        {
            "changed_task_count": changed_task_count,
            "unchanged_task_count": len(baseline.task_ids) - changed_task_count,
        }
    )
    return comparison, payload


def _assert_expected_case(
    baseline: RevisionSnapshot,
    candidate: RevisionSnapshot,
    comparison: Comparison,
    comparison_payload: Mapping[str, Any],
) -> None:
    if len(baseline.task_ids) != 250 or len(candidate.task_ids) != 250:
        raise RuntimeError("The pinned firm-knowledge case must contain exactly 250 tasks.")
    if baseline.documents != candidate.documents:
        raise RuntimeError("The pinned revisions unexpectedly changed the shared document corpus.")
    if baseline.documents.document_count == 0:
        raise RuntimeError("The pinned firm-knowledge case did not discover source documents.")
    if comparison.verdict is not Verdict.SEMANTIC_DRIFT:
        raise RuntimeError(
            f"Expected semantic_drift for the pinned revisions, got {comparison.verdict.value}."
        )
    if not comparison.scope_match or not comparison.coverage_match:
        raise RuntimeError("The pinned revisions must have matching scope and complete coverage.")
    if comparison.field_matches.get("metadata") != {"ordered": True, "unordered": True}:
        raise RuntimeError("Shared document/task metadata should remain unchanged in this case.")
    if comparison.field_matches.get("input", {}).get("unordered", True):
        raise RuntimeError("The pinned v3 update should change task inputs.")
    if comparison.field_matches.get("target", {}).get("unordered", True):
        raise RuntimeError("The pinned v3 update should change task rubrics.")
    if not isinstance(comparison_payload.get("changed_task_count"), int):
        raise RuntimeError("The changed-task count is missing from the comparison summary.")
    if comparison_payload["changed_task_count"] <= 0:
        raise RuntimeError("The pinned v3 update should change at least one task contract.")


def _render_summary(summary: Mapping[str, Any]) -> str:
    baseline = summary["baseline"]
    candidate = summary["candidate"]
    comparison = summary["comparison"]
    evalrepro = summary["evalrepro"]
    field_matches = comparison["field_matches"]
    changed_fields = ", ".join(
        f"`{field}`" for field, match in field_matches.items() if not match["unordered"]
    )
    return "\n".join(
        [
            "# Harvey LAB pinned-revision result",
            "",
            "**Validation status:** EvalRepro project workflow; not upstream-reviewed or "
            "upstream-merged.",
            "",
            "| Evidence | Result |",
            "| --- | --- |",
            f"| Baseline revision | `{baseline['revision']}` |",
            f"| Candidate revision | `{candidate['revision']}` |",
            f"| Task selector | `{summary['selector']}` |",
            f"| Task coverage | {baseline['task_count']} → {candidate['task_count']} |",
            f"| Shared document corpus | {baseline['source_document_count']} files; "
            f"{baseline['source_document_bytes']} bytes |",
            f"| Verdict | `{comparison['verdict']}` |",
            f"| Changed task contracts | {comparison['changed_task_count']} of "
            f"{baseline['task_count']} |",
            f"| Changed semantic fields | {changed_fields or 'none'} |",
            f"| Manifest / adapter contract | v{evalrepro['manifest_schema_version']} / "
            f"v{evalrepro['adapter_contract_version']} |",
            "",
            "The run imported no Harvey LAB Python modules and made no model, judge, or provider "
            "API calls. Manifests omit task-ID previews and contain hashes and aggregate metadata, "
            "not raw instructions, rubrics, document paths, or document bytes.",
            "",
        ]
    )


def run_case_study(
    repository: Path,
    *,
    baseline_revision: str = BASELINE_REVISION,
    candidate_revision: str = CANDIDATE_REVISION,
    selector: str = DEFAULT_SELECTOR,
    output: Path,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    baseline = _snapshot(
        repository,
        baseline_revision,
        selector,
        output / "baseline.manifest.json",
    )
    candidate = _snapshot(
        repository,
        candidate_revision,
        selector,
        output / "candidate.manifest.json",
    )
    comparison, comparison_payload = _compare_snapshots(baseline, candidate)
    _assert_expected_case(baseline, candidate, comparison, comparison_payload)

    summary: dict[str, Any] = {
        "case_study": "harvey-lab-firm-knowledge-v3-rubric",
        "source_repository": SOURCE_REPOSITORY,
        "source_compare": SOURCE_COMPARE,
        "selector": selector,
        "external_review_status": "not_upstream_reviewed",
        "evalrepro": {
            "version": __version__,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        },
        "baseline": _public_snapshot(baseline),
        "candidate": _public_snapshot(candidate),
        "comparison": comparison_payload,
        "limitations": [
            "This compares task contracts and source-document bytes, not model or judge outputs.",
            "Semantic drift does not establish whether the candidate rubric is better or worse.",
            "The result applies only to the two pinned revisions and the firm-knowledge selector.",
            "No Harvey maintainer review, adoption, or endorsement is claimed.",
        ],
    }
    (output / "comparison.json").write_text(
        json.dumps(comparison_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "comparison.md").write_text(render_markdown(comparison), encoding="utf-8")
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "summary.md").write_text(_render_summary(summary), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the pinned Harvey LAB firm-knowledge task-contract case study."
    )
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--baseline", default=BASELINE_REVISION)
    parser.add_argument("--candidate", default=CANDIDATE_REVISION)
    parser.add_argument("--selector", default=DEFAULT_SELECTOR)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_case_study(
            args.repository.resolve(),
            baseline_revision=args.baseline,
            candidate_revision=args.candidate,
            selector=args.selector,
            output=args.output.resolve(),
        )
    except RuntimeError as exc:
        print(f"harvey-lab-case-study: {exc}", file=sys.stderr)
        return 1
    print(_render_summary(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
