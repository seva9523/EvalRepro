"""Built-in evaluation-source adapters."""

from evalrepro.adapters.base import SnapshotSource
from evalrepro.adapters.jsonl import jsonl_source

__all__ = ["SnapshotSource", "jsonl_source"]
