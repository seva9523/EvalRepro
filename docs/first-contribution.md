# Your first EvalRepro contribution

A useful first contribution should be small, testable, and connected to a real evaluation workflow.
You do not need to understand every adapter or the full manifest schema.

## Choose a scoped issue

Good starting points include:

- a documentation or error-message improvement;
- a cross-platform path or normalisation fixture;
- a new report rendering test;
- a public reproducibility card with exact versions and commands;
- an adapter conformance fixture for a framework you already use.

Avoid opening a broad adapter PR without first discussing its semantic contract. Evaluation objects
contain framework-specific volatility, and removing the wrong field can hide real drift.

## Set up the project

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff format .
ruff check .
mypy src/evalrepro
pytest --cov=evalrepro
```

## Demonstrate the behaviour

Every behaviour change should include a small case that passes before/after as appropriate and a
mutation that the test catches. Keep tests offline and use synthetic records rather than copying a
restricted dataset into the repository.

## Open the pull request

Explain the problem, the smallest useful change, the evidence, and any material AI-assisted
development. Never include credentials, confidential manifests, or unsupported adoption claims.
Maintainers will help refine a well-scoped contribution even when the first implementation is not
complete.
