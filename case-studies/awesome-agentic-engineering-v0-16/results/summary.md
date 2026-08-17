# Awesome Agentic Engineering pinned-release result

**Validation status:** public design-partner case reproduced by the EvalRepro case-study script; a pinned GitHub workflow is included. No adoption or endorsement is claimed.

| Evidence | Result |
| --- | --- |
| Baseline revision | `d3bafb19c06bd493b43188675cf7b7fd4dbf3065` |
| Candidate revision | `7edabb8a76a225fd035b13f33f0b997c03175016` |
| Selected artifact coverage | 8 → 8 |
| Verdict | `semantic_drift` |
| Changed selected artifacts | 3 of 8 |
| Changed paths | `starters/read-only/agent-readiness.yml`, `starters/draft-only/agent-readiness.yml`, `starters/state-changing/agent-readiness.yml` |
| Unchanged selected artifacts | 3 Agent Cards, fixture pack, Agent Card Schema |
| Manifest / case-study contract | v1 / v1 |

The run reads the eight public files directly from two immutable git revisions. Published manifests contain hashes and aggregate metadata, not file contents. It does not run an agent, a model, a judge, or the generated workflows.
