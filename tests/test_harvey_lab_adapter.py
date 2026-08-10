from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import evalrepro.adapters.harvey_lab as adapter
from evalrepro.adapters.harvey_lab import harvey_lab_source
from evalrepro.compare import Verdict, compare_manifest_data
from evalrepro.errors import AdapterError
from evalrepro.manifest import build_manifest


def write_task(
    root: Path,
    task_id: str,
    *,
    instruction: str = "Review the contract.",
    fallback: bool = False,
    document_name: str = "source.txt",
    document_bytes: bytes = b"alpha",
    extra: dict[str, object] | None = None,
    docs_dir: str | None = None,
) -> Path:
    task_dir = root / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    effective_docs = (task_dir / (docs_dir or "documents")).resolve()
    effective_docs.mkdir(parents=True, exist_ok=True)
    (effective_docs / document_name).write_bytes(document_bytes)

    config: dict[str, Any] = {
        "title": "Contract review",
        "instructions": "" if fallback else instruction,
        "work_type": "review",
        "tags": ["contracts"],
        "deliverables": {"report.docx": "report.docx"},
        "criteria": [
            {
                "id": "C-001",
                "title": "Find issue",
                "match_criteria": "PASS if issue found",
                "deliverables": ["report.docx"],
                "sources": [document_name],
            }
        ],
    }
    if docs_dir is not None:
        config["docs_dir"] = docs_dir
    if extra:
        config.update(extra)
    (task_dir / "task.json").write_text(json.dumps(config), encoding="utf-8")
    if fallback:
        (task_dir / "instructions.md").write_text(instruction, encoding="utf-8")
    return task_dir


def manifest(
    root: Path,
    selector: str = "all",
    *,
    preview: bool = True,
) -> dict[str, Any]:
    return build_manifest(
        harvey_lab_source(root, task=selector),
        include_id_preview=preview,
    )


