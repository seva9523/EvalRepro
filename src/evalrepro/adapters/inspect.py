"""Optional Inspect AI / Inspect Evals adapter."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import AdapterError
from evalrepro.normalise import NormalisationPolicy, normalise
from evalrepro.runtime import discover_git_root, git_state, runtime_versions


def _load_symbol(spec: str) -> tuple[Any, Any]:
    if ":" in spec:
        module_name, symbol_name = spec.split(":", 1)
    else:
        module_name, separator, symbol_name = spec.rpartition(".")
        if not separator:
            raise AdapterError(
                "Task must use 'package.module:function' or 'package.module.function'."
            )
    if not module_name or not symbol_name:
        raise AdapterError(f"Invalid task specification: {spec!r}")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise AdapterError(
            f"Cannot import {module_name!r}. Install the framework/task package first."
        ) from exc
    try:
        return module, getattr(module, symbol_name)
    except AttributeError as exc:
        raise AdapterError(f"Module {module_name!r} has no symbol {symbol_name!r}.") from exc


def inspect_source(
    task_spec: str,
    *,
    kwargs: dict[str, Any] | None = None,
    fields: tuple[str, ...] = ("input", "target", "choices", "metadata"),
    id_field: str | None = "id",
) -> SnapshotSource:
    """Materialise the dataset exposed by an Inspect task factory."""
    task_kwargs = kwargs or {}
    module, task_factory = _load_symbol(task_spec)
    if not callable(task_factory):
        raise AdapterError(f"Loaded symbol {task_spec!r} is not callable.")
    try:
        task = task_factory(**task_kwargs)
    except Exception as exc:
        raise AdapterError(f"Inspect task {task_spec!r} could not be created: {exc}") from exc

    dataset = getattr(task, "dataset", None)
    if dataset is None:
        raise AdapterError(f"Inspect task {task_spec!r} does not expose a dataset.")
    try:
        iter(dataset)
    except TypeError as exc:
        dataset_type = type(dataset).__name__
        raise AdapterError(f"Inspect dataset type {dataset_type!r} is not iterable.") from exc

    try:
        declared_count = len(dataset)
    except (TypeError, AttributeError):
        declared_count = None

    module_file = getattr(module, "__file__", None)
    root = discover_git_root(Path(module_file)) if module_file else None
    task_metadata = normalise(
        getattr(task, "metadata", None),
        NormalisationPolicy(drop_message_ids=True),
    )

    return SnapshotSource(
        adapter="inspect-ai",
        identity={
            "task_spec": task_spec,
            "task_name": getattr(task, "name", None),
            "dataset_name": getattr(dataset, "name", None),
        },
        parameters={
            "kwargs": normalise(task_kwargs),
            "task_version": getattr(task, "version", None),
            "task_metadata": task_metadata,
        },
        records=dataset,
        declared_count=declared_count,
        fields=fields,
        id_field=id_field,
        runtime=runtime_versions(("inspect-ai", "inspect-evals", "datasets")),
        provenance={
            "module": module.__name__,
            **git_state(root),
        },
        normalisation_policy=NormalisationPolicy(drop_message_ids=True),
    )
