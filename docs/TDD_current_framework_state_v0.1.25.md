# TDD: Current Framework State v0.1.25

## Purpose

v0.1.25 repairs the v0.1.24 modeling-intent implementation defect discovered during certification-mode charge modeling attempts.

The v0.1.24 CLI accepted `--mode certification --modeling-intent-contract`, but suite artifacts could still contain the exploratory default contract because the run manager did not pass the supplied contract into each staged overlay. This created non-certifying records that were not reliably bound to the requested contract.

## Corrections

1. Contract propagation is now mandatory for suite runs.
2. The run manager passes the supplied `modeling_intent` payload into every staged overlay.
3. Certification mode performs pre-run compliance validation before model execution.
4. If a certification contract fails against an overlay, the framework writes a non-modeling rejection package and does not execute SOO for that case.
5. Per-case artifacts include `CONTRACT_PROPAGATION_REPORT.json` and `RUN_CLASSIFICATION.json`.
6. Suite reports include modeling mode, contract hash, contract path, certification-requested status, and warning-mode non-certifying status.
7. Local/offline signed release-guard sources can be supplied explicitly by CLI or by `RANK3_RELEASE_DIR`.

## Evidential status

v0.1.25 does not certify the charge path-adjustment theorem. It improves enforcement so certification attempts cannot silently fall back to exploratory/default-contract artifacts.

Any run without a contract remains exploratory by default. Any certification run with a rejected or missing contract is fail-closed before model execution.

## Path-edit ontology boundary

The v0.1.23 correction remains in force:

- path add/remove is not EAS ontology;
- path add/remove is not an intrinsic framework rule;
- path edit requests must come from an external exploratory monitor;
- the framework validates, applies transactionally, and logs accepted requests.

## Validation

- `python -m compileall`: passed.
- targeted contract/release tests: passed.
- pytest split validation: 55 non-charge-debug tests passed; 4 charge-debug tests passed separately.

Full single-process pytest can hang in this environment after the final long debug test, but the same tests pass when split by file group.