def test_all_tasks_are_sorted_hash_only_and_fallback_matches_inline(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    write_task(left, "zeta/task-2", instruction="Same instructions", fallback=True)
    write_task(left, "alpha/task-1", instruction="Inline")
    write_task(right, "zeta/task-2", instruction="Same instructions")
    write_task(right, "alpha/task-1", instruction="Inline")

    left_manifest = manifest(left)
    right_manifest = manifest(right)

    assert left_manifest["samples"]["id_preview"]["first"] == [
        "alpha/task-1",
        "zeta/task-2",
    ]
    assert compare_manifest_data(left_manifest, right_manifest).verdict is Verdict.REPRODUCIBLE
    source = harvey_lab_source(left)
    records = list(source.records)
    inventory = records[0]["metadata"]["source_documents"]
    assert inventory["count"] == 1
    assert inventory["total_bytes"] == len(b"alpha")
    assert len(inventory["ordered_digest"]) == 64
    dumped = json.dumps(left_manifest)
    assert "Same instructions" not in dumped
    assert "PASS if issue found" not in dumped
    assert "alpha/task-1" in dumped


def test_exact_prefix_and_missing_selector(tmp_path: Path) -> None:
    write_task(tmp_path, "corporate-ma/task-a")
    write_task(tmp_path, "corporate-ma/task-b")
    write_task(tmp_path, "real-estate/task-c")

    prefix = manifest(tmp_path, "corporate-ma")
    exact = manifest(tmp_path, "real-estate/task-c")

    assert prefix["coverage"]["processed_count"] == 2
    assert exact["samples"]["id_preview"]["first"] == ["real-estate/task-c"]
    with pytest.raises(AdapterError, match="No Harvey LAB tasks matched"):
        harvey_lab_source(tmp_path, task="missing")


def test_checkout_location_and_git_metadata_do_not_affect_verdict(tmp_path: Path) -> None:
    left = tmp_path / "checkout-a"
    right = tmp_path / "nested" / "checkout-b"
    write_task(left, "contracts/task-a")
    shutil.copytree(left, right)

    result = compare_manifest_data(manifest(left), manifest(right))

    assert result.verdict is Verdict.REPRODUCIBLE


def test_semantic_mutations_are_detected(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    write_task(baseline, "contracts/task-a")

    instruction = tmp_path / "instruction"
    write_task(instruction, "contracts/task-a", instruction="Different")

    document = tmp_path / "document"
    write_task(document, "contracts/task-a", document_bytes=b"different")

    moved = tmp_path / "moved"
    write_task(moved, "contracts/task-a", document_name="renamed.txt")

    criterion = tmp_path / "criterion"
    criterion_dir = write_task(criterion, "contracts/task-a")
    criterion_path = criterion_dir / "task.json"
    criterion_config = json.loads(criterion_path.read_text())
    criterion_config["criteria"][0]["match_criteria"] = "Changed rubric"
    criterion_path.write_text(json.dumps(criterion_config))

    unknown = tmp_path / "unknown"
    write_task(unknown, "contracts/task-a", extra={"judge_policy": "strict"})

    for candidate in (instruction, document, moved, criterion, unknown):
        result = compare_manifest_data(manifest(baseline), manifest(candidate))
        assert result.verdict is Verdict.SEMANTIC_DRIFT


def test_task_addition_is_coverage_mismatch_and_selector_is_scope(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    write_task(baseline, "contracts/task-a")
    shutil.copytree(baseline, candidate)
    write_task(candidate, "contracts/task-b")

    added = compare_manifest_data(manifest(baseline), manifest(candidate))
    scoped = compare_manifest_data(
        manifest(candidate, "all"),
        manifest(candidate, "contracts/task-a"),
    )

    assert added.verdict is Verdict.COVERAGE_MISMATCH
    assert scoped.verdict is Verdict.SCOPE_MISMATCH


def test_equivalent_docs_dir_spelling_is_reproducible(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    write_task(left, "contracts/task-a")
    write_task(right, "contracts/task-a", docs_dir="./documents")

    assert compare_manifest_data(manifest(left), manifest(right)).verdict is Verdict.REPRODUCIBLE


def test_no_id_preview_preserves_hashes(tmp_path: Path) -> None:
    write_task(tmp_path, "contracts/private-task")

    visible = manifest(tmp_path)
    hidden = manifest(tmp_path, preview=False)

    assert hidden["samples"]["id_preview"] == {"first": [], "last": []}
    assert hidden["samples"]["ordered_hashes"] == visible["samples"]["ordered_hashes"]


def test_errors_are_precise(tmp_path: Path) -> None:
    with pytest.raises(AdapterError, match="tasks directory not found"):
        harvey_lab_source(tmp_path)

    root = tmp_path / "repo"
    task_dir = write_task(root, "contracts/task-a")
    config_path = task_dir / "task.json"
    config_path.write_text("not-json")
    with pytest.raises(AdapterError, match="Invalid JSON"):
        harvey_lab_source(root)

    config_path.write_text(
        json.dumps(
            {
                "title": "x",
                "instructions": "",
                "criteria": [{"id": "C", "title": "t", "match_criteria": "m"}],
            }
        )
    )
    with pytest.raises(AdapterError, match="No readable instructions"):
        harvey_lab_source(root)


def test_docs_dir_escape_and_symlink_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    task_dir = root / "tasks/contracts/task-a"
    task_dir.mkdir(parents=True)
    config = {
        "title": "x",
        "instructions": "y",
        "docs_dir": "../../../../outside",
        "criteria": [{"id": "C", "title": "t", "match_criteria": "m"}],
    }
    (task_dir / "task.json").write_text(json.dumps(config))
    with pytest.raises(AdapterError, match="escapes repository root"):
        harvey_lab_source(root)

    root2 = tmp_path / "repo2"
    task = write_task(root2, "contracts/task-a")
    document = task / "documents/source.txt"
    document.unlink()
    document.symlink_to(outside / "secret.txt")
    with pytest.raises(AdapterError, match="symbolic links"):
        harvey_lab_source(root2)


def test_git_provenance_is_versioned_sanitised_and_non_semantic(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_task(root, "contracts/task-a")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "harvey-labs"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://user:secret@example.com:8443/harveyai/harvey-labs.git?token=hidden#fragment",
        ],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "tag", "v0.1.0"], cwd=root, check=True)

    clean = manifest(root)
    provenance = clean["provenance"]
    assert provenance["harvey_lab_version"] == "0.1.0"
    assert provenance["repository_origin"] == ("https://example.com:8443/harveyai/harvey-labs.git")
    assert provenance["git_tags"] == ["v0.1.0"]
    assert provenance["git_dirty"] is False
    assert len(provenance["git_commit"]) == 40

    (root / "untracked.txt").write_text("local work", encoding="utf-8")
    dirty = manifest(root)
    assert dirty["provenance"]["git_dirty"] is True
    assert dirty["provenance"]["git_status_digest"] != provenance["git_status_digest"]
    assert compare_manifest_data(clean, dirty).verdict is Verdict.REPRODUCIBLE


def test_shared_document_inventory_is_hashed_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    write_task(root, "contracts/task-a", docs_dir="../../shared")
    write_task(root, "contracts/task-b", docs_dir="../../shared")
    original = adapter._file_digest
    calls = 0

    def counting_digest(path: Path) -> tuple[int, str]:
        nonlocal calls
        calls += 1
        return original(path)

    monkeypatch.setattr(adapter, "_file_digest", counting_digest)
    source = harvey_lab_source(root)

    assert source.declared_count == 2
    assert calls == 1


def test_config_field_validation_errors(tmp_path: Path) -> None:
    mutations: list[tuple[str, object, str]] = [
        ("title", "", "title must be a non-empty string"),
        ("instructions", 7, "instructions must be a string"),
        ("work_type", 7, "work_type must be a string"),
        ("tags", "contracts", "tags must be a list of strings"),
        ("deliverables", [], "deliverables must be an object"),
        ("docs_dir", 7, "docs_dir must be a string"),
        ("criteria", [], "criteria must be a non-empty list"),
    ]
    for index, (field, value, match) in enumerate(mutations):
        root = tmp_path / f"case-{index}"
        task_dir = write_task(root, "contracts/task-a")
        config_path = task_dir / "task.json"
        config = json.loads(config_path.read_text())
        config[field] = value
        config_path.write_text(json.dumps(config))
        with pytest.raises(AdapterError, match=match):
            harvey_lab_source(root)


def test_criterion_and_fallback_validation_errors(tmp_path: Path) -> None:
    root = tmp_path / "criterion"
    task_dir = write_task(root, "contracts/task-a")
    config_path = task_dir / "task.json"
    config = json.loads(config_path.read_text())
    config["criteria"] = ["bad"]
    config_path.write_text(json.dumps(config))
    with pytest.raises(AdapterError, match="criterion 0 must be an object"):
        harvey_lab_source(root)

    root2 = tmp_path / "criterion-fields"
    task_dir2 = write_task(root2, "contracts/task-a")
    config_path2 = task_dir2 / "task.json"
    config2 = json.loads(config_path2.read_text())
    config2["criteria"][0]["deliverables"] = "report.docx"
    config_path2.write_text(json.dumps(config2))
    with pytest.raises(AdapterError, match="criterion 0 deliverables must be a list"):
        harvey_lab_source(root2)

    root3 = tmp_path / "blank-fallback"
    task_dir3 = write_task(root3, "contracts/task-a", fallback=True)
    (task_dir3 / "instructions.md").write_text("   ")
    with pytest.raises(AdapterError, match="instructions must be non-empty"):
        harvey_lab_source(root3)


def test_path_and_source_safety_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "absolute"
    task_dir = write_task(root, "contracts/task-a")
    config_path = task_dir / "task.json"
    config = json.loads(config_path.read_text())
    config["docs_dir"] = str((task_dir / "documents").resolve())
    config_path.write_text(json.dumps(config))
    with pytest.raises(AdapterError, match="docs_dir must be relative"):
        harvey_lab_source(root)

    root2 = tmp_path / "single"
    write_task(root2, "task-a")
    with pytest.raises(AdapterError, match="at least two path segments"):
        harvey_lab_source(root2)

    source_file = tmp_path / "not-a-directory"
    source_file.write_text("x")
    with pytest.raises(AdapterError, match="is not a directory"):
        harvey_lab_source(source_file)

    with pytest.raises(AdapterError, match="selector must not be empty"):
        harvey_lab_source(root2, task=" / ")

    root_windows = tmp_path / "windows-absolute"
    task_windows = write_task(root_windows, "contracts/task-a")
    config_windows_path = task_windows / "task.json"
    config_windows = json.loads(config_windows_path.read_text())
    config_windows["docs_dir"] = r"C:\outside"
    config_windows_path.write_text(json.dumps(config_windows))
    with pytest.raises(AdapterError, match="docs_dir must be relative"):
        harvey_lab_source(root_windows)

    root_tasks_link = tmp_path / "tasks-link"
    holder = tmp_path / "holder"
    write_task(holder, "contracts/task-a")
    actual_tasks = tmp_path / "actual-tasks"
    (holder / "tasks").rename(actual_tasks)
    root_tasks_link.mkdir()
    (root_tasks_link / "tasks").symlink_to(actual_tasks, target_is_directory=True)
    with pytest.raises(AdapterError, match="tasks directory must not be a symbolic link"):
        harvey_lab_source(root_tasks_link)

    root3 = tmp_path / "unreadable"
    task_dir3 = write_task(root3, "contracts/task-a")
    document = task_dir3 / "documents/source.txt"
    original_open = Path.open

    def guarded_open(path: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if path == document:
            raise PermissionError("blocked")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(AdapterError, match="Cannot read Harvey LAB source document"):
        harvey_lab_source(root3)


def test_non_object_config_symlink_config_and_duplicate_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "non-object"
    task_dir = write_task(root, "contracts/task-a")
    config_path = task_dir / "task.json"
    config_path.write_text("[]")
    with pytest.raises(AdapterError, match="must contain a JSON object"):
        harvey_lab_source(root)

    root2 = tmp_path / "symlink-config"
    task_dir2 = root2 / "tasks/contracts/task-a"
    task_dir2.mkdir(parents=True)
    real_config = root2 / "real-task.json"
    real_config.write_text("{}")
    (task_dir2 / "task.json").symlink_to(real_config)
    with pytest.raises(AdapterError, match="task config must not use symbolic links"):
        harvey_lab_source(root2)

    root3 = tmp_path / "duplicate"
    task_dir3 = write_task(root3, "contracts/task-a")
    duplicate_config = task_dir3 / "task.json"
    original_rglob = Path.rglob

    def duplicate_rglob(path: Path, pattern: str):  # type: ignore[no-untyped-def]
        if path == root3 / "tasks" and pattern == "task.json":
            return iter([duplicate_config, duplicate_config])
        return original_rglob(path, pattern)

    monkeypatch.setattr(Path, "rglob", duplicate_rglob)
    with pytest.raises(AdapterError, match="Duplicate Harvey LAB task ID"):
        adapter._discover(root3.resolve(), "all")


def test_selector_canonicalisation_and_remote_sanitisation(tmp_path: Path) -> None:
    write_task(tmp_path, "contracts/task-a")

    windows_style = manifest(tmp_path, r"contracts\task-a")
    canonical = manifest(tmp_path, "./contracts/task-a/")

    assert compare_manifest_data(windows_style, canonical).verdict is Verdict.REPRODUCIBLE
    assert adapter._sanitise_remote("git@github.com:harveyai/harvey-labs.git") == (
        "github.com:harveyai/harvey-labs.git"
    )
    assert (
        adapter._sanitise_remote(
            "https://user:secret@example.com:invalid/harveyai/harvey-labs.git?token=x"
        )
        == "https://example.com/harveyai/harvey-labs.git"
    )
    assert adapter._sanitise_remote("https:///missing-host") is None

    with pytest.raises(AdapterError, match=r"must not contain '\.\.'"):
        harvey_lab_source(tmp_path, task="../contracts")
