# TDD Current Framework State v0.1.11

Release label: `0.1.11-soo-settled-initialization-witness`

## Purpose

This revision repairs the initialization semantics for EAS candidate runs. A support-seeded field is not treated as a steady state merely because source records were applied. For charge/path candidate overlays, initialization now runs whole-field association-indexed SOO before the measurement epoch and evaluates settling only on support-influenced exterior witness records.

## Ontological constraints

- SOO remains whole-field.
- Witness sets do not alter SOO, stiffness, associations, remapping, scalar update rules, or readout verdicts.
- Path-facing is association-slot metadata only.
- Relational path witnesses are used only to decide whether initialization has reached a fixed or recurrent condition.
- Nonzero scalar values are not required for path participation.
- Steady state does not mean global quiescence or field-wide uniformity.

## New module

```text
rank3_enforced/initialization_settling.py
```

It provides:

```text
InitializationSettlingSpec
InitializationSettlingReport
parse_settling_spec
build_influenced_witness_points
analyze_settling_scan
disabled_settling_report
```

## Settling witness selection

For two or more supports with an explicit path:

```text
witness_scope = relational_path_exterior_witness
witness points = declared path points outside support-owned records
optional association-neighborhood depth may be included
```

For one support:

```text
witness_scope = single_support_dressing_exterior_witness
witness points = dressing points, plus optional exterior association-neighborhood
```

For no supports, only control-style fallback is allowed:

```text
witness_scope = no_support_whole_field_fallback_control
```

## Settling metric

After support seeding, the initializer runs association-indexed SOO through complete rank-3 cycles. For candidate recurrence periods, it compares same-phase returns over the witness set.

For each witness point and same-phase return, it computes statistics for both:

```text
Phi
Pi_A = Phi_l(x) - A_theta Phi_{l-1}(x)
```

Reported statistics include:

```text
rms_delta
q95_abs_delta
max_abs_delta
sign_change_fraction
comparable_point_count
```

A steady condition is accepted only if all phase records pass for the required number of consecutive cycles.

## New evidence artifact

Every run now emits:

```text
INITIALIZATION_SETTLING_REPORT.json
```

The report includes:

```text
initialization_scan_steps
initialization_scan_rank3_cycles
accepted_initialization_steps
accepted_initialization_rank3_cycles
steady_state_reached
steady_state_type = fixed | recurrent | not_reached
accepted_recurrence_period_cycles
witness_scope
witness_rule
witness_points
excluded_support_points
per_cycle_witness_statistics
measurement_initial_state_hash
```

## Initialization/measurement separation

The standard initialization report now distinguishes the legacy `initialization_cycles` field from association-indexed settling cycles. Association-indexed settling cycles are recorded in `INITIALIZATION_SETTLING_REPORT.json`.

When settling succeeds, the final accepted two-ledger state becomes the measurement initial state:

```text
Phi_previous_for_measurement = Phi_{accepted_layer-1}
Phi_current_for_measurement = Phi_{accepted_layer}
```

When settling fails, candidate packages may still be generated for diagnostics, but the BASE gate fails and admission/certification is blocked.

## Built-in charge suite

The built-in charge same/opposite overlays now declare initialization settling:

```json
"settling": {
  "enabled": true,
  "witness_scope": "auto_influenced_exterior",
  "witness_neighborhood_depth": 0,
  "min_cycles": 2,
  "max_cycles": 3,
  "consecutive_stable_cycles_required": 1,
  "recurrence_period_min": 1,
  "recurrence_period_max": 3,
  "tol_rms": 1e-8,
  "tol_q95": 1e-8,
  "tol_max": 1e-7,
  "tol_sign": 0.0,
  "zero_epsilon": 1e-12,
  "fail_if_not_steady": true
}
```

These defaults are intentionally short diagnostic defaults. If the current SOO candidate fails to settle under this gate, the run remains useful as SOO diagnostics but cannot certify charge/path adjustment.

## Run status interpretation

A candidate run with `initialization_steady_state_reached=false` must be interpreted as:

```text
Rejected as a charge/path theorem test.
Useful only as SOO initialization diagnostics.
```

The measurement phase may still be executed in candidate mode so the evidence package can show what the unsettled candidate SOO did. Admission/certification remains fail-closed.

## Validation

Selected regression tests were run:

```text
8 passed
```

The full test suite is slower after adding mandatory SOO initialization scans because association-indexed controls run additional full-layer SOO passes.
