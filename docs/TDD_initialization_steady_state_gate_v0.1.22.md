# Initialization steady-state gate v0.1.22

## Audit finding

The charge modeling redo audit reported:

```text
Initialization steady state reached: 0
Initial two-ledger report passed: 0
BASE gate passed: 0
Admitted certificates: 0
```

That means the legacy suite cannot be used as publication-grade evidence.

## Rule

For admission-grade modeling, diagnostic measurement must begin only after a declared initialization/settling phase has passed.

The initialization gate must be reported separately from path-remap and path-change diagnostics:

```text
initialization_admitted
diagnostic_run_completed
path_change_candidate_observed
path_change_admitted
BASE_gate_passed
external_verdict
```

## v0.1.22 suite status

The new role/path suite is candidate diagnostic infrastructure. It uses explicit scalar initial profiles to test role/path-remap machinery.

It is not an admission run and does not substitute for SOO-settled initialization evidence.

Future admission overlays must enable and pass initialization settling gates before theorem-level claims are made.
