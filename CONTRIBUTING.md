# Contributing

Thank you for improving evaluation reproducibility. Contributions should solve a real evaluation or
workflow problem and include evidence that the proposed behaviour is correct.

## Contribution ladder

### Small, well-scoped contributions

- documentation and examples;
- cross-platform path fixtures;
- report formatting;
- manifest validation cases;
- reproducibility cards backed by public evidence.

### Medium contributions

- normalisers for a documented framework type;
- new report formats;
- GitHub Action improvements;
- adapter conformance fixtures.

### Adapter contributions

Please open an adapter proposal issue before writing substantial code. State the framework, real
failure mode or use case, data objects involved, volatility that must be normalised, and how the
adapter will be validated. Read [`docs/adapter-spec.md`](docs/adapter-spec.md).

## Submit a reproducibility case

You do not need to implement an adapter or install EvalRepro before proposing a public case. Use the
**Reproducibility check request** issue form and provide a public source, exact baseline and candidate
revisions, a narrow evaluation contract, and the drift risk you want to test. The maintainer may
perform the first bounded comparison through the
[Reproducibility Clinic](docs/reproducibility-clinic.md).

Accepted cases still require external review before they are described as independently validated.
A completed comparison is not evidence of downstream adoption unless the submitting project installs
or repeatedly uses EvalRepro.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff format .
ruff check .
mypy src/evalrepro
pytest --cov=evalrepro
```

The test suite must remain network-free. Framework integrations that require downloads should use
small synthetic fixtures in unit tests and document a separate opt-in smoke test.

## Pull requests

- Keep one concern per PR.
- Include or update tests.
- Explain the user-visible failure the change prevents.
- Do not claim performance, adoption, or compatibility without reproducible evidence.
- Do not include confidential evaluation data, credentials, or raw copyrighted datasets.
- Disclose material use of coding agents in the PR description and personally review/test the result.

## Reproducibility cards

A card must link to public source versions, exact commands or a workflow, the manifest schema version,
and the status of external review. Use `fork-validated`, `upstream-reviewed`, or `upstream-merged`
accurately; do not imply upstream endorsement from an unmerged experiment.

## Recognition

Contributors are credited in release notes and adapter documentation. Sustained adapter maintainers
may be invited to become component maintainers under [`GOVERNANCE.md`](GOVERNANCE.md).
