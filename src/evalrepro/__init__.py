"""Semantic reproducibility checks for AI evaluations."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("evalrepro")
except PackageNotFoundError:  # pragma: no cover - source checkout before installation
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
