# Technical Design Document: Declarative SOO Enforcement Layer

## 1. Purpose

This document defines the enforced SOO layer added to the rank-3 scalar-field modeling framework.

The purpose is to remove arbitrary overlay-supplied Python functionals from candidate/certifiable SOO processing. In enforced mode, SOO is specified as a declarative recipe over locked SOO operators and locked closure methods. The locked core compiles the recipe into an instrumented scalar-update rule.

## 2. Security Problem Addressed

Before this layer, the main remaining manipulation surface was `ScalarUpdateRule`. A malicious or mishandled overlay functional could encode the desired outcome by forcing signs, clamping values, collapsing midpoint records, selecting endpoint-only updates, or reading target labels.

The new rule is:

```text
Candidate/certifiable overlays may not supply Python SOO functionals.
They may only supply declarative SOO recipes.
```

## 3. New Modules

```text
rank3_enforced/soo_schema.py
rank3_enforced/soo_operator_registry.py
rank3_enforced/soo_compiler.py
rank3_enforced/soo_trace.py
rank3_enforced/soo_invariants.py
```

## 4. Declarative Recipe Schema

A SOO recipe contains:

```text
recipe_id
residual_terms
closure
invariant_profile
```

Each residual term contains:

```text
id
operator_id
weight
scope
```

Current locked residual operators:

```text
active_association_contrast
completed_rank3_balance
tensor_completion_pressure
```

Current locked closures:

```text
linear_response
fixed_point_damped
```

The recipe is data-only. It may not contain executable keys or target-verdict keys.

## 5. Forbidden Recipe Keys

The parser rejects keys including:

```text
python
callable
function
lambda
source
source_code
code
exec
eval
module
import
class
expected_result
desired_result
attraction
repulsion
force_path_shortening
force_path_lengthening
midpoint_collapse
target_verdict
```

## 6. Locked Operator Registry

The SOO operator registry maps operator IDs to locked Python functions inside the core package. Overlay files may select operators by name but cannot define new operators.

### 6.1 `active_association_contrast`

Computes, for every point, the signed contrast to its active associate:

```text
residual[i] = phi[target(i, phase)] - phi[i]
```

### 6.2 `completed_rank3_balance`

Computes, for every point, the contrast between `phi[i]` and the mean of all three completed rank-3 associates.

### 6.3 `tensor_completion_pressure`

Computes a signed all-point tensor-mediated residual from the derived rank-3 tensor geometry. This reads derived tensor reports only and does not create primitive geometry.

## 7. Closure Registry

### 7.1 `linear_response`

Computes:

```text
delta_phi = response_scale * total_residual
```

This is a candidate/control closure scaffold. It is not admitted final SOO.

### 7.2 `fixed_point_damped`

Computes a deterministic damped fixed-point response for infrastructure/candidate exploration.

## 8. Trace Requirement

Every SOO transition emits `SOOUpdateTrace`:

```text
ell
phase
phi_current_hash
geometry_hash
boundary_source_hash
residual_terms
total_residual_hash
closure_trace
phi_next_hash
invariants
```

Each residual term emits:

```text
term_id
operator_id
weight
residual_hash
residual_l1
residual_l2
residual_min
residual_max
signed_sum
nonzero_count
considered_points
```

The closure emits:

```text
closure_id
solver
iterations
tolerance
converged
delta_phi_hash
delta_l1
delta_l2
delta_min
delta_max
signed_sum
```

## 9. Invariant Gate

Each SOO transition checks:

```text
shape invariant
finite-value invariant
all-points-considered invariant
no-geometry-mutation invariant
no-clamp invariant
zero-admissibility invariant
closure-convergence invariant
target-blindness invariant
```

If any invariant fails, the scalar update raises an error and the run is blocked.

## 10. Certified Runner Integration

The certified runner now:

```text
1. runs controls,
2. resets the SOO trace collector before the primary run,
3. executes the primary run,
4. collects SOO traces,
5. verifies one trace per transition,
6. verifies all SOO invariant reports,
7. verifies trace phi hashes against result phi layers,
8. hashes the SOO trace package into the evidence package,
9. includes SOO trace audit details in the BASE gate.
```

## 11. Admission Status

```text
soo_declarative_v0_1:
    Candidate only.

active_association_contrast:
    Locked candidate residual operator.

completed_rank3_balance:
    Locked candidate residual operator.

tensor_completion_pressure:
    Locked candidate residual operator.

linear_response:
    Candidate/control closure scaffold.

fixed_point_damped:
    Candidate/control closure scaffold.
```

None of these are final admitted SOO. The enforcement layer secures the execution surface; it does not certify the scientific correctness of the candidate SOO operators.

## 12. Acceptance Criteria

The layer is functioning when:

```text
arbitrary Python SOO functionals cannot be supplied by overlays;
SOO recipes reject executable and target-verdict keys;
SOO update rules are built only from locked operators;
SOO traces are emitted for every primary transition;
SOO traces are audited by the certified runner;
SOO trace hashes enter the evidence package;
all tests pass.
```
