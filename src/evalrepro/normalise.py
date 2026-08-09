"""Convert evaluation records into stable, JSON-compatible values."""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from evalrepro.errors import NormalisationError


@dataclass(frozen=True, slots=True)
class NormalisationPolicy:
    """Adapter-level controls for removing known non-semantic volatility."""

    drop_message_ids: bool = False
    digest_local_content_files: bool = True


def _content_file(value: Any, policy: NormalisationPolicy) -> Any:
    if not policy.digest_local_content_files or not isinstance(value, str):
        return value

    path = Path(value)
    try:
        if not path.is_file():
            return value
        file_digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                file_digest.update(chunk)
    except OSError:
        return value

    return {
        "__local_file__": {
            "sha256": file_digest.hexdigest(),
            "suffix": path.suffix.lower(),
        }
    }


def _sort_key(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def normalise(
    value: Any,
    policy: NormalisationPolicy | None = None,
    _seen: set[int] | None = None,
) -> Any:
    """Return a stable JSON-compatible representation.

    Unsupported opaque values raise instead of silently hashing an unstable ``repr``.
    Adapters should convert framework-specific objects before they reach that point.
    """
    policy = policy or NormalisationPolicy()
    seen = _seen if _seen is not None else set()

    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "NaN"}
        if math.isinf(value):
            return {"__float__": "Infinity" if value > 0 else "-Infinity"}
        return value

    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}

    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return {f"__{type(value).__name__}__": value.isoformat()}

    if isinstance(value, UUID):
        return {"__uuid__": str(value)}

    if isinstance(value, Enum):
        return normalise(value.value, policy, seen)

    if isinstance(value, Path):
        return {"__path__": value.as_posix()}

    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"__bytes_base64__": base64.b64encode(bytes(value)).decode("ascii")}

    value_id = id(value)
    if value_id in seen:
        type_name = f"{type(value).__module__}.{type(value).__qualname__}"
        raise NormalisationError(f"Cycle detected while normalising {type_name}.")

    seen.add(value_id)
    try:
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            try:
                dumped = model_dump(mode="json", exclude_none=False)
            except TypeError:
                dumped = model_dump()
            if isinstance(dumped, dict) and dumped.get("type") == "image":
                dumped = {**dumped, "image": _content_file(dumped.get("image"), policy)}
            return normalise(dumped, policy, seen)

        legacy_dict = getattr(value, "dict", None)
        if callable(legacy_dict) and not isinstance(value, Mapping):
            try:
                return normalise(legacy_dict(), policy, seen)
            except TypeError:
                pass

        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return normalise(dataclasses.asdict(value), policy, seen)

        if isinstance(value, Mapping):
            mapped: Mapping[Any, Any] = value
            if policy.drop_message_ids and {"role", "content", "id"}.issubset(mapped):
                mapped = {key: item for key, item in mapped.items() if key != "id"}
            if mapped.get("type") == "image" and "image" in mapped:
                mapped = {**mapped, "image": _content_file(mapped.get("image"), policy)}
            return {
                str(key): normalise(item, policy, seen)
                for key, item in sorted(mapped.items(), key=lambda pair: str(pair[0]))
            }

        if isinstance(value, (list, tuple)):
            return [normalise(item, policy, seen) for item in value]

        if isinstance(value, (set, frozenset)):
            items = [normalise(item, policy, seen) for item in value]
            return sorted(items, key=_sort_key)

        item_method = getattr(value, "item", None)
        if callable(item_method) and type(value).__module__.startswith("numpy"):
            return normalise(item_method(), policy, seen)

        if hasattr(value, "__dict__"):
            public = {key: item for key, item in vars(value).items() if not key.startswith("_")}
            if public:
                return {
                    "__type__": f"{type(value).__module__}.{type(value).__qualname__}",
                    "attributes": normalise(public, policy, seen),
                }

        type_name = f"{type(value).__module__}.{type(value).__qualname__}"
        raise NormalisationError(
            f"Cannot safely normalise {type_name}. Add an adapter conversion rather than relying "
            "on a potentially unstable repr()."
        )
    finally:
        seen.discard(value_id)
