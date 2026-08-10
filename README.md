# EvalRepro

[![CI](https://github.com/seva9523/EvalRepro/actions/workflows/ci.yml/badge.svg)](https://github.com/seva9523/EvalRepro/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/evalrepro?include_prereleases&label=PyPI)](https://pypi.org/project/evalrepro/)
[![Python](https://img.shields.io/pypi/pyversions/evalrepro)](https://pypi.org/project/evalrepro/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Project status: public alpha](https://img.shields.io/badge/status-public%20alpha-orange.svg)](ROADMAP.md)

**Detect semantic drift in AI evaluation inputs and contracts before it silently changes benchmark results.**

An evaluation can keep importing and its tests can stay green while a dependency, dataset revision,
task configuration, or adapter changes sample membership, ordering, targets, choices, metadata, or
types. EvalRepro creates hash-only manifests in isolated environments and compares the evaluation
contract rather than relying on import success alone.

```text
dependency / dataset / config change
                 ↓
       create two manifests
                 ↓
     compare scope + coverage +
     samples + semantic fields
                 ↓
reproducible | order drift | semantic drift
```

> **Status:** public alpha. The manifest schema and adapter API may change before v1. Raw evaluation
> records are never written to a manifest, but hashes are not anonymisation; review the privacy notes
> before publishing manifests from sensitive datasets.

## What EvalRepro checks

- evaluation identity, task version, adapter parameters, and selected semantic fields;
- complete versus partial coverage and declared/processed sample counts;
- ordered and unordered sample digests;
- `input`, `target`, `choices`, and `metadata` digests by default;
- top-level field type distributions;
- added/removed sample hashes and the first ordered mismatch;
- runtime and source provenance without treating dependency versions as semantic scope.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `reproducible` | Scope, coverage, sample content/order, field digests, and types match. |
| `order_drift` | The same records remain, but their order changed. |
| `semantic_drift` | Record content, semantic fields, membership, or types changed. |
| `coverage_mismatch` | The manifests cover different ranges or completeness levels. |
| `scope_mismatch` | The manifests describe different tasks, parameters, or fields. |

## Install

Install the public alpha from PyPI:

```bash
python -m pip install "evalrepro==0.1.0a1"
```

For the optional Inspect adapter:

```bash
python -m pip install "evalrepro[inspect]==0.1.0a1"
```

To install the same immutable release directly from source:

```bash
python -m pip install \
  "evalrepro @ git+https://github.com/seva9523/EvalRepro.git@v0.1.0a1"
```

## Quick start: JSONL

Create one JSON object per line:

```json
{"id":"1","input":"What is 2+2?","target":"4","metadata":{"split":"test"}}
```

Snapshot the baseline and candidate:

```bash
evalrepro snapshot jsonl baseline.jsonl --name arithmetic-v1 -o baseline.manifest.json
evalrepro snapshot jsonl candidate.jsonl --name arithmetic-v1 -o candidate.manifest.json
```

If sample IDs should not appear in a published manifest, add `--no-id-preview` to either snapshot
command. The IDs still contribute to the sample digests, so this changes the diagnostic presentation
only.

Compare them:

```bash
evalrepro compare baseline.manifest.json candidate.manifest.json \
  --json report.json \
  --markdown report.md
```

Exit codes are `0` for a reproducible comparison, `2` for detected drift/mismatch, and `3` for an
invalid source or manifest.

## Quick start: Inspect AI

Run the same task in two isolated environments:

```bash
evalrepro snapshot inspect inspect_evals.bbq.bbq:bbq \
  --kwargs '{"subsets":"Age"}' \
  -o artifacts/datasets-4.8.5.json
```

Repeat under the candidate dependency version, then compare the manifests. Inspect message IDs are
removed by the adapter because they are runtime-generated rather than evaluation semantics. Local
image content is represented by a content digest instead of an environment-specific path.

## GitHub Action

Use the immutable public-alpha tag:

```yaml
- uses: seva9523/EvalRepro@v0.1.0a1
  with:
    baseline: artifacts/baseline.json
    candidate: artifacts/candidate.json
    report-json: artifacts/evalrepro-report.json
    report-markdown: artifacts/evalrepro-report.md
    fail-on-drift: "true"
```

The Markdown report is appended to the GitHub Actions job summary.

## Founding case study

EvalRepro grew out of a dependency investigation for `UKGovernmentBEIS/inspect_evals#2049`. A
fork-side matrix compared Hugging Face `datasets==4.8.5` and `datasets==5.0.1` across seven complete
Inspect datasets and **22,773 records**. The tested sample membership, ordering, inputs, targets,
choices, metadata, types, task scope, and provenance matched exactly. The case study is documented in
[`case-studies/inspect-datasets-5.md`](case-studies/inspect-datasets-5.md). Its status is explicitly
recorded as **fork-validated**, not upstream-accepted.

## Built-in adapters

- Generic JSON Lines
- Inspect AI / Inspect Evals (optional extra)
- Framework-neutral `SnapshotSource` API for custom adapters

Planned adapters are tracked in the [roadmap](ROADMAP.md). The most useful contributions are adapters
backed by a real reproducibility case, not thin wrappers added only to increase framework count.

## Contributing

External contributors are central to this project. There are three useful entry points:

1. submit a reproducibility case or bug report;
2. add fixtures, normalisers, reports, or platform tests;
3. propose and implement a framework adapter using the public adapter contract.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), the
[`Adapter specification`](docs/adapter-spec.md), and issues labelled
[`good first issue`](https://github.com/seva9523/EvalRepro/labels/good%20first%20issue) or
[`help wanted`](https://github.com/seva9523/EvalRepro/labels/help%20wanted).

## Non-goals

EvalRepro does not run or grade language models, replace evaluation frameworks, compare model quality,
or claim that matching inputs guarantee identical model outputs. It protects the **evaluation
contract and data path** so score changes can be interpreted with greater confidence.

## Security and privacy

Manifests contain hashes, compact ID previews by default, runtime details, and provenance. They do not
contain raw sample text. Hashes of small or predictable values can still be brute-forced and ID
previews can be sensitive. Use `--no-id-preview` when the preview should be omitted, and do not
publish manifests from confidential evaluations without reviewing the remaining fields. See
[`docs/privacy.md`](docs/privacy.md), [`SECURITY.md`](SECURITY.md), and [`METHODOLOGY.md`](METHODOLOGY.md).

## Licence

Apache-2.0. See [`LICENSE`](LICENSE).
