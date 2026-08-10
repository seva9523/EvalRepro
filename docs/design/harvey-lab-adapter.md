# Harvey LAB adapter design

Status: implemented in adapter contract version 1; public pinned-revision case study pending

Tracking issue: [#13](https://github.com/seva9523/EvalRepro/issues/13)

Upstream project: [harveyai/harvey-labs](https://github.com/harveyai/harvey-labs)

## Purpose

Harvey LAB represents legal-agent evaluations as task directories containing a `task.json`,
effective instructions, expected deliverables, rubric criteria, and synthetic source documents.
Those inputs can change across tags or commits while schema validation and ordinary harness tests
continue to pass.

The adapter creates a hash-only EvalRepro manifest that answers a narrower question:

> Do two Harvey LAB revisions describe the same selected task contracts and source-document bytes?

It does not run an agent, grade output, validate legal correctness, or claim that matching task
inputs produce identical model or judge results.

## CLI

```bash
evalrepro snapshot harvey-lab /path/to/harvey-labs \
  --task all \
  -o baseline.manifest.json

evalrepro snapshot harvey-lab /path/to/harvey-labs-candidate \
  --task all \
  -o candidate.manifest.json
```

The selector accepts:

- `all` for every discovered `tasks/**/task.json`;
- a task-prefix selection such as `corporate-ma`;
- one exact task ID such as `real-estate/extract-psa-key-terms/scenario-01`.

Discovery is deterministic and ordered by POSIX-style task ID. `--limit` and `--no-id-preview`
use the same manifest semantics as the JSONL and Inspect adapters.

## Effective task loading

The adapter mirrors the model-free parts of Harvey LAB's harness without importing or executing its
Python modules:

1. locate `tasks/<task-id>/task.json`;
2. parse the JSON object;
3. use inline `instructions` when non-empty;
4. otherwise load `instructions.md` from the task directory;
5. resolve `docs_dir` relative to the task directory, or use `documents/` by default;
6. inventory regular source files recursively and hash their bytes;
7. validate titles, rubrics, deliverables, tags, and task field types before snapshotting.

The adapter returns a precise user-facing error for malformed JSON, missing effective instructions,
missing document directories, duplicate task IDs, unreadable files, invalid field types, absolute or
escaping `docs_dir` values, and symbolic links in task or source paths.

## Record contract

One in-memory EvalRepro record represents one task:

```json
{
  "id": "real-estate/extract-psa-key-terms/scenario-01",
  "input": {
    "title": "...",
    "instructions": "...",
    "work_type": "analyze",
    "tags": ["..."],
    "docs_dir": "tasks/real-estate/.../documents",
    "deliverables": {"report.docx": "report.docx"}
  },
  "target": {
    "criteria": [
      {
        "id": "C-001",
        "title": "...",
        "match_criteria": "...",
        "deliverables": ["report.docx"],
        "sources": ["source.docx"],
        "extra": {}
      }
    ]
  },
  "choices": null,
  "metadata": {
    "source_documents": {
      "count": 14,
      "total_bytes": 123456,
      "ordered_digest": "..."
    },
    "task_extra": {}
  }
}
```

This record exists only in memory before the normal manifest builder hashes it. The output
manifest does not contain raw instructions, rubric text, task JSON, relative document paths, or
document bytes. Task IDs are visible only through the optional diagnostic preview.

### Ordering rules

- task records are sorted by task ID;
- tags preserve source order;
- criteria preserve source order because rubric presentation is part of the contract;
- mappings use EvalRepro's canonical key ordering;
- source documents are sorted by repository-relative POSIX path before the inventory is hashed;
- task records store only the inventory count, total bytes, and ordered inventory digest;
- repeated shared document directories are read and summarised once per snapshot.

## Contract decisions

Adapter contract version 1 resolves the original open design questions as follows:

1. The resolved repository-relative `docs_dir` is semantic. Equivalent spellings such as
   `documents` and `./documents` compare equal, while a different effective corpus path is drift.
2. Unknown top-level task fields and unknown criterion fields are included in `task_extra` or
   `extra`. This fails closed when Harvey LAB adds a field whose semantics EvalRepro does not yet
   understand.
3. Adding or removing tasks from two complete selections produces `coverage_mismatch` because the
   complete task counts differ.
4. Repository-relative document paths, sizes, and content hashes are semantic inputs to one
   ordered inventory digest. Moving equal bytes to a different path is therefore drift.
5. `--no-id-preview` removes task IDs from the manifest. Reports retain aggregate hash/count
   evidence without attempting to reveal changed task IDs.

Changing one of these decisions requires incrementing `adapter_contract_version` so old and new
contracts cannot compare as though they were identical scopes.

## Scope, provenance, and runtime

Semantic scope contains:

- adapter name and contract version;
- exact, prefix, or full task selection;
- SHA-256 document-content policy;
- the document-path and unknown-field decisions above;
- the standard semantic field mapping.

Checkout path, Git commit, tag, dirty state, remote origin, and Harvey LAB package version are
provenance rather than scope. Two checkouts with identical task bytes can therefore compare as
`reproducible` even when their revisions or local paths differ.

Provenance records, when available:

- credential-stripped repository origin;
- Git commit and exact tags;
- tracked-diff and full status digests without exposing changed filenames;
- dirty working-tree state;
- Harvey LAB version from `pyproject.toml`;
- selected task count and task root.

Runtime uses EvalRepro's existing Python/platform collector. Harvey LAB is not imported and
remains an optional source checkout rather than a package dependency.

## Privacy and safety

Harvey LAB asks contributors to use synthetic matter data, but EvalRepro does not assume every
fork is safe to publish. The adapter therefore:

- performs no network, model, judge, or external API calls;
- never writes raw task or document content to a manifest;
- strips credentials and query secrets from HTTP(S) Git remote URLs;
- rejects source paths that escape the supplied repository root;
- rejects symbolic-link task, instruction, document-root, and source-file paths;
- supports `--no-id-preview` for sensitive task names;
- retains the general warning that hashes are not anonymisation.

Users remain responsible for source licences, confidentiality, and organisational policy.

## Offline mutation matrix

Synthetic tests cover:

| Mutation | Expected result |
| --- | --- |
| same repository copied to another absolute path | `reproducible` |
| Git metadata or dirty state changed, task bytes equal | `reproducible` |
| task added or removed from a complete selection | `coverage_mismatch` |
| exact/prefix/full selections differ | `scope_mismatch` |
| instruction, rubric, deliverable, unknown field, or document bytes changed | `semantic_drift` |
| inline instructions replaced by equal `instructions.md` content | `reproducible` |
| equivalent `docs_dir` spelling resolves to the same corpus | `reproducible` |
| equal document bytes moved to a different relative path | `semantic_drift` |
| missing, malformed, escaping, symlinked, or unreadable source | adapter error, exit code 3 |

All fixtures are local and synthetic. The adapter tests do not require Harvey LAB, provider keys,
network access, model execution, or judge execution.

## Public case study gate

The first public case study should compare two immutable Harvey LAB revisions and publish exact
revisions, adapter/schema versions, task and document counts, the comparison verdict, aggregate
changed-task counts, commands, and limitations. It must not publish raw task or document content.

No Harvey LAB issue or pull request should be opened until the adapter is merged, a pinned-revision
case is reproducible, and the result can be presented as a request for semantic review rather
than as a claim of Harvey adoption or endorsement.
