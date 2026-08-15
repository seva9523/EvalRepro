# Promptfoo export adapter design

Status: proposed contract; implementation has not started

Tracking issue: [#10](https://github.com/seva9523/EvalRepro/issues/10)

Upstream project: [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo)

## Purpose

Promptfoo can export a stored evaluation without rerunning its providers:

```bash
promptfoo export eval <eval-id> --output evaluation.json
```

EvalRepro should compare two of those JSON exports without opening Promptfoo's database, importing
Promptfoo internals, contacting Promptfoo Cloud, executing configuration functions, or calling a
model or grader.

The first adapter contract answers one deliberately narrow question:

> Do two stored exports describe the same executed evaluation definition and test-by-prompt
> coverage?

Version 1 does **not** compare model responses, pass/fail outcomes, scores, grader reasoning, traces,
latency, cost, or token usage. A later result contract requires a separate design because operational
metrics and provider-generated output have different reproducibility semantics from an evaluation
definition.

## Inspected upstream contract

This proposal was checked against Promptfoo `main` at
[`ab84555c1b0ff74eca6b03abb7936ac9a0149242`](https://github.com/promptfoo/promptfoo/commit/ab84555c1b0ff74eca6b03abb7936ac9a0149242).

The relevant public implementation surfaces are:

- [`src/commands/export.ts`](https://github.com/promptfoo/promptfoo/blob/ab84555c1b0ff74eca6b03abb7936ac9a0149242/src/commands/export.ts),
  where `promptfoo export eval` loads a stored evaluation and calls `createOutputData()`;
- [`src/util/output.ts`](https://github.com/promptfoo/promptfoo/blob/ab84555c1b0ff74eca6b03abb7936ac9a0149242/src/util/output.ts),
  where `createOutputData()` produces the JSON export;
- [`src/types/index.ts`](https://github.com/promptfoo/promptfoo/blob/ab84555c1b0ff74eca6b03abb7936ac9a0149242/src/types/index.ts),
  where `OutputFile`, `EvaluateSummaryV2`, `EvaluateSummaryV3`, and `EvaluateResult` are
  defined.

The inspected `OutputFile` contains:

- `evalId`;
- `results`, using an `EvaluateSummaryV2` or `EvaluateSummaryV3` shape;
- the sanitized evaluation `config`;
- `shareableUrl`;
- optional export `metadata`, `vars`, `runtimeOptions`, `traces`, and `blobAssets`.

This is a source-compatible proposal, not an upstream stability guarantee. The adapter must validate
the export shape and fail closed when Promptfoo introduces an unsupported schema.

## Proposed CLI

```bash
evalrepro snapshot promptfoo evaluation.json \
  --name customer-support-regression \
  --mode definition \
  -o evaluation.manifest.json
```

Contract version 1 supports only `--mode definition`. The flag remains explicit so a future
`results` mode cannot silently change the meaning of an existing command.

`--name` is required. Stored `evalId` values are run identifiers and must not define semantic
identity; otherwise two intended baseline/candidate exports would always produce a scope mismatch.

The standard `--limit` and `--no-id-preview` options should retain their existing manifest
semantics.

## Accepted source

Version 1 accepts one local UTF-8 JSON file produced by `promptfoo export eval`.

It must:

1. require a top-level JSON object;
2. require `results.version` and explicitly support the tested v2/v3 summary shapes;
3. require an array of stored results;
4. require the definition fields needed for every canonical record;
5. reject duplicate canonical record IDs;
6. reject unsupported top-level or result shapes with a path-specific error;
7. reject non-finite numbers and values that cannot be represented by EvalRepro's canonical JSON
   policy;
8. never resolve `file://`, JavaScript, Python, Nunjucks, or provider references found inside the
   export.

YAML, JSONL, HTML, CSV, direct database access, Cloud URLs, and `--include-media` exports are out of
scope for contract version 1.

An export with non-empty `blobAssets` must fail with an actionable unsupported-media error rather
than hashing base64 media accidentally or ignoring an evaluation input.

## Canonical record identity

One EvalRepro record represents one executed test-case and prompt/provider combination.

A stable in-memory record ID is derived from a domain-separated SHA-256 digest of:

- the canonical test-case definition;
- Promptfoo `promptId`;
- the canonical prompt definition;
- provider ID and semantic provider configuration.

It must not use positional `testIdx` or `promptIdx` as identity. Positional indexes remain useful
for source ordering, but using them as identity would make a reorder look like content replacement
instead of `order_drift`.

It must not use `result.id`, `evalId`, `evaluationId`, or `traceId`; those identify stored runs
or telemetry rather than the test/prompt contract.

The digest exists only as the record ID and optional diagnostic preview. Raw prompt, variable, test,
assertion, or provider content is never copied into the manifest.

## Record contract

The exact field-level mapping will be locked by fixtures before implementation, but contract version
1 follows this shape:

```json
{
  "id": "<definition digest>",
  "input": {
    "prompt": "<canonical Promptfoo prompt object>",
    "vars": {"question": "..."},
    "provider": {"id": "...", "config": {}},
    "transform": "<if present>"
  },
  "target": {
    "assertions": [],
    "expected_output": "<if present>",
    "thresholds": {},
    "grader_configuration": {}
  },
  "choices": null,
  "metadata": {
    "test_description": "...",
    "test_options": {},
    "definition_extra": {}
  }
}
```

All values above exist only in memory before the normal manifest builder hashes the record and its
semantic fields.

### Fail-closed unknown fields

Definition-bearing fields that are not yet understood must not be silently removed. They should be
included in a canonical `definition_extra` mapping when their values are inert JSON data.

An unknown value that represents executable or opaque behaviour must produce an adapter error until
the contract defines how it is represented. A string such as a `file://` reference may be hashed as
a literal definition value, but the adapter must never open or execute it.

## Scope, provenance, and runtime

Semantic scope contains:

- adapter name `promptfoo-export`;
- adapter contract version;
- required user-supplied evaluation name;
- mode `definition`;
- semantic field mapping;
- record-identity policy;
- definition-extra and unsupported-media policies;
- complete or partial coverage selection.

The following belong in provenance rather than semantic scope:

- source export SHA-256;
- stored `evalId`;
- Promptfoo summary version;
- evaluation and export timestamps;
- source filename reduced to a non-sensitive basename only when diagnostics need it;
- whether optional trace or media sections were absent.

Runtime records, when available:

- `metadata.promptfooVersion`;
- `metadata.nodeVersion`;
- `metadata.platform`;
- `metadata.arch`.

Promptfoo package version is runtime, not scope, so two versions can be intentionally compared. The
adapter contract version prevents unlike normalisation policies from comparing as equivalent.

## Included definition semantics

Contract version 1 includes, when present:

- effective prompt objects and prompt IDs;
- provider IDs and semantic provider configuration;
- test variables;
- assertions, assertion thresholds, weights, transforms, and grader configuration;
- test descriptions, metadata, options, and definition-level tags;
- configuration that affects prompt rendering, filtering, repetition, or evaluated matrix coverage;
- the set and order of executed test-by-prompt definitions.

Generated or positional indexes may help reconstruct source order, but they are not semantic record
identity.

## Deliberately excluded result semantics

Contract version 1 excludes from the semantic record:

- provider responses and raw model output;
- `success`, `failureReason`, `score`, `namedScores`, and grading reasons;
- latency, cost, and token usage;
- errors produced during the run;
- traces and telemetry metadata;
- share URLs and authorship;
- stored result, evaluation, and trace identifiers;
- evaluation/export timestamps;
- aggregate run statistics.

These values are not declared non-semantic in general. They are excluded because version 1 compares
definitions only. A future `results` mode must increment the adapter contract and state which of
these values it compares.

## Coverage and ordering

The complete export result array defines the executed test-by-prompt matrix for version 1.

- the adapter preserves Promptfoo's stored result order;
- the canonical record ID is independent of that order;
- equal definitions in a different order should produce `order_drift`;
- a missing or added executed combination in two complete exports should produce
  `coverage_mismatch`;
- a definition mutation should produce `semantic_drift`;
- a different `--name`, mode, or adapter contract should produce `scope_mismatch`.

If the user applies `--limit`, the manifest is partial and uses the standard EvalRepro coverage
rules.

## Normalisation policy

The initial implementation may ignore only volatility demonstrated by Promptfoo's source contract
and fixtures:

| Source value | Version 1 treatment |
| --- | --- |
| `evalId`, `result.id`, `evaluationId`, `traceId` | provenance/excluded run identity |
| `results.timestamp`, `metadata.exportedAt`, `metadata.evaluationCreatedAt` | provenance |
| `metadata.promptfooVersion`, Node/platform/architecture | runtime |
| `shareableUrl`, `author` | excluded presentation/ownership |
| `testIdx`, `promptIdx` | ordering diagnostics, not record identity |
| prompts, vars, assertions, transforms, provider configuration | semantic |
| unknown inert definition fields | semantic `definition_extra` |
| unknown opaque/executable fields | fail closed |

Changing only an excluded generated value must compare as `reproducible`. No field may be dropped
merely because it makes two real exports differ.

## Privacy and safety

Promptfoo exports may contain confidential prompts, test data, model responses, grading reasons,
traces, or embedded media. EvalRepro's hash-only manifest does not make a private export safe to
share automatically.

The adapter must:

- read locally and perform no network or provider calls;
- never write raw prompts, variables, assertions, outputs, traces, or config values to a manifest;
- reject embedded media in version 1;
- support `--no-id-preview`;
- avoid putting the user-supplied path or raw definition values in normal success output;
- return JSON-path error locations without echoing the rejected value;
- document that hashes of small or predictable inputs can be brute-forced.

Users remain responsible for confidentiality, source licences, and organisational policy. Public
case studies must use a non-sensitive demo evaluation.

## Offline fixture and mutation matrix

Network-free synthetic fixtures must cover both supported summary shapes and the following
mutations:

| Mutation | Expected result |
| --- | --- |
| generated IDs/timestamps/author/share URL changed | `reproducible` |
| Promptfoo/Node/platform version changed, definition equal | `reproducible` |
| test or prompt order changed | `order_drift` |
| executed combination added or removed from complete export | `coverage_mismatch` |
| prompt text or prompt configuration changed | `semantic_drift` |
| vars or test metadata changed | `semantic_drift` |
| assertion, threshold, transform, or grader configuration changed | `semantic_drift` |
| provider ID or semantic provider configuration changed | `semantic_drift` |
| response, score, latency, cost, tokens, or trace changed alone | `reproducible` in definition mode |
| unknown inert definition field added | `semantic_drift` |
| unsupported summary shape, opaque value, or embedded media | adapter error, exit code 3 |

Fixtures must contain synthetic values only. The tests must not install or import Promptfoo, execute
template/config code, access a database, or require network/model credentials.

## Public case-study gate

Implementation is not complete until an opt-in workflow exercises one real, non-sensitive Promptfoo
demo export at two pinned Promptfoo versions or source revisions.

The case study must publish:

- exact Promptfoo and EvalRepro versions;
- the command that produced each export;
- export SHA-256 values;
- adapter/schema versions and manifest coverage;
- the comparison verdict and changed semantic fields;
- hash-only manifests and reports;
- limitations and exact external-review status.

The raw export should be published only when its prompts, tests, outputs, and licence are deliberately
public. Otherwise the workflow should generate it from a public demo and retain only hash-only
EvalRepro evidence.

Until a Promptfoo maintainer or independent user reviews the mapping, the case must be labelled
`fork-validated`, not upstream-reviewed or upstream-merged.

## Implementation sequence

1. obtain a sanitised v2 and v3 export-schema fixture generated by Promptfoo;
2. lock strict parsers and definition-only normalisation with mutation tests;
3. add the `promptfoo` snapshot command and documentation;
4. run the public opt-in demo case;
5. request narrow upstream schema/contract feedback;
6. consider a separate result-mode design only after definition-mode behaviour is reviewed.

No implementation PR should claim Promptfoo compatibility, adoption, or endorsement before these
gates are met.
