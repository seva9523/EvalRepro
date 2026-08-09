# Verdict semantics

EvalRepro returns the first applicable verdict in a deliberate precedence order. A lower-level hash
match must not hide the fact that two manifests describe different tasks or different coverage.

## `scope_mismatch`

The adapter, evaluation identity, semantic parameters, selected fields, or ID field differ. Compare
these manifests only after confirming that the scope difference is intentional and compatible.

## `coverage_mismatch`

The manifests do not cover the same range: one may be complete while the other is partial, the
processed counts differ, or two partial runs use different limits. A coincidental match over the
shared prefix is not reported as reproducibility.

## `semantic_drift`

Sample membership/content, selected semantic field digests, or top-level type distributions changed.
This verdict does not decide whether the change is good or bad; it says benchmark results should not
be compared as though the evaluation contract were unchanged.

## `order_drift`

The same multiset of normalised records remains and unordered semantic field digests match, but the
order moved. This matters for limited runs, batching, caching, few-shot selection, and any evaluation
path that is not invariant to order.

## `reproducible`

Scope, coverage, ordered/unordered records, selected fields, and top-level types match under the
manifest schema and adapter policy. This is not a guarantee that models, scorers, random seeds, or
external services will produce identical outputs.

CLI exit codes are `0` for `reproducible`, `2` for any drift/mismatch verdict, and `3` for invalid
input or an adapter/manifest error. `--allow-drift` changes only the exit code, not the reported
verdict.
