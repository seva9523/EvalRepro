"""Stable JSON serialization and hashing helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize an already-normalised value deterministically."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    """Return a SHA-256 digest for an already-normalised value."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sequence_digest(hashes: Sequence[str]) -> str:
    """Hash an ordered sequence without ambiguous concatenation."""
    result = hashlib.sha256()
    for item_hash in hashes:
        result.update(item_hash.encode("ascii"))
        result.update(b"\n")
    return result.hexdigest()
