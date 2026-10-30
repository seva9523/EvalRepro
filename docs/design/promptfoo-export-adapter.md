# Promptfoo Export Adapter

## Status
**Implemented** (Contract Version 1). Validated against Promptfoo commit `ab84555c1b0ff74eca6b03abb7936ac9a0149242`.

## Mapping & Fidelity
* **Mode:** Definition-only API (`promptfoo_source`).
* **Input:** Preserves `prompt`, `vars`, semantic `provider` configurations, and explicitly supplied `providerOutput`.
* **Target:** Extracts structural `assertions`, test `thresholds`, and `grader_configuration` (including custom scoring functions).
* **Metadata:** Captures `evaluateOptions`, `commandLineOptions`, `tags`, runtime semantics, and merges effective `testCase` metadata. (Note: The adapter trusts Promptfoo's native evaluation process, which persists `defaultTest` into the effective `testCase` prior to export, avoiding duplicate application).

## Provider Resolution
Resolves semantic execution details from `config.providers` (supporting strings, `ProviderOptions`, and single-keyed dictionaries), `config.targets`, and per-test `provider` overrides. Fails closed on ambiguous resolution.

## Validation & Provenance Privacy
* Strict schema validation rejects non-finite floats (`NaN`/`Infinity`), out-of-bounds array indices, present-null overrides, and malformed option types.
* Opaque execution nodes (e.g., serialized `[Function...]`) and embedded media (`blobAssets`) are strictly rejected.
* Provenance excludes raw filesystem paths and hashes the `evalId` (`evalrepro.promptfoo-export.eval-id.v1`) to prevent leaking sensitive internal evaluation identifiers or filenames into public manifests.