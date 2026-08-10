from __future__ import annotations

import json
from pathlib import Path

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
    assert "semantic_drift" in report_markdown.read_text()
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
