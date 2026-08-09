"""Project-specific exceptions."""

from __future__ import annotations


class EvalReproError(RuntimeError):
    """Base class for user-facing EvalRepro failures."""


class AdapterError(EvalReproError):
    """Raised when an evaluation source cannot be loaded safely."""


class ManifestError(EvalReproError):
    """Raised when a manifest is missing required or valid data."""


class NormalisationError(EvalReproError):
    """Raised when a value cannot be converted without losing meaning."""
