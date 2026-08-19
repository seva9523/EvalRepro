from __future__ import annotations

from pathlib import Path

import pytest

from evalrepro.errors import NormalisationError
from evalrepro.hashing import digest
from evalrepro.normalise import NormalisationPolicy, normalise


def test_mapping_order_and_sets_are_stable() -> None:
    left = {"b": {3, 1, 2}, "a": [1, 2]}
    right = {"a": [1, 2], "b": {2, 3, 1}}

    assert normalise(left) == normalise(right)
    assert digest(normalise(left)) == digest(normalise(right))


def test_message_ids_can_be_removed_without_dropping_other_ids() -> None:
    policy = NormalisationPolicy(drop_message_ids=True)
    message = {"id": "volatile", "role": "user", "content": "hello"}
    sample = {"id": "sample-1", "input": message}

    value = normalise(sample, policy)

    assert value["id"] == "sample-1"
    assert "id" not in value["input"]


def test_local_image_content_uses_digest(tmp_path: Path) -> None:
    image = tmp_path / "image.bin"
    image.write_bytes(b"same-content")

    value = normalise({"type": "image", "image": str(image)})

    assert value["image"]["__local_file__"]["suffix"] == ".bin"
    assert len(value["image"]["__local_file__"]["sha256"]) == 64


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (r"C:\some\windows\path\file.bin", "C:/some/windows/path/file.bin"),
        (r"C:\some\windows\path\file.bin", r"C:\other\windows\path\file.bin"),
        (r"\\server\share\folder\file.bin", "//server/share/folder/file.bin"),
    ],
)
def test_windows_and_unc_path_strings_remain_path_sensitive(left: str, right: str) -> None:
    """Synthetic Windows and UNC strings should stay exact without depending on the host OS."""
    assert normalise({"path": left}) != normalise({"path": right})
    assert normalise({"path": left})["path"] == left


def test_same_content_local_files_different_paths_produce_same_digest(tmp_path: Path) -> None:
    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"same-content")
    right.write_bytes(b"same-content")

    left_value = normalise({"type": "image", "image": str(left)})
    right_value = normalise({"type": "image", "image": str(right)})

    assert (
        left_value["image"]["__local_file__"]["sha256"]
        == right_value["image"]["__local_file__"]["sha256"]
    )
    assert digest(left_value) == digest(right_value)


def test_different_file_bytes_produce_different_digests(tmp_path: Path) -> None:
    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"content-a")
    right.write_bytes(b"content-b")

    left_value = normalise({"type": "image", "image": str(left)})
    right_value = normalise({"type": "image", "image": str(right)})

    assert (
        left_value["image"]["__local_file__"]["sha256"]
        != right_value["image"]["__local_file__"]["sha256"]
    )
    assert digest(left_value) != digest(right_value)


def test_missing_or_unreadable_local_content_falls_back_to_original_path(
    monkeypatch, tmp_path: Path
) -> None:
    """A missing or unreadable local content path falls back to the original path value."""
    missing = tmp_path / "missing.bin"
    assert normalise({"type": "image", "image": str(missing)})["image"] == str(missing)

    unreadable = tmp_path / "unreadable.bin"
    unreadable.write_bytes(b"secret")
    monkeypatch.setattr(Path, "is_file", lambda self: self == unreadable)

    def raise_oserror(self, *args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "open", raise_oserror)
    assert normalise({"type": "image", "image": str(unreadable)})["image"] == str(unreadable)


def test_ordinary_metadata_paths_remain_path_sensitive() -> None:
    left = {"metadata": {"source": "a/b/c", "label": "same"}}
    right = {"metadata": {"source": "a/b/d", "label": "same"}}

    assert normalise(left) != normalise(right)
    assert normalise({"metadata": {"source": Path("a/b/c")}}) != normalise(
        {"metadata": {"source": Path("a/b/d")}}
    )


def test_cycle_raises_instead_of_silently_hashing_repr() -> None:
    value: list[object] = []
    value.append(value)

    with pytest.raises(NormalisationError, match="Cycle detected"):
        normalise(value)


def test_opaque_value_raises() -> None:
    class Opaque:
        __slots__ = ()

    with pytest.raises(NormalisationError, match="Cannot safely normalise"):
        normalise(Opaque())
