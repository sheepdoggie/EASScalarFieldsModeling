# Current Framework State v0.1.16: bounded-context SOO candidate kernel

Status: candidate infrastructure, not admitted EAS law.

## Added kernel

`bounded_context_soo_v1` implements a complete-rank-3 context second-order scalar update:

```text
Phi_next(i) = 2 Phi_curr(i) - Phi_prev(i)
    - epsilon^2 K_i (Phi_curr(i) - mean_r Phi_curr(a_r(i))).
```

This kernel was added because boundedness-derived stiffness assumes complete rank-3 context comparison, while the earlier `association_indexed_soo_v1` is an active-slot/two-ledger transport operator.

## Ontology boundary

The scalar field still has one scalar value per point. `K_i` is a declared or boundedness-derived SOO coefficient profile, not an additional dynamic scalar-field state. The kernel does not use charge labels, path-shortening targets, midpoint-zero targets, detector records, or phase-specific stiffness.

## Gate

`rank3-run-bounded-context-parity` runs a triangle/lepton-like parity gate comparing the framework kernel against the direct exploratory complete-context formula.

External admission verdict: not run.
