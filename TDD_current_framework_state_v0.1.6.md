# Technical Design Document: Enforceable Rank-3 Scalar Field Modeling Framework v0.1.6

**Release label:** `0.1.6-support-seeded-two-ledger-charge-modules`  
**Status:** Candidate framework infrastructure. Not an admitted physical model.  
**Primary architectural rule:** every modeling feature is isolated in a locked, declarative, non-executable module boundary.

## 1. Purpose

This framework exists to run EAS rank-3 scalar-field diagnostics without allowing model-specific Python logic to smuggle results into the run. The current revision adds optional experimental module overlays and the support/path initialization needed to rebuild charge same/opposite tests on the association-indexed SOO core.

The framework now separates:

1. primitive association-indexed SOO execution;
2. support/path initialization;
3. optional module declarations;
4. stiffness-feedback diagnostics;
5. charge/gravity module overlays;
6. readouts and burdens;
7. certification/gate evidence.

## 2. Current implemented scope

Implemented in v0.1.6:

- Support-seeded two-ledger initializer.
- Default phase-specific association-indexed SOO with `K0=K1=K2=I` when no stiffness family is declared.
- Optional module declaration/reporting system.
- Experimental charge attraction/repulsion module overlay type.
- Experimental gravitation path module overlay type.
- Permutation-safe explicit path construction `linear_support_path_v0_2` for orthogonal active association operators.
- New association-indexed controls.
- Charge path/support burden rule placeholders.
- Relation-complete packet readout.
- Common-mode/zero-sum packet readout.
- Rebuilt L16-L32 same/opposite charge overlays.
- Updated TDDs and tests.

Postponed by instruction:

- SOO-stiffness closure BASE gate block.
- Final stiffness-feedback functional.
- Admitted charge or gravitation verdicts.

## 3. EAS SOO basis

The primitive SOO law remains `association_indexed_soo_v1`:

```text
(Phi_l - A_theta_l Phi_{l-1})
-
A^*_{theta_{l+1}}(Phi_{l+1} - A_theta_{l+1} Phi_l)
-
epsilon^2 K_theta_l Phi_l
= 0
```

The runner is two-ledger: it uses both `Phi_{l-1}` and `Phi_l`. The first measurement step may now receive an explicit `initial_phi_previous` from the support-seeded two-ledger initializer. This removes the need to fake the first ledger by copying `Phi_0` for support/path diagnostics.

## 4. Modular architecture

### 4.1 Core scalar-field engine

Files:

```text
scalar_field_geometry.py
```

Responsibilities:

- immutable association states;
- geometry snapshots;
- scalar update context;
- remap context;
- run loop;
- optional `initial_phi_previous` for second-order update rules.

Non-responsibilities:

- no hard-coded SOO;
- no charge logic;
- no gravity logic;
- no stiffness-feedback logic.

### 4.2 Association-indexed SOO core

Files:

```text
rank3_enforced/active_association.py
rank3_enforced/association_indexed_soo.py
rank3_enforced/soo_execution.py
rank3_enforced/cyclic_return.py
```

Responsibilities:

- build `A_theta` and `A_theta^*`;
- verify orthogonality/invertibility;
- execute the association-indexed second-order relation;
- emit `SOO_EXECUTION_REPORT.json`;
- emit `CYCLIC_RETURN_REPORT.json`.

Candidate/admission default solve policy remains `orthogonal_required` unless explicitly changed.

### 4.3 Stiffness reports and feedback diagnostics

Files:

```text
rank3_enforced/stiffness_reports.py
rank3_enforced/response_burden.py
rank3_enforced/second_variation.py
rank3_enforced/stiffness_equivalence.py
rank3_enforced/stiffness_feedback.py
```

Responsibilities:

- represent phase-specific `K0,K1,K2`;
- default to `K=I` for association-indexed SOO when no stiffness is declared;
- compute placeholder response burden diagnostics;
- compute induced stiffness placeholder reports;
- compare `K'` to `K` using strong/weak closure rules.

Current limitation:

- feedback closure is a diagnostic handle, not a solved stiffness derivation.
- The BASE gate does not yet require stiffness closure to pass.

### 4.4 Support-seeded two-ledger initialization

Files:

```text
rank3_enforced/initialization_sources.py
rank3_enforced/initialization_runner.py
rank3_enforced/two_ledger_initialization.py
rank3_enforced/initialization_trace.py
```

New initialization mode:

```json
"mode": "support_seeded_two_ledger"
```

New source rules:

```text
balanced_boundary_dressing_two_ledger_lift_v0_1
neutral_boundary_dressing_two_ledger_lift_v0_1
```

The initializer builds:

```text
Phi_prev = declared initial_phi
Phi_curr = declared initial_phi + sealed support source
Pi_A_curr = Phi_curr - A_theta_curr Phi_prev
```

Evidence artifact:

```text
INITIAL_TWO_LEDGER_REPORT.json
```

Guardrails:

- no SOO is run during this initializer;
- zero remains a scalar value, not absence;
- measurement readouts begin only after initialization;
- `initialization_cycles` must currently be zero for this initializer.

### 4.5 Optional module overlays

Files:

```text
rank3_enforced/optional_modules.py
rank3_enforced/overlay_schema.py
```

