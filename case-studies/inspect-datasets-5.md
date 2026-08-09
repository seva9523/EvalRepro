# Inspect Evals: `datasets` 4.8.5 → 5.0.1

**Status:** fork-validated; not yet upstream-accepted.

## Question

Could the Hugging Face `datasets` major-version change alter the records exposed by Inspect Evals
while normal import/path tests continued to pass?

## Method

Two isolated Python 3.12 environments installed the same Inspect Evals contribution revision with
`datasets==4.8.5` and `datasets==5.0.1`. Complete manifests compared sample count, ordered/unordered
membership, `input`, `target`, `choices`, `metadata`, top-level types, task scope/version/kwargs, and
source provenance. Focused tests and a mock-model smoke run supplemented the data comparison.

## Complete datasets checked

| Evaluation | Records | Result |
| --- | ---: | --- |
| BBQ — Age | 3,680 | Exact match |
| PIQA | 1,838 | Exact match |
| APPS — introductory | 1,000 | Exact match |
| MedQA | 1,273 | Exact match |
| MMMU — Math multiple choice | 29 | Exact match |
| SciKnowEval — biology literature QA | 14,838 | Exact match |
| V*Bench — attribute recognition | 115 | Exact match |
| **Total** | **22,773** | **Exact match** |

## Additional validation

- Comparator tests passed in both dependency environments.
- Repository quality gate, Ruff, and mypy passed in the fork-side validation workflow.
- No explicit `streaming=True` use was found under Inspect Evals source/package paths; this matters
  because Datasets 5 changed streaming shuffle behaviour.
- Representative candidate-version tests and a SciKnowEval mock-model smoke run passed.

## Evidence

- Upstream tracking issue: https://github.com/UKGovernmentBEIS/inspect_evals/issues/2049
- Contribution branch: https://github.com/seva9523/inspect_evals/tree/investigate/datasets-5-reproducibility
- Fork-side validation PR: https://github.com/seva9523/inspect_evals/pull/1
- Compared contribution revision: `3d9d1afdad953523b5869463456494761f2d06ae`

## Interpretation

The tested evaluation records were reproducible across these two dependency versions. This is not a
claim about every Inspect evaluation, model score, streaming workload, private/gated dataset, or
future revision. The result demonstrates why semantic manifests add information beyond import-only
compatibility checks.
