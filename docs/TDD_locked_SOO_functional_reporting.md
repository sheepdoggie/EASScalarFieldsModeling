# Technical Design Document: Locked SOO Functional Reporting and Diagnostic Residual Traces

## Purpose

The scalar field values change only through the scalar update rule. Therefore every enforceable run must identify the SOO functional being used and must expose enough signed evidence to audit how that functional acted at predeclared diagnostic points.

This addition treats the SOO functional as a first-class evidential artifact, not an informal property of the source code.

## New signed artifact

Each signed run package now contains:

```text
SOO_FUNCTIONAL_REPORT.json
```

The report records:

- scalar update rule name and metadata;
- declarative SOO recipe id;
- residual operator ids, term ids, weights, and scopes;
- closure id and closure parameters;
- whole-field update status;
- signed-value / zero-crossing / no-clamp requirements;
- operator functional descriptions;
- warnings when a recipe contains only raw scalar smoothing terms;
- diagnostic points sampled by the SOO trace.

The report hash is included in `evidence_package.json` and in `EVIDENCE_ENVELOPE.json` as `soo_functional_hash`.

## Diagnostic point traces

The SOO trace format now includes per-diagnostic-point samples.

For each residual term and diagnostic point:

```text
phi_current_value
raw_residual_value
weighted_residual_value
```

For the closure at the same diagnostic point:

```text
total_residual_value
delta_phi_value
phi_next_value
```

For explicit path runs, the compiler selects the diagnostic points from locked records:

- declared center point for odd path length;
- declared center pair for even path length;
- left and right support anchors;
- declared boundary and dressing points;
- active dressing points by phase.

The overlay cannot insert arbitrary Python trace logic.

## New locked candidate residual operator

```text
relation_complete_packet_contrast
```

For active phase `r` and support `H`, the support packet is:

```text
chi_H,r = phi(boundary_H,r) - phi(dressing_H,r)
```

The operator propagates the signed packet comparison from the two declared supports along the locked explicit path record. It preserves the relation-complete boundary/dressing contrast channel separately from raw scalar smoothing terms.

This operator remains candidate status. It is not an admitted final SOO law.

## Why this was added

Earlier framework runs used residual terms such as:

```text
active_association_contrast
completed_rank3_balance
tensor_completion_pressure
```

Those are whole-field signed scalar operators, but they can behave like smoothing or common-mode balancing. For charge-contact tests, that can erase the relation-complete signed boundary/dressing packet distinction required by the paper mechanism.

The framework now exposes this explicitly: the functional report warns when a charge-orientation run lacks `relation_complete_packet_contrast`, and the trace records exactly what each residual term contributed at the center locus.

## Admission status

This update improves auditability and supplies a locked candidate relation-complete channel. It does not admit the final SOO functional. A run using the new operator remains candidate evidence unless a separate external admission verdict and BASE gate admit it.