Supported optional module IDs:

```text
soo_stiffness_feedback
charge_attraction_repulsion
gravitation
```

Optional modules are declarative configuration overlays, not executable plugins. They are recorded in:

```text
OPTIONAL_MODULE_REPORT.json
```

### 4.6 Explicit path construction

Files:

```text
rank3_enforced/path_construction.py
```

Rules:

```text
linear_support_path_v0_1
linear_support_path_v0_2
```

`linear_support_path_v0_2` constructs slot operators as full permutations so that `A0,A1,A2` are orthogonal under the standard finite-sector pairing. This is the preferred rule for association-indexed SOO candidate tests.

### 4.7 Charge readouts

Files:

```text
rank3_enforced/readouts.py
rank3_enforced/locked_registries.py
```

New readouts:

```text
relation_complete_packet_readout
common_mode_zero_sum_report
```

The relation-complete packet readout computes:

```text
chi_H,r = Phi(boundary_H,r) - Phi(dressing_H,r)
```

These are readouts only. They do not feed SOO and do not select stiffness.

### 4.8 Charge burden placeholders

Files:

```text
rank3_enforced/response_burden.py
```

New burden rule IDs:

```text
path_sector_role_burden_v0_1
support_packet_role_burden_v0_1
charge_packet_contrast_burden_v0_1
path_support_packet_burden_v0_1
rank3_closure_burden_v0_1
```

These provide a measurement handle for stiffness-feedback work but remain placeholders. Charge-facing burdens must not be the sole stiffness selector for admission.

### 4.9 Model types

Files:

```text
rank3_enforced/model_type_registry.py
```

Current model types include:

```text
minimal_control
two_support_path_adjustment
two_support_explicit_path_adjustment
association_indexed_soo_feedback_candidate
charge_attraction_repulsion_candidate
gravitation_path_candidate
```

The charge module requires:

```text
scalar_update_rule = association_indexed_soo_v1
path_construction.rule = linear_support_path_v0_2
initialization.mode = support_seeded_two_ledger
exactly two supports
complete active_phase_map for phases 0,1,2
support handedness right/left
non_overlap_required = true
```

### 4.10 Controls

Files:

```text
rank3_enforced/control_suite.py
```

New association-indexed controls:

```text
association_indexed_two_ledger_control
association_indexed_identity_stiffness_control
association_indexed_zero_stiffness_control
residual_recipe_rejection_control
```

These are added to association-indexed and charge model plans.

## 5. Rebuilt charge same/opposite overlays

Directory:

```text
overlays/charge_same_opposite_association_indexed/
```

Generated overlays:

```text
L16_same_association_indexed_soo.json
L16_opposite_association_indexed_soo.json
...
L32_same_association_indexed_soo.json
L32_opposite_association_indexed_soo.json
```

Each overlay uses:

```text
model_type = charge_attraction_repulsion_candidate
initialization.mode = support_seeded_two_ledger
path_construction.rule = linear_support_path_v0_2
scalar_update_rule = association_indexed_soo_v1
feedback burden = path_support_packet_burden_v0_1
```

Same/opposite is encoded only through support handedness/orientation:

```text
same:     support_A right, support_B right
opposite: support_A right, support_B left
```

## 6. Evidence artifacts

A complete signed run may now emit:

```text
overlay.json
compiled_manifest.json
evidence_package.json
BASE_GATE_REPORT.json
control_results.json
source_audits.json
readout_results.json
SOO_FUNCTIONAL_REPORT.json
SOO_EXECUTION_REPORT.json
CYCLIC_RETURN_REPORT.json
STIFFNESS_INPUT_REPORT.json
RESPONSE_BURDEN_REPORT.json
INDUCED_STIFFNESS_REPORT.json
STIFFNESS_CLOSURE_REPORT.json
STIFFNESS_FEEDBACK_REPORT.json
INITIAL_TWO_LEDGER_REPORT.json
OPTIONAL_MODULE_REPORT.json
initialization_report.json
initialization_soo_traces.json
raw_result_package.json
EVIDENCE_ENVELOPE.json
EVIDENCE_ENVELOPE.sig
CERTIFICATE.json
SHA256SUMS.csv
```

## 7. Certification status

The framework remains candidate infrastructure. The new charge overlays are not admitted evidence. A valid structural run means only:

- the declarative overlay compiled;
- the support-seeded two-ledger initializer produced a valid pair;
- association-indexed SOO executed;
- controls ran;
- readouts were emitted;
- stiffness-feedback placeholder reports were produced.

It does **not** mean charge attraction/repulsion is certified.

## 8. Test status

Current test suite:

```text
27 passed
```

Additional test coverage in v0.1.6:

- `linear_support_path_v0_2` produces orthogonal slot operators;
- one rebuilt charge overlay runs and emits two-ledger/readout/SOO reports;
- all 34 rebuilt charge overlays compile.

## 9. Remaining work

Postponed or not yet admitted:

1. SOO-stiffness closure BASE gate block.
2. Formal response-burden functional for stiffness feedback.
3. Support-seeded gravitation overlay suite.
4. Stiffness closure admission policy.
5. Charge result statistical analyzer.
6. Suite runner that stops on first failure and packages all outputs.
7. External admission workflow for associational SOO charge tests.

