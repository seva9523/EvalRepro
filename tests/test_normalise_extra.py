from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

from evalrepro.normalise import NormalisationPolicy, normalise


class Colour(Enum):
    RED = "red"


@dataclass
class Record:
    value: int


class LegacyModel:
    def dict(self) -> dict[str, int]:
        return {"value": 3}


class PydanticLike:
    def model_dump(self, **kwargs: object) -> dict[str, object]:
        assert kwargs == {"mode": "json", "exclude_none": False}
        return {"value": 4}


class OldPydanticLike:
    def model_dump(self, **kwargs: object) -> dict[str, object]:
        if kwargs:
            raise TypeError("old signature")
        return {"value": 5}


class PublicObject:
    def __init__(self) -> None:
        self.visible = 6
        self._private = "ignore"


class NumpyScalar:
    __module__ = "numpy.fake"

    def item(self) -> int:
        return 7


def test_scalar_and_structured_special_types(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    value = normalise(
        {
            "decimal": Decimal("1.20"),
            "date": dt.date(2026, 8, 9),
            "time": dt.time(12, 30),
            "datetime": dt.datetime(2026, 8, 9, 12, 30, tzinfo=dt.UTC),
            "uuid": UUID("12345678-1234-5678-1234-567812345678"),
            "enum": Colour.RED,
            "path": path,
            "bytes": b"abc",
            "nan": math.nan,
            "positive_inf": math.inf,
            "negative_inf": -math.inf,
        }
    )

    assert value["decimal"] == {"__decimal__": "1.20"}
    assert value["enum"] == "red"
    assert value["path"] == {"__path__": path.as_posix()}
    assert value["bytes"] == {"__bytes_base64__": "YWJj"}
    assert value["nan"] == {"__float__": "NaN"}
    assert value["positive_inf"] == {"__float__": "Infinity"}
    assert value["negative_inf"] == {"__float__": "-Infinity"}


def test_model_dataclass_numpy_and_public_attribute_paths() -> None:
    assert normalise(Record(2)) == {"value": 2}
    assert normalise(LegacyModel()) == {"value": 3}
    assert normalise(PydanticLike()) == {"value": 4}
    assert normalise(OldPydanticLike()) == {"value": 5}
    assert normalise(NumpyScalar()) == 7
    assert normalise(PublicObject()) == {
        "__type__": f"{PublicObject.__module__}.{PublicObject.__qualname__}",
        "attributes": {"visible": 6},
    }


def test_image_policy_can_keep_path(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    image.write_bytes(b"content")

    value = normalise(
        {"type": "image", "image": str(image)},
        NormalisationPolicy(digest_local_content_files=False),
    )

    assert value["image"] == str(image)


def test_tuple_and_frozenset_normalise() -> None:
    assert normalise((1, 2)) == [1, 2]
    assert normalise(frozenset({"b", "a"})) == ["a", "b"]
