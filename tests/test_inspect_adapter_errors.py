from __future__ import annotations

from types import SimpleNamespace

import pytest

from evalrepro.adapters import inspect as inspect_adapter
from evalrepro.errors import AdapterError


def test_invalid_task_spec() -> None:
    with pytest.raises(AdapterError, match="must use"):
        inspect_adapter._load_symbol("invalid")


def test_import_and_symbol_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_import(_: str) -> object:
        raise ImportError("missing")

    monkeypatch.setattr(inspect_adapter.importlib, "import_module", fail_import)
    with pytest.raises(AdapterError, match="Cannot import"):
        inspect_adapter._load_symbol("missing.module:task")

    monkeypatch.setattr(
        inspect_adapter.importlib,
        "import_module",
        lambda _: SimpleNamespace(__name__="module", __file__=None),
    )
    with pytest.raises(AdapterError, match="has no symbol"):
        inspect_adapter._load_symbol("module:task")


def test_factory_and_dataset_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(__name__="module", __file__=None, value=1)
    monkeypatch.setattr(inspect_adapter.importlib, "import_module", lambda _: module)
    with pytest.raises(AdapterError, match="not callable"):
        inspect_adapter.inspect_source("module:value")

    def broken(**_: object) -> object:
        raise RuntimeError("boom")

    module.broken = broken
    with pytest.raises(AdapterError, match="could not be created"):
        inspect_adapter.inspect_source("module:broken")

    module.no_dataset = lambda: SimpleNamespace()
    with pytest.raises(AdapterError, match="does not expose"):
        inspect_adapter.inspect_source("module:no_dataset")

    module.non_iterable = lambda: SimpleNamespace(dataset=object())
    with pytest.raises(AdapterError, match="not iterable"):
        inspect_adapter.inspect_source("module:non_iterable")


def test_dot_task_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(
        __name__="module", __file__=None, task=lambda: SimpleNamespace(dataset=[])
    )
    monkeypatch.setattr(inspect_adapter.importlib, "import_module", lambda name: module)

    loaded_module, symbol = inspect_adapter._load_symbol("module.task")

    assert loaded_module is module
    assert symbol is module.task
