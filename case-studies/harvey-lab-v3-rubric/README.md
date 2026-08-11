# Harvey LAB: firm-knowledge v3 rubric update

**Status:** EvalRepro workflow-validated; not upstream-reviewed or upstream-merged. No Harvey
adoption or endorsement is claimed.

## Question

Did Harvey LAB's firm-knowledge v3 rubric update change the selected evaluation contracts while task
coverage and the shared source-document corpus remained fixed?

## Pinned source revisions

| Role | Revision | Upstream change |
| --- | --- | --- |
| Baseline | `55510f0e609ffa5cf6f5df17d9a813ce4bb33d0c` | Adds the 250-task firm-knowledge benchmark |
| Candidate | `60071cc424d6479569626b8c76d90b958fe2d6c0` | Updates those tasks to the v3 rubric |

The candidate is the immediate child of the baseline. The public source comparison is
[`55510f0…60071cc`](https://github.com/harveyai/harvey-labs/compare/55510f0e609ffa5cf6f5df17d9a813ce4bb33d0c...60071cc424d6479569626b8c76d90b958fe2d6c0).

## Method

The workflow performs a blob-filtered sparse fetch of only `pyproject.toml` and
`tasks/firm-knowledge`, then runs EvalRepro adapter contract v1 over the selector
`firm-knowledge` at each immutable commit. It:

1. verifies that the candidate's parent is the baseline;
2. requires a clean checkout and exact commit provenance;
3. hashes the 250 task contracts and deduplicates the shared DMS inventory;
4. omits task-ID previews from both manifests;
5. compares scope, coverage, ordered/unordered task hashes, semantic fields, and types;
6. reports an aggregate changed-task count only after confirming the ordered task IDs match.

Run it from an EvalRepro source checkout after fetching both revisions into a local Harvey LAB
checkout:

```bash
python -m pip install -e .
python tools/harvey_lab_case_study.py \
  --repository /path/to/harvey-labs \
  --baseline 55510f0e609ffa5cf6f5df17d9a813ce4bb33d0c \
  --candidate 60071cc424d6479569626b8c76d90b958fe2d6c0 \
  --selector firm-knowledge \
  --output artifacts/harvey-lab-v3-rubric
```

The opt-in GitHub workflow is
[`harvey-lab-case-study.yml`](../../.github/workflows/harvey-lab-case-study.yml).

## Verified result

A verified [workflow run](https://github.com/seva9523/EvalRepro/actions/runs/31488789107)
completed successfully on Python 3.12 using EvalRepro `0.1.0a2`, manifest schema v1, and Harvey LAB
adapter contract v1.

| Evidence | Baseline | Candidate | Comparison |
| --- | ---: | ---: | --- |
| Pinned revision | `55510f0e…` | `60071cc4…` | Candidate is one commit ahead |
| Complete task contracts | 250 | 250 | Scope and coverage match |
| Shared DMS inventory | 9,288 files | 9,288 files | Exact digest match |
| Shared DMS bytes | 520,597,269 | 520,597,269 | Exact match |
| Changed task contracts | — | — | **250 of 250** |
| Changed semantic fields | — | — | `input`, `target` |
| Unchanged semantic fields | — | — | `choices`, `metadata` |
| Verdict | — | — | **`semantic_drift`** |

Top-level field types also matched. Both manifests were complete, came from clean exact-revision
checkouts, contained 250 ordered task hashes, and had empty task-ID previews.

## Published evidence

- [Stable machine-readable summary](results/summary.json)
- [Human-readable summary](results/summary.md)
- [Machine-readable comparison](results/comparison.json)
- [Markdown comparison report](results/comparison.md)
- [Baseline hash-only manifest](results/baseline.manifest.json)
- [Candidate hash-only manifest](results/candidate.manifest.json)

## Privacy and execution boundary

The run does not import Harvey LAB modules, install its dependencies, execute an agent, run a judge,
or call a model/provider API. Published manifests contain task hashes and aggregate provenance, not
raw instructions, rubrics, document paths, or document bytes. Hashes are not anonymisation; this
case uses Harvey LAB's public synthetic benchmark only.

The semantic summary and comparison values were reproduced in separate workflow runs. The committed
stable summary intentionally excludes runtime-specific Python/platform fields. Any later Harvey
outreach should ask for semantic review of this concrete method and result, not promotion.

## Limitations

- Task-contract drift does not establish whether the candidate rubric is better or worse.
- Matching source-document inventories do not guarantee identical agent or judge outputs.
- The result applies only to the pinned revisions and `firm-knowledge` selector.
- Until a Harvey maintainer reviews it, this is project-generated evidence, not upstream validation.
