# Adapter specification

Adapters convert framework-specific evaluation sources into `SnapshotSource` without deciding the
comparison result.

```python
from evalrepro.adapters.base import SnapshotSource

source = SnapshotSource(
    adapter="my-framework",
    identity={"task": "benchmark-name"},
    parameters={"revision": "v2", "mode": "strict"},
    records=my_iterable,
    declared_count=1000,
    fields=("input", "target", "choices", "metadata"),
    id_field="id",
    runtime={"my-framework": "2.1.0"},
    provenance={"source_revision": "abc123"},
)
```

## Contract fields

- `adapter`: stable adapter identifier.
- `identity`: what evaluation is being compared. It must remain equal across intended baseline and
  candidate environments.
- `parameters`: settings whose differences make the evaluations non-equivalent, such as task
  kwargs, task version, split, filtering mode, or scorer configuration.
- `records`: iterable of sample objects.
- `declared_count`: total count if cheaply and reliably available.
- `fields`: mapping keys treated as semantic fields.
- `id_field`: mapping key used only for compact previews; it is not excluded from the sample hash.
- `runtime`: dependency versions and platform details. Runtime does not participate in scope matching.
- `provenance`: commits, file digests, dataset revisions, or package sources.
- `normalisation_policy`: only documented non-semantic volatility may be removed.

## Rules

1. Do not convert different semantic values to the same representation.
2. Do not drop timestamps, IDs, paths, or metadata merely because they are inconvenient. Demonstrate
   that they are runtime-generated and non-semantic for the framework.
3. Keep network access outside the comparator. The adapter may load framework data, but manifest
   comparison is pure and offline.
4. Record revisions in provenance and semantic task versions in parameters.
5. Include fixtures proving that the adapter detects at least one real mutation and ignores only the
   intended volatility.
6. Fail closed on unsupported opaque values.

## Acceptance evidence

An adapter PR should include:

- a public framework/task reference;
- a minimal reproducible command;
- one matching baseline/candidate case;
- one mutation that produces expected drift;
- unit tests without network/model calls;
- any opt-in integration run and its exact environment.
