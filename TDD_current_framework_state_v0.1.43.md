# TDD Current Framework State v0.1.43

## Release label

`0.1.43-whole-field-conjugate-vacuum-derived-longitudinal`

## Purpose

v0.1.43 adds an exploratory whole-field runner for the repaired photon-like emergence question:

```text
Can undefined whole-field vacuum, first-association conjugate splitting, SOO, and generated association selection produce lambda(P)=0 as a derived longitudinal residual while preserving non-path conjugate balance q,-q?
```

The runner is not an endpoint-class comparison and does not certify photons, charge, bounded supports, Standard Model particles, or a path-accommodation theorem.

## New runner

`rank3_enforced/whole_field_conjugate_vacuum.py`

Console commands:

```text
rank3-run-whole-field-conjugate-vacuum
rank3-write-whole-field-conjugate-vacuum-packet
```

## Core rule added

When an undefined vacuum site first participates in association selection, the site splits into two generated conjugate branches. Under the conjugate-link variants, one association of each branch is assigned to its conjugate partner. This is a generated association record, not a memory variable and not a photon template.

## Derived readout

The longitudinal component is not a stored path-facing scalar value. It is read after SOO as:

```text
lambda(P) = Phi(P) - Phi(a_path(P))
```

The non-path conjugate readout is:

```text
tau_plus(P)  = Phi(P)
tau_minus(P) = Phi(a_conjugate(P))
```

A clean candidate requires:

```text
lambda(P) = 0
tau_plus(P) + tau_minus(P) = 0
tau_plus(P) - tau_minus(P) != 0
```

## Variants

- `A_NO_CONJUGATE_FIRST_ASSOC_BASELINE`
- `B_CONJUGATE_LINK_PATH_SLOT_CONTROL`
- `C_CONJUGATE_LINK_TRANSVERSE_SLOT`
- `D_SUCCESSOR_COVARIANT_CONJUGATE_SLOT`

The path-slot control is expected to fail clean photon-like status because if the conjugate branch itself is used as the path-facing association, the derived longitudinal residual is nonzero.

## Required reports

- `WHOLE_FIELD_RUN_SCOPE_REPORT.json`
- `WHOLE_FIELD_ADMISSIBILITY_VARIANT_LEDGER.json`
- `VACUUM_FIRST_ASSOCIATION_CONJUGATE_SPLIT_LEDGER.json`
- `WHOLE_FIELD_ASSOCIATION_SELECTION_LEDGER.json`
- `WHOLE_FIELD_SOO_TRACE.json`
- `DERIVED_LONGITUDINAL_RESIDUAL_REPORT.json`
- `NON_PATH_CONJUGATE_BALANCE_REPORT.json`
- `POSTRUN_TRANSVERSE_RECORD_CANDIDATE_REPORT.json`
- `PHOTON_CANDIDATE_DERIVED_ZERO_AUDIT.json`
- `PATH_ACCOMMODATION_FROM_DERIVED_RESIDUAL_REPORT.json`
- `PHOTON_NONZERO_PATH_FACING_CONTROL_REPORT.json`
- `LEAKAGE_MANIPULATION_AUDIT.json`
- `EXPLORATORY_VERDICT_REPORT.json`

## Controls

Forbidden generator inputs include stored path-facing zero scalar values, component-zero sealing, constructed photon endpoints, loaded q/-q transverse forms, photon labels, Standard Model labels, target Delta L, and endpoint-class comparison sets.

The `PHOTON_NONZERO_PATH_FACING_CONTROL_REPORT` remains explicit: nonzero longitudinal/path-facing load is path-capable and is classified as a noncertifying photon-perturbation control, not as photon-like.
