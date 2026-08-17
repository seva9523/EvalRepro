from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from evalrepro.compare import Verdict, compare_manifest_data
from tools.agentic_engineering_case_study import (
    ARTIFACT_PATHS,
    EXPECTED_CHANGED_PATHS,
    _assert_expected_case,
    _snapshot,
    run_case_study,
)


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_contract(repository: Path, *, candidate: bool = False) -> None:
    for path in ARTIFACT_PATHS:
        destination = repository / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        value = f"stable:{path}\n"
        if candidate and path in EXPECTED_CHANGED_PATHS:
            value = f"hardened:{path}\n"
        destination.write_text(value, encoding="utf-8")


def _source_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repository = tmp_path / "source"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Test")
    _git(repository, "config", "user.email", "test@example.com")
    _write_contract(repository)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "baseline")
    baseline = _git(repository, "rev-parse", "HEAD")
    _write_contract(repository, candidate=True)
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "candidate")
    candidate = _git(repository, "rev-parse", "HEAD")
    return repository, baseline, candidate


def test_case_study_detects_only_the_expected_workflow_drift(tmp_path: Path) -> None:
    repository, baseline, candidate = _source_repository(tmp_path)

    summary = run_case_study(
        repository,
        baseline_revision=baseline,
        candidate_revision=candidate,
        output=tmp_path / "results",
    )

    assert summary["comparison"]["verdict"] == Verdict.SEMANTIC_DRIFT.value
    assert summary["comparison"]["changed_paths"] == list(EXPECTED_CHANGED_PATHS)
    assert summary["comparison"]["unchanged_path_count"] == 5
    assert summary["baseline"]["artifact_count"] == 8
    assert summary["candidate"]["artifact_count"] == 8
    assert (tmp_path / "results" / "baseline.manifest.json").is_file()
    assert (tmp_path / "results" / "candidate.manifest.json").is_file()


def test_case_study_manifests_omit_artifact_id_previews(tmp_path: Path) -> None:
    repository, baseline, _ = _source_repository(tmp_path)

    snapshot = _snapshot(repository, baseline, tmp_path / "baseline.json")

    assert snapshot.manifest["coverage"] == {
        "declared_count": 8,
        "processed_count": 8,
        "complete": True,
        "sample_limit": None,
    }
    assert snapshot.manifest["samples"]["id_preview"] == {"first": [], "last": []}
    assert "stable:" not in (tmp_path / "baseline.json").read_text(encoding="utf-8")


def test_expected_case_rejects_drift_outside_generated_workflows(tmp_path: Path) -> None:
    repository, baseline, candidate = _source_repository(tmp_path)
    card = repository / "starters/read-only/agent-card.json"
    card.write_text("unexpected card drift\n", encoding="utf-8")
    _git(repository, "add", str(card.relative_to(repository)))
    _git(repository, "commit", "-m", "unexpected")
    unexpected_candidate = _git(repository, "rev-parse", "HEAD")
    baseline_snapshot = _snapshot(repository, baseline, tmp_path / "baseline.json")
    candidate_snapshot = _snapshot(
        repository,
        unexpected_candidate,
        tmp_path / "candidate.json",
    )
    comparison = compare_manifest_data(
        baseline_snapshot.manifest,
        candidate_snapshot.manifest,
    )

    with pytest.raises(RuntimeError, match="unexpected artifact set"):
        _assert_expected_case(baseline_snapshot, candidate_snapshot, comparison)

    assert candidate != unexpected_candidate
