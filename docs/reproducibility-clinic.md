# EvalRepro Reproducibility Clinic

The clinic turns a concrete public evaluation change into reviewable reproducibility evidence. Submit a
public source, two exact revisions, and the narrow contract that should remain stable. You do not need
to install EvalRepro first.

[Request a reproducibility check](https://github.com/seva9523/EvalRepro/issues/new/choose)

## Initial public-alpha cycle

The initial cycle targets three independently participating public workflows, tracked in
[issue #11](https://github.com/seva9523/EvalRepro/issues/11). Cases are selected for reproducibility,
diversity, public value, and fit with the current adapter surface. One accepted case does not imply
project-wide adoption or endorsement.

## What to provide

- a public repository, dataset, or reproducible research workflow;
- an immutable baseline and candidate revision;
- the tasks, files, dataset slice, prompts, rubrics, schemas, or configs to compare;
- the drift risk or expected invariant;
- permission to cite the public source and publish non-sensitive aggregate findings.

Do not post credentials, confidential manifests, private datasets, personal data, or raw restricted
records.

## What an accepted case may receive

- independent preflight of the supplied revisions and ancestry where applicable;
- a bounded baseline/candidate evaluation-contract comparison;
- hash-only manifests and machine-readable and human-readable reports;
- documented assumptions, limitations, and privacy boundaries;
- a reviewable issue or draft pull request;
- an optional GitHub Action integration proposal when the workflow is a good fit.

Acceptance and turnaround are not guaranteed. Some cases require a new adapter or cannot be
reproduced safely from public evidence.

## Selection criteria

A strong first case has exact revisions, public inputs, a narrow contract, a meaningful silent-drift
risk, and a maintainer or user willing to review the result. A reproducible match is as useful as
detected drift when the method and limitations are documented honestly.

Cases are not selected based on follower count, stars, reciprocal promotion, or commercial
endorsement.

## Validation ladder

Clinic outcomes are recorded separately so one-off analysis is not overstated as adoption:

1. submitted public problem;
2. EvalRepro comparison reproduced;
3. external technical review;
4. downstream CI installation;
5. repeat use on a later change;
6. real unexpected drift caught before release.

The strongest public-alpha goal is independent repeat use, not download or star volume.
