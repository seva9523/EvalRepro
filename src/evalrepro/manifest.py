"""Build, load, and validate privacy-conscious evaluation manifests."""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from evalrepro import __version__
from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import ManifestError
from evalrepro.hashing import digest, sequence_digest
from evalrepro.normalise import normalise

MANIFEST_SCHEMA_VERSION = 1


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, Mapping):
        return "object"
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _preview(values: Sequence[Any], width: int = 5) -> dict[str, list[Any]]:
    if len(values) <= width * 2:
        return {"first": list(values), "last": []}
    return {"first": list(values[:width]), "last": list(values[-width:])}


def build_manifest(source: SnapshotSource, sample_limit: int | None = None) -> dict[str, Any]:
    """Create a hash-only manifest from an adapter-provided record stream."""
    if sample_limit is not None and sample_limit <= 0:
        raise ManifestError("sample_limit must be a positive integer or None.")

    sample_hashes: list[str] = []
    sample_ids: list[Any] = []
    type_counts: dict[str, Counter[str]] = {}
    field_hashes: dict[str, list[str]] = {field: [] for field in source.fields}
    exhausted = True

    for index, sample in enumerate(source.records):
        if sample_limit is not None and index >= sample_limit:
            exhausted = False
            break

        value = normalise(sample, source.normalisation_policy)
        sample_hashes.append(digest(value))
        if isinstance(value, Mapping):
            sample_ids.append(value.get(source.id_field) if source.id_field else None)
            for key, item in value.items():
                type_counts.setdefault(str(key), Counter()).update([_type_name(item)])
            for field in source.fields:
                field_hashes[field].append(digest(value.get(field)))
        else:
            sample_ids.append(None)
            type_counts.setdefault("__sample__", Counter()).update([_type_name(value)])
            for field in source.fields:
                field_hashes[field].append(digest(None))

    processed_count = len(sample_hashes)
    complete = exhausted
    if source.declared_count is not None:
        complete = processed_count == source.declared_count

    scope = normalise(source.scope())
    provenance = normalise(source.provenance)
    runtime = normalise(source.runtime)
    type_summary = {
        key: dict(sorted(counter.items())) for key, counter in sorted(type_counts.items())
    }

    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "tool": {"name": "evalrepro", "version": __version__},
        "runtime": runtime,
        "scope": scope,
        "scope_digest": digest(scope),
        "provenance": provenance,
        "coverage": {
            "declared_count": source.declared_count,
            "processed_count": processed_count,
            "complete": complete,
            "sample_limit": sample_limit,
        },
        "samples": {
            "ordered_digest": sequence_digest(sample_hashes),
            "unordered_digest": sequence_digest(sorted(sample_hashes)),
            "ordered_hashes": sample_hashes,
            "id_preview": _preview(sample_ids),
            "top_level_type_summary": type_summary,
            "field_digests": {
                field: {
                    "ordered": sequence_digest(hashes),
                    "unordered": sequence_digest(sorted(hashes)),
                }
                for field, hashes in field_hashes.items()
            },
        },
    }


def validate_manifest(data: Any, *, source: str = "manifest") -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError(f"{source} must contain a JSON object.")
    if data.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            f"{source} uses unsupported manifest schema "
            f"{data.get('manifest_schema_version')!r}; expected {MANIFEST_SCHEMA_VERSION}."
        )

    required_objects: dict[str, tuple[str, ...]] = {
        "runtime": (),
        "scope": ("adapter", "identity", "parameters", "fields", "id_field"),
        "provenance": (),
        "coverage": ("declared_count", "processed_count", "complete", "sample_limit"),
        "samples": (
            "ordered_digest",
            "unordered_digest",
            "ordered_hashes",
            "id_preview",
            "top_level_type_summary",
            "field_digests",
        ),
    }
    for section, required_fields in required_objects.items():
        value = data.get(section)
        if not isinstance(value, dict):
            raise ManifestError(f"{source} is missing object {section!r}.")
        missing = [field for field in required_fields if field not in value]
        if missing:
            raise ManifestError(f"{source} is missing {section} fields: {', '.join(missing)}.")

    coverage = data["coverage"]
    hashes = data["samples"]["ordered_hashes"]
    if not isinstance(coverage["complete"], bool):
        raise ManifestError(f"{source} coverage.complete must be boolean.")
    if not isinstance(coverage["processed_count"], int) or coverage["processed_count"] < 0:
        raise ManifestError(f"{source} coverage.processed_count must be a non-negative integer.")
    if not isinstance(hashes, list) or not all(isinstance(item, str) for item in hashes):
        raise ManifestError(f"{source} samples.ordered_hashes must be a list of strings.")
    if len(hashes) != coverage["processed_count"]:
        raise ManifestError(
            f"{source} processed_count does not match the number of ordered sample hashes."
        )
    if data.get("scope_digest") != digest(data["scope"]):
        raise ManifestError(f"{source} scope_digest does not match scope content.")
    return data


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestError(f"Cannot read manifest {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid JSON manifest {path}: {exc}") from exc
    return validate_manifest(data, source=str(path))


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    validate_manifest(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
