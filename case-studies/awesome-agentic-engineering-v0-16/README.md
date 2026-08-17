# Awesome Agentic Engineering: v0.16 workflow pin hardening

**Status:** Public design-partner case submitted independently and reproduced with EvalRepro's
case-study script. A pinned GitHub workflow is included for repeat validation. This is not a claim
of project adoption or endorsement.

## Question

Did the `v0.15.0` to `v0.16.0` release boundary change only the three selected generated workflows,
while the selected Agent Cards, prompt-injection fixture pack, and Agent Card Schema stayed fixed?

## Pinned source revisions

| Role | Revision | Release |
| --- | --- | --- |
| Baseline | `d3bafb19c06bd493b43188675cf7b7fd4dbf3065` | `v0.15.0` |
| Candidate | `7edabb8a76a225fd035b13f33f0b997c03175016` | `v0.16.0` |

The baseline is an ancestor of the candidate. The public comparison is
[`d3bafb1…7edabb8`](https://github.com/lindixu6-hash/awesome-agentic-engineering/compare/d3bafb19c06bd493b43188675cf7b7fd4dbf3065...7edabb8a76a225fd035b13f33f0b997c03175016).

## Contract and method

The contributor who maintains the source repository proposed an eight-file public contract in
[EvalRepro issue #11](https://github.com/seva9523/EvalRepro/issues/11). The selected contract contains:

- three profile-specific Agent Cards;
- three generated `agent-readiness.yml` workflows;
- `evals/prompt-injection/fixtures.jsonl`;
- `schema/agent-card.schema.json`.

The case-study script reads each file directly from both immutable git revisions without checking
out either revision. Each record contains the public path, artifact kind, and a SHA-256 digest of the
file bytes. EvalRepro then builds manifests with ID previews disabled and compares identical scope,
ordering, and complete eight-file coverage.

Run from an EvalRepro checkout after fetching both revisions into a local source checkout:

```bash
python -m pip install -e .
python tools/agentic_engineering_case_study.py \
  --repository /path/to/awesome-agentic-engineering \
  --baseline d3bafb19c06bd493b43188675cf7b7fd4dbf3065 \
  --candidate 7edabb8a76a225fd035b13f33f0b997c03175016 \
  --output artifacts/awesome-agentic-engineering-v0-16
```

The opt-in workflow is
[`agentic-engineering-case-study.yml`](../../.github/workflows/agentic-engineering-case-study.yml).

## Reproduced result

| Evidence | Baseline | Candidate | Comparison |
| --- | ---: | ---: | --- |
| Selected public artifacts | 8 | 8 | Scope, coverage, and order match |
| Agent Cards | 3 | 3 | Exact blob match |
| Prompt-injection fixture pack | 1 | 1 | Exact blob match |
| Agent Card Schema | 1 | 1 | Exact blob match |
| Generated workflows | 3 | 3 | All three changed |
| Changed semantic field | — | — | `input` (file-content digest) |
| Verdict | — | — | **`semantic_drift`** |

The three changed paths are:

- `starters/read-only/agent-readiness.yml`;
- `starters/draft-only/agent-readiness.yml`;
- `starters/state-changing/agent-readiness.yml`.

This matches the source maintainer's stated release intent: replace mutable `actions/checkout@v7`
references in all three generated workflows with the reviewed v7.0.1 commit SHA.

## Published evidence

- [Stable machine-readable summary](results/summary.json)
- [Human-readable summary](results/summary.md)
- [Machine-readable comparison](results/comparison.json)
- [Markdown comparison report](results/comparison.md)
- [Baseline hash-only manifest](results/baseline.manifest.json)
- [Candidate hash-only manifest](results/candidate.manifest.json)

## Privacy and execution boundary

The selected files are public. Published manifests contain hashes and aggregate metadata, not file
contents or ID previews. The run does not execute the initializer, generated workflows, an agent, a
model, or a judge. Hashes are evidence of selected-byte equality or difference, not anonymisation.

## Limitations

- This is an eight-file release-contract comparison, not a complete repository diff.
- Byte equality does not prove equivalent runtime behaviour on every platform.
- The expected workflow change records supply-chain hardening; it does not rate release quality.
- Participation in this case study is not evidence of broader EvalRepro adoption or endorsement.
