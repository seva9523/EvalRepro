# Manifest privacy model

EvalRepro deliberately stores digests instead of raw evaluation records, but a hash-only manifest is
not automatically anonymous or safe to publish.

## What a manifest contains

- SHA-256 digests for complete records and selected semantic fields;
- compact previews from the configured sample ID field;
- top-level type counts and coverage information;
- task/adapter scope, runtime versions, and source provenance.

## Residual disclosure risks

Low-entropy values can be guessed and re-hashed. For example, a target drawn from `A`, `B`, `C`, and
`D` is trivial to enumerate. Sample identifiers may contain customer, document, or case references.
Runtime and source metadata can disclose package versions, repository revisions, or operating-system
details. Dataset membership can sometimes be inferred from public candidate records.

## Publication guidance

Before publishing a manifest from a private or restricted evaluation:

1. use `--no-id-preview` for either snapshot adapter when sample IDs should not be
   included in the manifest, for example:

   ```bash
   evalrepro snapshot jsonl records.jsonl --no-id-preview -o manifest.json
   evalrepro snapshot inspect package.module:task --no-id-preview -o manifest.json
   ```

   This removes only the diagnostic preview. The ID remains part of the normalised
   sample and its digest, so the option does not weaken semantic drift detection or
   change scope comparison.
2. review or disable the sample ID field;
3. consider whether the field vocabulary is small enough to brute-force;
4. remove environment/provenance fields that your policy treats as sensitive;
5. confirm that publication complies with the dataset licence and organisational policy;
6. prefer sharing the comparison verdict and reproducible procedure over the manifests themselves
   when the underlying evaluation is confidential.

Further privacy controls may include keyed digests and configurable provenance redaction. Even with
ID-preview suppression enabled, treat manifests as potentially sensitive derived data.
