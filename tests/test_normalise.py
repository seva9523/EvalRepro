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
