# Enforceable Rank-3 Scalar Field Modeling Framework

Current release: `0.1.8-run-debugging-path-neighborhood`.

This package is designed to be installed and then run from code-free workspaces. Do not execute candidate/admission runs from inside an extracted framework source tree containing `./rank3_enforced/`, because Python will import that local tree instead of the signed installed package.

## Install and verify

```bash
python -m pip install --force-reinstall releases/current/enforceable_rank3_modeling.zip
rank3-check-release-guard --force-refresh
```

The release guard must report `"passed": true` before candidate/admission work.

## Normal run workflow

```bash
cd ~/Projects/EAS_runs
rank3-init-workspace charge_assoc_workspace
cd charge_assoc_workspace
rank3-list-suites
rank3-run-suite charge_same_opposite_association_indexed \
  --output-root runs/charge_same_opposite_assoc_soo \
  --signing-key ~/.rank3/private_key.pem
```

## Run-debugging instrumentation

The built-in charge suite now declares the optional `run_debugging` module. It emits:

```text
PATH_FACING_ASSOCIATION_REPORT.json
RUN_DEBUG_REPORT.json
```

These reports retain path-neighborhood scalar values, association rows, association-indexed ordered differences, and SOO transition changes to the requested association depth. They are diagnostic only. They do not seed path carriers, do not alter SOO, and do not make path points a special scalar-update domain.

## Run one overlay

```bash
rank3-run-overlay path/to/overlay.json runs/case_id --signing-key ~/.rank3/private_key.pem
```

## Architectural rule

```text
SOO acts whole-field.
Path-facing is association-slot role metadata only.
Debug instrumentation observes path neighborhoods but never participates in SOO.
```
