# Technical Design Document: Locked Association-Indexed SOO Feedback Core

## Purpose

This framework update replaces residual-recipe SOO as the candidate primitive with a locked association-indexed second-order SOO execution core. Residual recipes remain available only as legacy controls or archive-reproduction infrastructure. The new primitive execution object is the finite-sector relation

```text
(Phi_l - A_theta_l Phi_{l-1})
- A^*_{theta_{l+1}}(Phi_{l+1} - A_theta_{l+1} Phi_l)
- epsilon^2 K_theta_l Phi_l = 0.
```

The implementation preserves modular separation between:

1. active association operators;
2. phase-indexed stiffness reports;
3. second-order SOO stepping;
4. cyclic return construction;
5. response-burden measurement;
6. induced-stiffness estimation;
7. stiffness-equivalence verdicts;
8. feedback-closure reporting.

## New Modules

### `rank3_enforced.active_association`

Builds and audits the finite active association operators `A_s`, their adjoints, hashes, invertibility, orthogonality, and permutation-like status. This module does not know about SOO, stiffness, charge, or path readouts.

### `rank3_enforced.stiffness_reports`

Defines `PhaseIndexedStiffnessFamily` and stiffness-matrix reports. This module treats `K_0`, `K_1`, and `K_2` as declared report-level stiffness candidates. It does not execute SOO and does not certify stiffness closure.

### `rank3_enforced.association_indexed_soo`

Defines the locked scalar update rule `association_indexed_soo_v1`. It executes the second-order point-to-associate relation using a two-ledger state `(Phi_{l-1}, Phi_l)` and emits step-level diagnostics. It does not derive `K`; it consumes a declared `PhaseIndexedStiffnessFamily`.

### `rank3_enforced.soo_execution`

Defines dataclasses for `SOOStepExecutionReport` and `SOOExecutionReport`. This is a pure reporting module.

### `rank3_enforced.cyclic_return`

Builds finite phase-step matrices `F_0,A`, `F_1,A`, `F_2,A` and the cyclic return report `F_cyc,A = F_2,A o F_1,A o F_0,A` where the finite sector admits a single-valued linear step map.

### `rank3_enforced.response_burden`

Defines response-burden reports. The initial admitted-to-code burden is `soo_residual_burden_v0`, the sum of squared association-indexed SOO equation residuals over executed steps. Other burden IDs are present only as exploratory placeholders.

### `rank3_enforced.second_variation`

Defines induced-stiffness report scaffolding. The initial estimator is deliberately conservative and is a measurement handle, not a claimed derivation of scalar-field stiffness.

### `rank3_enforced.stiffness_equivalence`

Compares input `K` to induced `K'` and emits one of:

```text
StrongClosed
WeakClosed
NotClosed
```

Weak closure compares structural features such as spectral signature and eigenvalue ratios up to scale. It is not allowed to use charge readouts as its equivalence criterion.

### `rank3_enforced.stiffness_feedback`

Coordinates the closure diagnostic loop:

```text
K -> association-indexed SOO sector -> response burden -> K' -> closure verdict
```

This layer never mutates `K` during a candidate/admission run.

## Schema and Runner Changes

A new model type is available:

```text
association_indexed_soo_feedback_candidate
```

It requires:

```text
rules.scalar_update_rule = "association_indexed_soo_v1"
```

and rejects residual recipes for this model type.

The scalar-field engine now passes `phi_previous` into `ScalarUpdateContext`. Existing first-order/control update rules ignore this field.

## Evidence Artifacts

Signed packages now write the following additional artifacts when available:

```text
SOO_EXECUTION_REPORT.json
CYCLIC_RETURN_REPORT.json
STIFFNESS_INPUT_REPORT.json
RESPONSE_BURDEN_REPORT.json
INDUCED_STIFFNESS_REPORT.json
STIFFNESS_CLOSURE_REPORT.json
STIFFNESS_FEEDBACK_REPORT.json
```

`SOO_FUNCTIONAL_REPORT.json` now records whether the primitive operator is `association_indexed_soo_v1` and points to the cyclic-return and stiffness-feedback report hashes.

## Current Limitations

1. The implementation provides an explicit measurement handle for stiffness feedback; it does not solve the scalar-field origin of stiffness.
2. Support-seeded initialization is not yet admitted for `association_indexed_soo_v1`; a separate two-ledger support initializer is required.
3. Candidate/admission runs should use `orthogonal_required` or `invertible_adjoint_required`. Pseudoinverse and least-squares continuation are intentionally absent.
4. Charge-specific response burden must not be used as the sole stiffness selector.
5. Residual-recipe SOO remains present only for legacy/control use and should not be used as a candidate primitive for the new model type.

## Validation

The update includes tests verifying that:

1. association-indexed SOO emits the modular evidence reports;
2. cyclic return is constructed;
3. stiffness feedback closure reports are produced;
4. residual recipes are rejected for `association_indexed_soo_feedback_candidate` model type.
