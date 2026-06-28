# Technical Design Document: Support-Seeded Initialization Epoch

## 1. Purpose

This document defines the support-seeded initialization layer added to the enforceable rank-3 scalar-field modeling framework.

The purpose of the layer is to solve the initialization problem for support-bearing scalar-field models:

```text
If SOO starts from anonymous all-zero vacuum, every vacuum point sees only zero.
A support-bearing model must therefore declare where the non-vacuum support record enters the scalar field.
```

The fix is a locked initialization epoch that starts from declared support-owned boundary and/or dressing records, not from arbitrary post-hoc Python logic.

## 2. Design Rule

The initialization layer obeys the same core rule as the geometry engine:

```text
Initialization sources do not create primitive association geometry.
They only define sealed scalar source records over already-declared point indices.
```

Primitive geometry remains `FrozenAssociationState`.

Scalar initialization is a pre-measurement scalar-field process.

## 3. Execution Split

A support-bearing run now has two epochs:

```text
Epoch 1: initialization
    declared support records
        -> locked initialization source rule
        -> sealed source array
        -> optional SOO initialization cycles
        -> phi_after_initialization

Epoch 2: measurement/modeling
    phi_after_initialization becomes phi_0 for the measurement run
        -> normal enforced runner
        -> readouts
        -> controls
        -> BASE gate
```

Measurement readouts begin only after initialization completes.

## 4. New Modules

The implementation adds:

```text
rank3_enforced/initialization_sources.py
rank3_enforced/initialization_runner.py
rank3_enforced/initialization_trace.py
TDD_support_seeded_initialization.md
```

Existing modules updated:

```text
rank3_enforced/overlay_schema.py
rank3_enforced/overlay_compiler.py
rank3_enforced/model_type_registry.py
rank3_enforced/soo_schema.py
rank3_enforced/soo_operator_registry.py
rank3_enforced/soo_compiler.py
rank3_enforced/soo_trace.py
rank3_enforced/certified_runner.py
rank3_enforced/evidence.py
```

## 5. Overlay Schema

A new `initialization` section is accepted by declarative overlays:

```json
{
  "initialization": {
    "mode": "support_seeded",
    "start_sites": "boundary_and_dressing_points",
    "source_rule": "balanced_boundary_dressing_lift_v0_1",
    "initialization_cycles": 2,
    "amplitude": 1.0,
    "require_nonzero_support_activation": true,
    "require_vacuum_zero_elsewhere": true,
    "measurement_starts_after_initialization": true
  }
}
```

Supported modes:

```text
vacuum_zero
explicit_phi
support_seeded
```

Supported start sites:

```text
none
boundary_points
dressing_points
boundary_and_dressing_points
```

## 6. Locked Initialization Source Rules

The locked source registry supports:

```text
zero_vacuum
explicit_phi
balanced_boundary_dressing_lift_v0_1
phase_active_dressing_lift_v0_1
phase_active_boundary_lift_v0_1
```

### 6.1 `balanced_boundary_dressing_lift_v0_1`

Requires:

```text
start_sites = boundary_and_dressing_points
boundary_points present
dressing_points present
equal boundary/dressing counts
handedness = right or left
```

Behavior:

```text
right-handed support:
    boundary += amplitude
    dressing -= amplitude

left-handed support:
    boundary -= amplitude
    dressing += amplitude
```

This is a locked scalar source rule. It does not create or modify associations.

### 6.2 `phase_active_dressing_lift_v0_1`

Requires:

```text
start_sites = dressing_points
complete active_phase_map for phases 0,1,2
```

Behavior:

```text
active dressing sites receive handedness-signed source values
```

### 6.3 `phase_active_boundary_lift_v0_1`

Requires:

```text
start_sites = boundary_points
at least three boundary points
```

Behavior:

```text
first three boundary points receive handedness-signed source values
```

## 7. SOO Initialization Source Operator

The SOO residual operator registry now includes:

```text
support_initialization_source
```

This operator is valid only when a sealed initialization source array is supplied by the locked initialization runner.

It is not available to arbitrary overlay code.

It fails if used without a sealed initialization source.

## 8. Measurement Recipe Handling

A support-seeded SOO recipe may include:

```json
{
  "id": "support_seed",
  "operator_id": "support_initialization_source",
  "weight": 1.0,
  "scope": "declared_support_sites"
}
```

During initialization, this term injects the sealed source residual.

During measurement, the compiler strips `support_initialization_source` terms from the measurement recipe. Measurement therefore begins from `phi_after_initialization` and does not keep re-injecting initialization-only source unless a future model type explicitly admits such a source.

The measurement recipe must still contain at least one non-source SOO residual term.

## 9. Blocking Rules

The model-type compiler now rejects:

```text
two_support_path_adjustment without initialization.mode = support_seeded
support_seeded initialization without supports
support_seeded initialization without soo_declarative_v0_1
support_initialization_source outside support_seeded initialization
support source affecting non-support vacuum when require_vacuum_zero_elsewhere = true
support-seeded runs with zero support activation when require_nonzero_support_activation = true
measurement_starts_after_initialization = false for support_seeded initialization
```

This prevents support-bearing models from pretending that all-zero vacuum can spontaneously construct a support path.

## 10. Initialization Traces

The initialization layer emits:

```text
InitializationSourceTrace
InitializationEpochReport
SOOUpdateTrace(epoch="initialization")
```

The source trace records:

```text
mode
start_sites
source_rule
source_hash
support_hash
source_l1
source_l2
nonzero_count
support_nonzero_count
vacuum_nonzero_count
required source invariants
pass/fail status
```

The epoch report records:

```text
initialization_cycles
initial_phi_hash
source_trace
phi_after_initialization_hash
initialization SOO trace hashes
pass/fail status
```

## 11. Evidence Package Integration

The evidence package now includes:

```text
initialization_hash
```

The BASE gate source provenance check includes this hash. Candidate/admission overlays require a compiled initialization report.

## 12. Admission Status

Current status:

```text
support-seeded initialization layer:
    enforced scaffold

balanced_boundary_dressing_lift_v0_1:
    locked candidate source rule

phase_active_dressing_lift_v0_1:
    locked candidate source rule

phase_active_boundary_lift_v0_1:
    locked candidate source rule

support_initialization_source:
    locked initialization-only SOO residual operator

final SOO dynamics:
    not admitted

final EAS remapping:
    not admitted
```

The system can now execute support-origin candidate runs while preserving the rule that support initialization is declared, locked, traced, and source-separated from measurement readouts.
