from __future__ import annotations

import json
from pathlib import Path

import pytest

from evalrepro.cli import main


def test_cli_snapshot_validate_and_compare(tmp_path: Path, capsys: object) -> None:
    baseline_data = tmp_path / "baseline.jsonl"
    candidate_data = tmp_path / "candidate.jsonl"
    baseline_manifest = tmp_path / "baseline.json"
    candidate_manifest = tmp_path / "candidate.json"
    report_json = tmp_path / "report.json"
    report_markdown = tmp_path / "report.md"

    baseline_data.write_text('{"id":"1","input":"a","target":"x"}\n')
    candidate_data.write_text('{"id":"1","input":"a","target":"y"}\n')

    assert main(["snapshot", "jsonl", str(baseline_data), "-o", str(baseline_manifest)]) == 0
    assert main(["snapshot", "jsonl", str(candidate_data), "-o", str(candidate_manifest)]) == 0
    assert main(["validate", str(baseline_manifest)]) == 0

    exit_code = main(
        [
            "compare",
            str(baseline_manifest),
            str(candidate_manifest),
            "--json",
            str(report_json),
            "--markdown",
            str(report_markdown),
        ]
    )

    assert exit_code == 2
    assert json.loads(report_json.read_text())["verdict"] == "semantic_drift"
    assert "semantic_drift" in report_markdown.read_text(encoding="utf-8")
    assert "EvalRepro verdict" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_cli_allow_drift_returns_success(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text('{"id":"1","input":"a"}\n')
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    assert main(["snapshot", "jsonl", str(source), "-o", str(left), "--name", "left"]) == 0
    assert main(["snapshot", "jsonl", str(source), "-o", str(right), "--name", "right"]) == 0

    assert main(["compare", str(left), str(right), "--allow-drift", "--quiet"]) == 0


def test_cli_no_id_preview_preserves_hashes(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text('{"id":"private-case-1","input":"a"}\n')
    with_preview = tmp_path / "with-preview.json"
    without_preview = tmp_path / "without-preview.json"

    assert main(["snapshot", "jsonl", str(source), "-o", str(with_preview)]) == 0
    assert (
        main(
            [
                "snapshot",
                "jsonl",
                str(source),
                "-o",
                str(without_preview),
                "--no-id-preview",
            ]
        )
        == 0
    )

    visible = json.loads(with_preview.read_text())
    private = json.loads(without_preview.read_text())
    assert visible["samples"]["id_preview"]["first"] == ["private-case-1"]
    assert private["samples"]["id_preview"] == {"first": [], "last": []}
    assert private["samples"]["ordered_hashes"] == visible["samples"]["ordered_hashes"]


def test_cli_bad_jsonl_returns_user_error(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "broken.jsonl"
    source.write_text("not-json\n")

    exit_code = main(["snapshot", "jsonl", str(source), "-o", str(tmp_path / "out.json")])

    assert exit_code == 3
    assert "Invalid JSON" in capsys.readouterr().err  # type: ignore[attr-defined]


def test_cli_validate_rejects_malformed_manifest_json(tmp_path: Path, capsys: object) -> None:
    manifest = tmp_path / "malformed.json"
    manifest.write_text("{not-json\n")

    assert main(["validate", str(manifest)]) == 3
    assert "Invalid JSON manifest" in capsys.readouterr().err  # type: ignore[attr-defined]


def test_cli_validate_rejects_structurally_invalid_manifest(tmp_path: Path, capsys: object) -> None:
    manifest = tmp_path / "incomplete.json"
    manifest.write_text(json.dumps({"manifest_schema_version": 1}))

    assert main(["validate", str(manifest)]) == 3
    assert "missing object 'runtime'" in capsys.readouterr().err  # type: ignore[attr-defined]


@pytest.mark.parametrize("invalid_position", ["baseline", "candidate"])
def test_cli_compare_invalid_manifest_writes_no_reports(
    tmp_path: Path, capsys: object, invalid_position: str
) -> None:
    valid_source = tmp_path / "source.jsonl"
    valid_manifest = tmp_path / "valid.json"
    invalid_manifest = tmp_path / "invalid.json"
    json_report = tmp_path / "report.json"
    markdown_report = tmp_path / "report.md"
    valid_source.write_text('{"id":"1","input":"a"}\n')
    invalid_manifest.write_text("{not-json\n")
    assert main(["snapshot", "jsonl", str(valid_source), "-o", str(valid_manifest)]) == 0

    manifests = (
        (invalid_manifest, valid_manifest)
        if invalid_position == "baseline"
        else (valid_manifest, invalid_manifest)
    )
    assert (
        main(
            [
                "compare",
                str(manifests[0]),
                str(manifests[1]),
                "--json",
                str(json_report),
                "--markdown",
                str(markdown_report),
            ]
        )
        == 3
    )
    assert "Invalid JSON manifest" in capsys.readouterr().err  # type: ignore[attr-defined]
    assert not json_report.exists()
    assert not markdown_report.exists()


def test_cli_compare_semantic_drift_allow_drift_and_quiet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline_data = tmp_path / "baseline.jsonl"
    candidate_data = tmp_path / "candidate.jsonl"
    baseline_manifest = tmp_path / "baseline.json"
    candidate_manifest = tmp_path / "candidate.json"
    report_json = tmp_path / "report.json"

    baseline_data.write_text(
        '{"id":"1","input":"prompt","target":"expected_a"}\n', encoding="utf-8"
    )
    candidate_data.write_text(
        '{"id":"1","input":"prompt","target":"expected_b"}\n', encoding="utf-8"
    )

    assert main(["snapshot", "jsonl", str(baseline_data), "-o", str(baseline_manifest)]) == 0
    assert main(["snapshot", "jsonl", str(candidate_data), "-o", str(candidate_manifest)]) == 0

    # 1. Default comparison on semantic drift returns exit code 2 and prints text report
    exit_code_default = main(
        [
            "compare",
            str(baseline_manifest),
            str(candidate_manifest),
        ]
    )
    assert exit_code_default == 2
    out_default = capsys.readouterr().out
    assert "EvalRepro verdict: semantic_drift" in out_default

    # 2. --allow-drift returns exit code 0 while keeping semantic_drift in reports
    exit_code_allow_drift = main(
        [
            "compare",
            str(baseline_manifest),
            str(candidate_manifest),
            "--allow-drift",
            "--json",
            str(report_json),
        ]
    )
    assert exit_code_allow_drift == 0
    allow_drift_data = json.loads(report_json.read_text(encoding="utf-8"))
    assert allow_drift_data["verdict"] == "semantic_drift"
    capsys.readouterr()

    # 3. --quiet suppresses text report on stdout, while writing requested JSON and Markdown
    quiet_report_json = tmp_path / "quiet_report.json"
    quiet_report_markdown = tmp_path / "quiet_report.md"
    exit_code_quiet = main(
        [
            "compare",
            str(baseline_manifest),
            str(candidate_manifest),
            "--quiet",
            "--json",
            str(quiet_report_json),
            "--markdown",
            str(quiet_report_markdown),
        ]
    )
    assert exit_code_quiet == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    assert quiet_report_json.exists()
    assert quiet_report_markdown.exists()
    assert json.loads(quiet_report_json.read_text(encoding="utf-8"))["verdict"] == "semantic_drift"
    assert "semantic_drift" in quiet_report_markdown.read_text(encoding="utf-8")


def test_cli_compare_quiet_preserves_actionable_stderr_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    valid_source = tmp_path / "valid.jsonl"
    valid_source.write_text('{"id":"1","input":"a"}\n', encoding="utf-8")
    valid_manifest = tmp_path / "valid.json"
    missing_manifest = tmp_path / "missing.json"

    assert main(["snapshot", "jsonl", str(valid_source), "-o", str(valid_manifest)]) == 0
    capsys.readouterr()

    exit_code = main(
        [
            "compare",
            str(valid_manifest),
            str(missing_manifest),
            "--quiet",
        ]
    )
    assert exit_code == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Cannot read manifest" in captured.err
