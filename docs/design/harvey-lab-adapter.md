# Harvey LAB adapter design

Status: proposed

Tracking issue: [#13](https://github.com/seva9523/EvalRepro/issues/13)

Upstream project: [harveyai/harvey-labs](https://github.com/harveyai/harvey-labs)

## Purpose

Harvey LAB represents legal-agent evaluations as task directories containing a `task.json`, effective
instructions, expected deliverables, rubric criteria, and synthetic source documents. Those inputs can
change across tags or commits while schema validation and ordinary harness tests continue to pass.

The adapter should create a hash-only EvalRepro manifest that answers a narrower question:

> Do two Harvey LAB revisions describe the same selected task contracts and source-document bytes?

It does not run an agent, grade output, validate legal correctness, or claim that matching task inputs
produce identical model/judge results.

## Proposed CLI

```bash
evalrepro snapshot harvey-lab /path/to/harvey-labs \
  --task all \
  -o baseline.manifest.json

evalrepro snapshot harvey-lab /path/to/harvey-labs-candidate \
  --task all \
  -o candidate.manifest.json
```

Selectors:

- `all`: every discovered `tasks/**/task.json`;
- a practice-area/task prefix, such as `corporate-ma`;
- one exact task ID, such as `real-estate/extract-psa-key-terms/scenario-01`.

Discovery must be deterministic and ordered by POSIX-style task ID.

## Effective task loading

The adapter should mirror the relevant, model-free parts of Harvey LAB's harness:

1. locate `tasks/<task-id>/task.json`;
2. parse the JSON object;
3. use inline `instructions` when non-empty;
4. otherwise load `instructions.md` from the task directory;
5. resolve `docs_dir` relative to the task directory when present, otherwise use `documents/`;
6. inventory regular files under the effective document directory recursively.

The adapter should fail with a precise error for malformed JSON, missing effective instructions,
missing effective document directories, duplicate task IDs, or unreadable source files. It should not
import or execute Harvey LAB Python modules.

## Record contract

One EvalRepro record represents one task. A proposed normalised shape is:

```json
{
  "id": "real-estate/extract-psa-key-terms/scenario-01",
  "input": {
    "title": "...",
    "instructions": "...",
    "work_type": "analyze",
    "tags": ["..."],
    "docs_dir": "documents",
    "deliverables": {"report.docx": "report.docx"}
  },
  "target": {
    "criteria": [
      {
        "id": "C-001",
        "title": "...",
        "match_criteria": "...",
        "deliverables": ["report.docx"],
        "sources": ["source.docx"]
      }
    ]
  },
  "choices": null,
  "metadata": {
    "source_documents": [
      {
        "path": "documents/source.docx",
        "size_bytes": 1234,
        "content_sha256": "..."
      }
    ],
    "task_extra": {}
  }
}
```

The record exists only in memory before the normal EvalRepro manifest builder hashes it. The manifest
must not contain raw instructions, rubric text, task JSON, or document bytes.

### Ordering rules

- Task records: sorted by task ID.
- Tags: preserve source order initially; a tag-order-only change is therefore visible until upstream
  semantics establish that order is irrelevant.
- Criteria: preserve source order because all-pass rubric presentation and criterion IDs are part of
  the published contract.
- Deliverable mappings: normalised through EvalRepro's canonical mapping rules.
- Source documents: sorted by POSIX relative path.

## Scope, provenance, and runtime

### Semantic scope

The following should be in adapter scope:

- adapter name and adapter contract version;
- selection (`all`, prefix, or exact task ID);
- whether document content is included;
- semantic field mapping;
- any explicit exclusion patterns.

The checkout path, Git commit, tag, and Harvey LAB repository version must not be in semantic scope.
Putting revisions in scope would make the intended comparison return `scope_mismatch` before task
content is examined.

### Provenance

Record when available:

- repository origin URL;
- Git commit SHA;
- exact tag(s) pointing at the commit;
- dirty working-tree status;
- task root and selected task count;
- adapter limitations.

A dirty checkout should be clearly reported but not rejected by default; users may be intentionally
comparing local changes. A future `--require-clean` option can enforce a clean checkout.

### Runtime

Record Python and EvalRepro versions using the existing runtime collector. No Harvey LAB Python package
is imported, so the adapter has no runtime dependency on its harness environment.

## Privacy and licensing

Harvey LAB states that contributions should use synthetic matter data, but EvalRepro must not infer
that every downstream fork is safe to publish. The adapter therefore:

- stores only record and field digests in the output manifest;
- stores relative document paths, sizes, and content digests only inside the in-memory record that is
  subsequently hashed, not as raw manifest fields;
- supports the existing `--no-id-preview` option;
- warns that hashes are not anonymisation and can reveal membership for predictable content;
- does not upload documents or contact external services.

Users remain responsible for source licences and organisational policy.

## Mutation test matrix

Synthetic, network-free tests should prove detection of:

| Mutation | Expected result |
| --- | --- |
| same repository copied to a different absolute path | `reproducible` |
| different Git commit metadata with identical task bytes | `reproducible` |
| task added or removed | `semantic_drift` or `coverage_mismatch`, depending on complete selection semantics |
| task ordering only | deterministic discovery prevents false drift |
| instruction text changed | `semantic_drift` |
| inline instructions replaced by equal `instructions.md` content | `reproducible` |
| rubric criterion text changed | `semantic_drift` |
| criterion order changed | `semantic_drift`/`order_drift` in the relevant field digests |
| deliverable mapping changed | `semantic_drift` |
| `docs_dir` changed but effective files and semantic path contract remain equal | decision must be documented before implementation |
| source-document bytes changed | `semantic_drift` |
| same document bytes at a different relative path | `semantic_drift` unless a later contract explicitly makes paths non-semantic |
| partial prefix versus full benchmark | `scope_mismatch` |
| missing/unreadable document | adapter error, exit code 3 |

## Public case study plan

The first case study should compare two immutable Harvey LAB revisions, preferably a released tag and a
later commit that contains a documented task/rubric change. It should publish:

- exact repository revisions;
- adapter and manifest schema versions;
- task and source-document counts;
- comparison verdict and aggregate changed-task counts;
- commands and limitations;
- no raw task or document content.

Before contacting Harvey maintainers, the adapter must have offline unit tests, a reproducible public
case, and conservative wording. Upstream outreach should ask whether the contract captures the
benchmark semantics correctly and whether a CI/example integration is useful.

## Open design decisions

1. Whether `docs_dir`'s textual value is semantic when two paths resolve to identical file inventories.
2. Whether unknown top-level `task.json` fields belong in `metadata.task_extra` by default or require an
   explicit allow-list.
3. Whether a full-benchmark task add/remove should be classified as semantic drift or coverage mismatch.
4. Whether document relative paths should be included as semantic fields in addition to content bytes.
5. How to report changed task IDs without publishing ID previews when `--no-id-preview` is active.
