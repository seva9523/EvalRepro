"""Run the pinned Awesome Agentic Engineering public-file contract case study."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, overload

from evalrepro import __version__
from evalrepro.adapters.base import SnapshotSource
from evalrepro.compare import Comparison, Verdict, compare_manifest_data
from evalrepro.manifest import MANIFEST_SCHEMA_VERSION, build_manifest, write_manifest
from evalrepro.report import render_markdown

BASELINE_REVISION = "d3bafb19c06bd493b43188675cf7b7fd4dbf3065"
CANDIDATE_REVISION = "7edabb8a76a225fd035b13f33f0b997c03175016"
SOURCE_REPOSITORY = "https://github.com/lindixu6-hash/awesome-agentic-engineering"
CASE_STUDY_CONTRACT_VERSION = 1

ARTIFACT_PATHS = (
    "starters/read-only/agent-card.json",
    "starters/draft-only/agent-card.json",
    "starters/state-changing/agent-card.json",
    "starters/read-only/agent-readiness.yml",
    "starters/draft-only/agent-readiness.yml",
    "starters/state-changing/agent-readiness.yml",
    "evals/prompt-injection/fixtures.jsonl",
    "schema/agent-card.schema.json",
)
EXPECTED_CHANGED_PATHS = (
    "starters/read-only/agent-readiness.yml",
    "starters/draft-only/agent-readiness.yml",
    "starters/state-changing/agent-readiness.yml",
)


@dataclass(frozen=True, slots=True)
class RevisionSnapshot:
    """One pinned revision represented as a hash-only public-file contract."""

    revision: str
    blob_shas: Mapping[str, str]
    manifest: dict[str, Any]


@overload
def _run_git(repository: Path, *args: str, binary: Literal[False] = False) -> str: ...


@overload
def _run_git(repository: Path, *args: str, binary: Literal[True]) -> bytes: ...


def _run_git(repository: Path, *args: str, binary: bool = False) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            text=not binary,
            encoding=None if binary else "utf-8",
            errors=None if binary else "replace",
        )
    except OSError as exc:
        raise RuntimeError(f"Cannot run git for the source checkout: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr
        stdout = exc.stdout
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        detail = (stderr or stdout or "git command failed").strip()
        raise RuntimeError(f"Source git command failed: {detail}") from exc
    if binary:
        assert isinstance(result.stdout, bytes)
        return result.stdout
    assert isinstance(result.stdout, str)
    return result.stdout.strip()


def _validate_revision(revision: str) -> None:
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise RuntimeError(f"Revision must be a full lowercase commit SHA: {revision}")


def _verify_revision(repository: Path, revision: str) -> None:
    _validate_revision(revision)
    actual = _run_git(repository, "rev-parse", f"{revision}^{{commit}}")
    if actual != revision:
        raise RuntimeError(f"Revision mismatch: expected {revision}, got {actual}")


def _verify_history(repository: Path, baseline_revision: str, candidate_revision: str) -> None:
    _verify_revision(repository, baseline_revision)
    _verify_revision(repository, candidate_revision)
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_revision, candidate_revision],
            cwd=repository,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("The candidate revision does not descend from the baseline.") from exc


def _artifact_kind(path: str) -> str:
    if path.endswith("agent-card.json"):
        return "agent-card"
    if path.endswith("agent-readiness.yml"):
        return "generated-workflow"
    if path.endswith("fixtures.jsonl"):
        return "evaluation-fixture-pack"
    if path.endswith("agent-card.schema.json"):
        return "agent-card-schema"
    raise RuntimeError(f"Unsupported case-study artifact path: {path}")


def _snapshot(repository: Path, revision: str, output: Path) -> RevisionSnapshot:
    _verify_revision(repository, revision)
    records: list[dict[str, Any]] = []
    blob_shas: dict[str, str] = {}
    for path in ARTIFACT_PATHS:
        content = _run_git(repository, "show", f"{revision}:{path}", binary=True)
        assert isinstance(content, bytes)
        blob_sha = _run_git(repository, "rev-parse", f"{revision}:{path}")
        assert isinstance(blob_sha, str)
        if len(blob_sha) != 40:
            raise RuntimeError(f"Invalid git blob SHA for {path}: {blob_sha}")
        blob_shas[path] = blob_sha
        records.append(
            {
                "id": path,
                "input": {"content_sha256": hashlib.sha256(content).hexdigest()},
                "target": None,
                "choices": None,
                "metadata": {"artifact_kind": _artifact_kind(path)},
            }
        )

    source = SnapshotSource(
        adapter="case-study-public-files",
        identity={"repository": SOURCE_REPOSITORY},
        parameters={
            "contract_version": CASE_STUDY_CONTRACT_VERSION,
            "artifact_paths": list(ARTIFACT_PATHS),
        },
        records=records,
        declared_count=len(ARTIFACT_PATHS),
        runtime={},
        provenance={
            "git_commit": revision,
            "source_repository": SOURCE_REPOSITORY,
        },
    )
    manifest = build_manifest(source, include_id_preview=False)
    write_manifest(output, manifest)
    return RevisionSnapshot(revision=revision, blob_shas=blob_shas, manifest=manifest)


def _changed_paths(
    baseline: RevisionSnapshot,
    candidate: RevisionSnapshot,
) -> tuple[str, ...]:
    if tuple(baseline.blob_shas) != ARTIFACT_PATHS:
        raise RuntimeError("Baseline artifact ordering does not match the case-study contract.")
    if tuple(candidate.blob_shas) != ARTIFACT_PATHS:
        raise RuntimeError("Candidate artifact ordering does not match the case-study contract.")
    return tuple(
        path for path in ARTIFACT_PATHS if baseline.blob_shas[path] != candidate.blob_shas[path]
    )


def _assert_expected_case(
    baseline: RevisionSnapshot,
    candidate: RevisionSnapshot,
    comparison: Comparison,
) -> tuple[str, ...]:
    changed_paths = _changed_paths(baseline, candidate)
    if changed_paths != EXPECTED_CHANGED_PATHS:
        raise RuntimeError(
            "Pinned revisions changed an unexpected artifact set: " + ", ".join(changed_paths)
        )
    if comparison.verdict is not Verdict.SEMANTIC_DRIFT:
        raise RuntimeError(
            f"Expected semantic_drift for the pinned revisions, got {comparison.verdict.value}."
        )
    if not comparison.scope_match or not comparison.coverage_match:
        raise RuntimeError("The pinned revisions must have matching scope and complete coverage.")
    if comparison.field_matches.get("input") != {"ordered": False, "unordered": False}:
        raise RuntimeError("The expected workflow byte changes must appear in the input field.")
    for field in ("target", "choices", "metadata"):
        if comparison.field_matches.get(field) != {"ordered": True, "unordered": True}:
            raise RuntimeError(f"The pinned case unexpectedly changed the {field} field.")
    return changed_paths


def _public_snapshot(snapshot: RevisionSnapshot) -> dict[str, Any]:
    samples = snapshot.manifest["samples"]
    return {
        "revision": snapshot.revision,
        "artifact_count": len(snapshot.blob_shas),
        "git_blob_shas": dict(snapshot.blob_shas),
        "scope_digest": snapshot.manifest["scope_digest"],
        "ordered_artifact_digest": samples["ordered_digest"],
        "unordered_artifact_digest": samples["unordered_digest"],
    }


def _render_summary(summary: Mapping[str, Any]) -> str:
    baseline = summary["baseline"]
    candidate = summary["candidate"]
    comparison = summary["comparison"]
    changed_paths = comparison["changed_paths"]
    return "\n".join(
        [
            "# Awesome Agentic Engineering pinned-release result",
            "",
            "**Validation status:** public design-partner case reproduced by the EvalRepro "
            "case-study script; a pinned GitHub workflow is included. No adoption or endorsement "
            "is claimed.",
            "",
            "| Evidence | Result |",
            "| --- | --- |",
            f"| Baseline revision | `{baseline['revision']}` |",
            f"| Candidate revision | `{candidate['revision']}` |",
            f"| Selected artifact coverage | {baseline['artifact_count']} → "
            f"{candidate['artifact_count']} |",
            f"| Verdict | `{comparison['verdict']}` |",
            f"| Changed selected artifacts | {len(changed_paths)} of "
            f"{baseline['artifact_count']} |",
            "| Changed paths | " + ", ".join(f"`{path}`" for path in changed_paths) + " |",
            "| Unchanged selected artifacts | 3 Agent Cards, fixture pack, Agent Card Schema |",
            "| Manifest / case-study contract | "
            f"v{summary['evalrepro']['manifest_schema_version']} / "
            f"v{summary['evalrepro']['case_study_contract_version']} |",
            "",
            "The run reads the eight public files directly from two immutable git revisions. "
            "Published manifests contain hashes and aggregate metadata, not file contents. It "
            "does not run an agent, a model, a judge, or the generated workflows.",
            "",
        ]
    )


def _source_compare_url(baseline_revision: str, candidate_revision: str) -> str:
    return f"{SOURCE_REPOSITORY}/compare/{baseline_revision}...{candidate_revision}"


def run_case_study(
    repository: Path,
    *,
    baseline_revision: str = BASELINE_REVISION,
    candidate_revision: str = CANDIDATE_REVISION,
    output: Path,
) -> dict[str, Any]:
    _verify_history(repository, baseline_revision, candidate_revision)
    output.mkdir(parents=True, exist_ok=True)
    baseline = _snapshot(repository, baseline_revision, output / "baseline.manifest.json")
    candidate = _snapshot(repository, candidate_revision, output / "candidate.manifest.json")
    comparison = compare_manifest_data(baseline.manifest, candidate.manifest)
    changed_paths = _assert_expected_case(baseline, candidate, comparison)

    comparison_payload = comparison.to_dict()
    comparison_payload["changed_paths"] = list(changed_paths)
    comparison_payload["unchanged_path_count"] = len(ARTIFACT_PATHS) - len(changed_paths)
    stable_comparison = {
        key: value
        for key, value in comparison_payload.items()
        if key not in {"baseline_runtime", "candidate_runtime"}
    }
    summary: dict[str, Any] = {
        "case_study": "awesome-agentic-engineering-v0.15.0-to-v0.16.0",
        "source_repository": SOURCE_REPOSITORY,
        "source_compare": _source_compare_url(baseline_revision, candidate_revision),
        "validation_status": "evalrepro-project-validated",
        "design_partner_status": "public-case-submitted",
        "evalrepro": {
            "version": __version__,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "case_study_contract_version": CASE_STUDY_CONTRACT_VERSION,
        },
        "baseline": _public_snapshot(baseline),
        "candidate": _public_snapshot(candidate),
        "comparison": stable_comparison,
        "limitations": [
            "This compares bytes for eight selected public files, not executed agent behaviour.",
            "The result does not cover other files changed between the two repository revisions.",
            "Expected workflow drift records a dependency-pin hardening; it does not rate quality.",
            "No project adoption, endorsement, or broad compatibility claim is made.",
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
        description="Run the pinned Awesome Agentic Engineering public-file case study."
    )
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--baseline", default=BASELINE_REVISION)
    parser.add_argument("--candidate", default=CANDIDATE_REVISION)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_case_study(
            args.repository.resolve(),
            baseline_revision=args.baseline,
            candidate_revision=args.candidate,
            output=args.output.resolve(),
        )
    except RuntimeError as exc:
        print(f"agentic-engineering-case-study: {exc}", file=sys.stderr)
        return 1
    print(_render_summary(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
