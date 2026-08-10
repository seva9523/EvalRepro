# Changelog

All notable changes will be documented here. The format follows Keep a Changelog and the project
uses semantic versioning once the manifest and adapter contracts reach stability.

## [Unreleased]

### Added

- First-party Harvey LAB task-contract adapter and CLI for hash-only comparison of exact tasks,
  task-prefix selections, or complete local benchmark checkouts.
- Deterministic effective-instruction, rubric, deliverable, unknown-field, document-path, and
  document-content semantics for Harvey LAB adapter contract version 1.
- Credential-stripped Git provenance, shared-document inventory caching, `--no-id-preview`, and
  synthetic offline mutation coverage for the Harvey LAB workflow.

### Security

- Harvey LAB snapshots reject absolute or repository-escaping document roots and symbolic-link task,
  instruction, document-root, and source-file paths.

## [0.1.0a1] - 2026-08-10

### Added

- Hash-only manifest schema v1.
- Generic JSONL and optional Inspect AI adapters.
- Scope, coverage, ordering, semantic-field, membership, and type drift classification.
- Text, JSON, and Markdown reports with CI-friendly exit codes.
- Composite GitHub Action.
- Founding Inspect Evals dependency-reproducibility case study.
- `--no-id-preview` for JSONL and Inspect snapshots, contributed by
  [`@uuzzrm`](https://github.com/uuzzrm), so published manifests can omit diagnostic identifiers
  without weakening semantic drift detection.

### Validation

- Python 3.11, 3.12, and 3.13 CI.
- Ruff formatting and linting.
- Strict mypy checks.
- 54 offline tests and 96.22% branch coverage after the first external contribution.
- Source distribution and wheel builds.

[0.1.0a1]: https://github.com/seva9523/EvalRepro/releases/tag/v0.1.0a1
