# Governance

EvalRepro is currently a maintainer-led public alpha.

## Roles

- **Project maintainer:** Sevinj Ahmadova (`@seva9523`) owns releases, security decisions, schema
  compatibility, and final merge decisions.
- **Component maintainer:** a sustained contributor may be invited to review and maintain a specific
  adapter or subsystem.
- **Contributor:** anyone whose accepted issue, review, documentation, code, test, or reproducibility
  card improves the project.

## Decision process

Small reversible changes are decided through pull-request review. Manifest-schema changes, digest
semantics, privacy defaults, and compatibility-breaking adapter changes require a public design issue
and a documented decision. Maintainers must state conflicts of interest and cannot use private data
to justify public compatibility claims.

## Releases

Alpha releases may change APIs. Once schema stability is declared, breaking schema changes require a
major version and a migration note. Release notes credit external contributors and distinguish
experimental, fork-validated, reviewed, and merged integrations.
