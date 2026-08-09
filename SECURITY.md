# Security policy

## Supported versions

Only the latest release and current `main` are supported during public alpha.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities that could expose evaluation data, execute untrusted
code unexpectedly, bypass manifest integrity checks, or compromise the GitHub Action. Use GitHub's
private vulnerability reporting feature for this repository. If that feature is unavailable, contact
the maintainer through the email address listed on the maintainer's GitHub profile without including
sensitive payloads in the first message.

## Threat model notes

- Adapters may import and execute framework code. Run untrusted tasks in an isolated environment.
- A hash-only manifest can still leak information through low-entropy hashes and ID previews.
- The composite action installs code from the referenced EvalRepro revision; pin a release tag or
  commit in security-sensitive workflows.
- EvalRepro does not verify package signatures or dataset licences.
