from __future__ import annotations

from types import SimpleNamespace

from evalrepro.adapters import inspect as inspect_adapter
from evalrepro.manifest import build_manifest


class FakeTask:
    name = "fake-task"
    version = "1.2.3"
    metadata = {"purpose": "test"}
    dataset = [
        {
            "id": "sample-1",
            "input": {"id": "volatile-message", "role": "user", "content": "hello"},
            "target": "world",
        }
    ]


def fake_task(**kwargs: object) -> FakeTask:
    assert kwargs == {"mode": "demo"}
    return FakeTask()


def test_inspect_adapter_builds_framework_scope(monkeypatch: object) -> None:
    module = SimpleNamespace(__name__="fake.module", __file__=None, task=fake_task)
    monkeypatch.setattr(inspect_adapter.importlib, "import_module", lambda _: module)

    source = inspect_adapter.inspect_source("fake.module:task", kwargs={"mode": "demo"})
    manifest = build_manifest(source)

    assert manifest["scope"]["adapter"] == "inspect-ai"
    assert manifest["scope"]["parameters"]["task_version"] == "1.2.3"
    assert manifest["coverage"]["processed_count"] == 1
