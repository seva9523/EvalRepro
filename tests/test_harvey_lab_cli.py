from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evalrepro.cli import main


def _write_task(root: Path) -> None:
    task_dir = root / "tasks/contracts/task-a"
    docs_dir = task_dir / "documents"
    docs_dir.mkdir(parents=True)
    (docs_dir / "source.txt").write_text("source", encoding="utf-8")
    config: dict[str, Any] = {
        "title": "Review",
        "instructions": "Review the source.",
        "criteria": [{"id": "C-001", "title": "Issue", "match_criteria": "PASS"}],
    }
    (task_dir / "task.json").write_text(json.dumps(config), encoding="utf-8")


def test_cli_snapshots_harvey_lab_without_id_preview(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_task(root)
    output = tmp_path / "manifest.json"

    exit_code = main(
        [
            "snapshot",
            "harvey-lab",
            str(root),
            "--task",
            "contracts",
            "-o",
            str(output),
            "--no-id-preview",
        ]
    )

    manifest = json.loads(output.read_text())
    assert exit_code == 0
    assert manifest["scope"]["adapter"] == "harvey-lab"
    assert manifest["scope"]["parameters"]["task_selector"] == "contracts"
    assert manifest["samples"]["id_preview"] == {"first": [], "last": []}


def test_cli_harvey_lab_user_error_returns_three(tmp_path: Path, capsys: object) -> None:
    output = tmp_path / "manifest.json"

    exit_code = main(
        ["snapshot", "harvey-lab", str(tmp_path / "missing"), "-o", str(output)]
    )

    assert exit_code == 3
    assert "repository path does not exist" in capsys.readouterr().err  # type: ignore[attr-defined]
