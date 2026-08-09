"""Human-readable comparison reports."""

from __future__ import annotations

from evalrepro.compare import Comparison


def render_text(comparison: Comparison) -> str:
    lines = [
        f"EvalRepro verdict: {comparison.verdict.value}",
        f"Reproducible: {'yes' if comparison.reproducible else 'no'}",
        f"Scope match: {'yes' if comparison.scope_match else 'no'}",
        f"Coverage match: {'yes' if comparison.coverage_match else 'no'}",
        f"Ordered samples match: {'yes' if comparison.ordered_samples_match else 'no'}",
        f"Unordered samples match: {'yes' if comparison.unordered_samples_match else 'no'}",
        f"Top-level types match: {'yes' if comparison.top_level_types_match else 'no'}",
        f"Added sample hashes: {comparison.added_sample_hashes}",
        f"Removed sample hashes: {comparison.removed_sample_hashes}",
    ]
    for field, matches in comparison.field_matches.items():
        lines.append(
            f"Field {field}: ordered={'yes' if matches['ordered'] else 'no'}, "
            f"unordered={'yes' if matches['unordered'] else 'no'}"
        )
    if comparison.first_ordered_mismatch is not None:
        lines.append(f"First ordered mismatch: {comparison.first_ordered_mismatch}")
    if comparison.notes:
        lines.append("Notes:")
        lines.extend(f"- {note}" for note in comparison.notes)
    return "\n".join(lines) + "\n"


def render_markdown(comparison: Comparison) -> str:
    status = "✅" if comparison.reproducible else "❌"
    lines = [
        f"# EvalRepro report: {status} `{comparison.verdict.value}`",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Scope | {'match' if comparison.scope_match else 'mismatch'} |",
        f"| Coverage | {'match' if comparison.coverage_match else 'mismatch'} |",
        f"| Ordered samples | {'match' if comparison.ordered_samples_match else 'mismatch'} |",
        f"| Unordered samples | {'match' if comparison.unordered_samples_match else 'mismatch'} |",
        f"| Top-level types | {'match' if comparison.top_level_types_match else 'mismatch'} |",
        f"| Added sample hashes | {comparison.added_sample_hashes} |",
        f"| Removed sample hashes | {comparison.removed_sample_hashes} |",
        "",
        "## Semantic fields",
        "",
        "| Field | Ordered | Unordered |",
        "| --- | --- | --- |",
    ]
    for field, matches in comparison.field_matches.items():
        lines.append(
            f"| `{field}` | {'match' if matches['ordered'] else 'mismatch'} | "
            f"{'match' if matches['unordered'] else 'mismatch'} |"
        )
    if comparison.notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in comparison.notes)
    return "\n".join(lines) + "\n"
