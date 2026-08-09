"""Adapter contract used by the manifest builder."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from evalrepro.normalise import NormalisationPolicy


@dataclass(slots=True)
class SnapshotSource:
    """Framework-neutral description of an evaluation record stream."""

    adapter: str
    identity: dict[str, Any]
    parameters: dict[str, Any]
    records: Iterable[Any]
    declared_count: int | None = None
    fields: tuple[str, ...] = ("input", "target", "choices", "metadata")
    id_field: str | None = "id"
    runtime: dict[str, str | None] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    normalisation_policy: NormalisationPolicy = field(default_factory=NormalisationPolicy)

    def scope(self) -> dict[str, Any]:
        """Return the comparison contract, excluding environment/provenance data."""
        return {
            "adapter": self.adapter,
            "identity": self.identity,
            "parameters": self.parameters,
            "fields": list(self.fields),
            "id_field": self.id_field,
        }
