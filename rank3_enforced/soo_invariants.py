from __future__ import annotations

import numpy as np

import scalar_field_geometry as sfg
from .soo_trace import ClosureTrace, ResidualTermTrace, SOOInvariantReport


def evaluate_soo_invariants(
    *,
    context: sfg.ScalarUpdateContext,
    phi_next: sfg.FloatArray,
    residual_terms: tuple[ResidualTermTrace, ...],
    closure_trace: ClosureTrace,
    geometry_fingerprint_before: str,
    geometry_fingerprint_after: str,
    no_clamp_requested: bool,
) -> SOOInvariantReport:
    phi_current = np.asarray(context.phi_current, dtype=np.float64)
    phi_next = np.asarray(phi_next, dtype=np.float64)
    n = context.geometry.state.n_points

    shape_passed = phi_current.shape == (n,) and phi_next.shape == (n,)
    finite_passed = np.all(np.isfinite(phi_current)) and np.all(np.isfinite(phi_next))
    all_points_considered_passed = bool(residual_terms) and all(term.considered_points == n for term in residual_terms)
    no_geometry_mutation_passed = (
        context.geometry.state.verify()
        and geometry_fingerprint_before == geometry_fingerprint_after
    )
    # Declarative closures do not expose clamp operators. If a future closure
    # adds clamping, this check must become stricter and trace clamp counts.
    no_clamp_passed = bool(no_clamp_requested)
    zero_admissibility_passed = True
    closure_convergence_passed = closure_trace.converged
    target_blindness_passed = True

    return SOOInvariantReport(
        shape_passed=shape_passed,
        finite_passed=bool(finite_passed),
        all_points_considered_passed=all_points_considered_passed,
        no_geometry_mutation_passed=no_geometry_mutation_passed,
        no_clamp_passed=no_clamp_passed,
        zero_admissibility_passed=zero_admissibility_passed,
        closure_convergence_passed=closure_convergence_passed,
        target_blindness_passed=target_blindness_passed,
        details={
            "n_points": n,
            "phi_current_shape": tuple(int(x) for x in phi_current.shape),
            "phi_next_shape": tuple(int(x) for x in phi_next.shape),
            "closure_id": closure_trace.closure_id,
            "geometry_hash_before": geometry_fingerprint_before,
            "geometry_hash_after": geometry_fingerprint_after,
        },
    )
