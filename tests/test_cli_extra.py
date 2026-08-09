from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from evalrepro import cli
from evalrepro.adapters.base import SnapshotSource


def test_parser_helpers() -> None:
    assert cli._fields("input, target") == ("input", "target")
    assert cli._json_object('{"x":1}') == {"x": 1}
    assert cli._positive_limit("2") == 2

    with pytest.raises(argparse.ArgumentTypeError, match="At least one"):
        cli._fields(" , ")
    with pytest.raises(argparse.ArgumentTypeError, match="unique"):
        cli._fields("input,input")
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid JSON"):
        cli._json_object("bad")
    with pytest.raises(argparse.ArgumentTypeError, match="JSON object"):
        cli._json_object("[]")
    with pytest.raises(argparse.ArgumentTypeError, match="greater than zero"):
        cli._positive_limit("0")


def test_cli_inspect_snapshot_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = SnapshotSource(
        adapter="inspect-ai",
        identity={"task": "fake"},
        parameters={},
        records=[{"id": "1", "input": "x"}],
        declared_count=1,
    )
    monkeypatch.setattr(cli, "inspect_source", lambda *args, **kwargs: source)
    output = tmp_path / "inspect.json"

    assert cli.main(["snapshot", "inspect", "module:task", "-o", str(output)]) == 0
    assert output.exists()


def test_entrypoint_raises_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "main", lambda: 7)
    with pytest.raises(SystemExit) as exc:
        cli.entrypoint()
    assert exc.value.code == 7
