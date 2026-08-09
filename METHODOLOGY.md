# Methodology

## Claim EvalRepro makes

Given two manifests produced from evaluation record streams, EvalRepro reports whether the selected
evaluation contract, coverage, sample membership/order, semantic fields, and top-level types agree.
It does **not** claim that identical manifests guarantee identical model outputs or scores.

## Comparison layers

### Scope

Scope contains the adapter, evaluation identity, task/adapter parameters, selected semantic fields,
and sample ID field. Runtime package versions and source commits are provenance, not scope: comparing
two different dependency versions is a primary use case.

### Coverage

A comparison is only meaningful when both manifests cover the same record range. Complete datasets
can match even when one run specified a limit larger than the dataset. Partial runs must use the same
limit and process the same count.

### Samples

Every normalised record is canonicalised to sorted, compact JSON and SHA-256 hashed. EvalRepro stores
an ordered sequence digest, an unordered sequence digest, and per-record hashes. The unordered digest
is computed over sorted hashes, retaining multiplicity.

### Semantic fields

For mapping-shaped records, each selected field is hashed separately in ordered and unordered form.
The defaults are `input`, `target`, `choices`, and `metadata`. A missing field is represented as JSON
`null`, so adding or removing a selected field changes its digest.

### Types

EvalRepro records counts of top-level value types. This catches changes such as a scalar target
becoming a list even where downstream stringification could hide the difference.

## Normalisation

Normalisation supports JSON primitives, non-finite floats, decimals, dates/times, UUIDs, enums,
paths, bytes, mappings, sequences, sets, dataclasses, Pydantic-style objects, NumPy scalars, and
objects with public attributes. Opaque values raise an error instead of falling back to `repr()`,
which may contain memory addresses or omit semantics.

Adapters may define narrowly scoped volatility policies. The Inspect adapter removes IDs from
message-shaped `{id, role, content}` objects because those IDs are generated at runtime. It does not
remove sample IDs. Local image paths are replaced with file-content digests where readable.

## Verdict precedence

1. `scope_mismatch`
2. `coverage_mismatch`
3. `semantic_drift`
4. `order_drift`
5. `reproducible`

This precedence prevents a coincidental sample hash match from being presented as reproducibility
when the tasks or coverage differ.

## Privacy and security limitations

- SHA-256 hashes are not anonymisation. Low-entropy values can be guessed and re-hashed.
- ID previews may expose identifiers.
- Runtime/platform and source metadata may reveal environment information.
- A malicious source can execute code before EvalRepro sees records; run untrusted adapters in an
  isolated environment.
- Manifest equality does not validate dataset licences, benchmark validity, scorer correctness, or
  the integrity of the upstream package index.

Future work includes optional keyed digests, configurable ID-preview suppression, signed cards, and
manifest attestations.
