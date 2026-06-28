from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import scalar_field_geometry as sfg
from .fingerprints import array_hash, stable_json_hash
from .rule_metadata import RuleMetadata, RuleStatus
from .soo_invariants import evaluate_soo_invariants
from .soo_operator_registry import compute_residual_term
from .soo_schema import SOORecipe
from .soo_trace import (
    ClosurePointSample,
    ClosureTrace,
    DiagnosticPointSample,
    ResidualTermTrace,
    SOOTraceCollector,
    SOOUpdateTrace,
)

DiagnosticPoint = tuple[int, str]


def _dedupe_diagnostic_points(points: tuple[DiagnosticPoint, ...]) -> tuple[DiagnosticPoint, ...]:
    seen: set[int] = set()
    out: list[DiagnosticPoint] = []
    for point, role in points:
        point = int(point)
        if point in seen:
            continue
        seen.add(point)
        out.append((point, str(role)))
    return tuple(out)


def _point_samples(
    *,
    phi_current: np.ndarray,
    raw_residual: np.ndarray,
    weighted_residual: np.ndarray,
    diagnostic_points: tuple[DiagnosticPoint, ...],
) -> tuple[DiagnosticPointSample, ...]:
    samples: list[DiagnosticPointSample] = []
    n = int(phi_current.shape[0])
    for point, role in diagnostic_points:
        point = int(point)
        if point < 0 or point >= n:
            raise ValueError(f"SOO diagnostic point {point} out of range for n_points={n}.")
        samples.append(
            DiagnosticPointSample(
                point_index=point,
                role=str(role),
                phi_current_value=float(phi_current[point]),
                raw_residual_value=float(raw_residual[point]),
                weighted_residual_value=float(weighted_residual[point]),
            )
        )
    return tuple(samples)


def _closure_point_samples(
    *,
    total_residual: np.ndarray,
    delta_phi: np.ndarray,
    phi_next: np.ndarray,
    diagnostic_points: tuple[DiagnosticPoint, ...],
) -> tuple[ClosurePointSample, ...]:
    samples: list[ClosurePointSample] = []
    n = int(total_residual.shape[0])
    for point, role in diagnostic_points:
        point = int(point)
        if point < 0 or point >= n:
            raise ValueError(f"SOO diagnostic point {point} out of range for n_points={n}.")
        samples.append(
            ClosurePointSample(
                point_index=point,
                role=str(role),
                total_residual_value=float(total_residual[point]),
                delta_phi_value=float(delta_phi[point]),
                phi_next_value=float(phi_next[point]),
            )
        )
    return tuple(samples)


def _array_stats(
    *,
    term_id: str,
    operator_id: str,
    weight: float,
    phi_current: np.ndarray,
    raw_residual: np.ndarray,
    weighted_residual: np.ndarray,
    diagnostic_points: tuple[DiagnosticPoint, ...],
) -> ResidualTermTrace:
    residual = np.asarray(weighted_residual, dtype=np.float64)
    raw = np.asarray(raw_residual, dtype=np.float64)
    return ResidualTermTrace(
        term_id=term_id,
        operator_id=operator_id,
        weight=float(weight),
        residual_hash=array_hash(residual),
        residual_l1=float(np.sum(np.abs(residual))),
        residual_l2=float(np.linalg.norm(residual)),
        residual_min=float(np.min(residual)) if residual.size else 0.0,
        residual_max=float(np.max(residual)) if residual.size else 0.0,
        signed_sum=float(np.sum(residual)),
        nonzero_count=int(np.count_nonzero(residual)),
        considered_points=int(residual.shape[0]) if residual.ndim == 1 else -1,
        point_samples=_point_samples(
            phi_current=phi_current,
            raw_residual=raw,
            weighted_residual=residual,
            diagnostic_points=diagnostic_points,
        ),
    )


def _geometry_hash(geometry: sfg.GeometrySnapshot) -> str:
    return stable_json_hash(
        {
            "state_fingerprint": geometry.state.fingerprint,
            "ell": geometry.ell,
            "phase": geometry.phase,
            "adjacency": array_hash(geometry.adjacency),
            "path_lengths": array_hash(geometry.path_lengths),
            "pair_weights": array_hash(geometry.pair_weights),
            "tensor_geometry": array_hash(geometry.tensor_geometry),
        }
    )


@dataclass(frozen=True)
class DeclarativeSOOScalarUpdateRule:
    """Locked candidate SOO update compiled from a declarative recipe.

    The overlay supplies data only. This rule executes only locked operators and
    emits a trace for every transition. Diagnostic point samples are selected by
    the compiler from locked path/support records, not by post-hoc readout code.
    """

    recipe: SOORecipe
    boundary_source_array: sfg.FloatArray | None = None
    boundary_source_hash: str | None = None
    epoch_label: str = "measurement"
    supports: tuple[object, ...] = ()
    path_construction_report: object | None = None
    diagnostic_points: tuple[DiagnosticPoint, ...] = ()
    trace_collector: SOOTraceCollector = field(default_factory=SOOTraceCollector)
    name: str = "soo_declarative_v0_1"
    metadata: RuleMetadata = RuleMetadata(
        name="soo_declarative_v0_1",
        version="0.2.0",
        status=RuleStatus.CANDIDATE,
        source_hash="locked_registry_soo_declarative_v0_2_with_functional_and_point_traces",
        allowed_for_certified_runs=False,
        notes="Locked candidate SOO update compiled from declarative residual/closure recipe; emits SOO functional report and diagnostic point residual contributions.",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostic_points", _dedupe_diagnostic_points(self.diagnostic_points))

    def reset_trace(self) -> None:
        self.trace_collector.reset()

    def get_traces(self) -> tuple[SOOUpdateTrace, ...]:
        return self.trace_collector.as_tuple()

    def trace_fingerprint(self) -> str:
        return self.trace_collector.fingerprint()

    def __call__(self, context: sfg.ScalarUpdateContext) -> sfg.FloatArray:
        phi_current = np.asarray(context.phi_current, dtype=np.float64)
        n = context.geometry.state.n_points
        if phi_current.shape != (n,):
            raise ValueError(f"phi_current must have shape {(n,)}, got {phi_current.shape}.")

        geometry_hash_before = _geometry_hash(context.geometry)
        total_residual = np.zeros_like(phi_current, dtype=np.float64)
        term_traces: list[ResidualTermTrace] = []

        for term in self.recipe.residual_terms:
            raw_residual = compute_residual_term(
                spec=term,
                context=context,
                boundary_source_array=self.boundary_source_array,
                supports=self.supports,
                path_construction_report=self.path_construction_report,
            )
            if raw_residual.shape != (n,):
                raise ValueError(
                    f"SOO residual term {term.id!r} returned shape {raw_residual.shape}; expected {(n,)}."
                )
            if not np.all(np.isfinite(raw_residual)):
                raise ValueError(f"SOO residual term {term.id!r} contains non-finite values.")
            weighted = float(term.weight) * raw_residual
            total_residual += weighted
            term_traces.append(
                _array_stats(
                    term_id=term.id,
                    operator_id=term.operator_id,
                    weight=float(term.weight),
                    phi_current=phi_current,
                    raw_residual=raw_residual,
                    weighted_residual=weighted,
                    diagnostic_points=self.diagnostic_points,
                )
            )

        closure = self.recipe.closure
        if closure.id == "linear_response":
            delta_phi = float(closure.response_scale) * total_residual
            closure_iterations = 1
            converged = True
            solver_name = "linear_response"
        elif closure.id == "fixed_point_damped":
            # Conservative deterministic fixed-point scaffold. It does not use
            # target labels and does not clamp signed values.
            delta_phi = np.zeros_like(phi_current, dtype=np.float64)
            previous = delta_phi.copy()
            scale = float(closure.response_scale)
            converged = False
            closure_iterations = 0
            for iteration in range(1, int(closure.max_iterations) + 1):
                closure_iterations = iteration
                delta_phi = scale * (total_residual - 0.5 * previous)
                if np.linalg.norm(delta_phi - previous) <= float(closure.tolerance):
                    converged = True
                    break
                previous = delta_phi.copy()
            solver_name = "fixed_point_damped"
        else:
            raise ValueError(f"Unknown SOO closure id: {closure.id}")

        if not np.all(np.isfinite(delta_phi)):
            raise ValueError("SOO closure produced non-finite delta_phi.")

        phi_next = phi_current + delta_phi
        closure_trace = ClosureTrace(
            closure_id=closure.id,
            solver=solver_name,
            iterations=int(closure_iterations),
            tolerance=float(closure.tolerance),
            converged=bool(converged),
            delta_phi_hash=array_hash(delta_phi),
            delta_l1=float(np.sum(np.abs(delta_phi))),
            delta_l2=float(np.linalg.norm(delta_phi)),
            delta_min=float(np.min(delta_phi)) if delta_phi.size else 0.0,
            delta_max=float(np.max(delta_phi)) if delta_phi.size else 0.0,
            signed_sum=float(np.sum(delta_phi)),
            point_samples=_closure_point_samples(
                total_residual=total_residual,
                delta_phi=delta_phi,
                phi_next=phi_next,
                diagnostic_points=self.diagnostic_points,
            ),
        )

        invariants = evaluate_soo_invariants(
            context=context,
            phi_next=phi_next,
            residual_terms=tuple(term_traces),
            closure_trace=closure_trace,
            geometry_fingerprint_before=geometry_hash_before,
            geometry_fingerprint_after=_geometry_hash(context.geometry),
            no_clamp_requested=closure.forbid_clamping,
        )
        trace = SOOUpdateTrace(
            ell=int(context.ell),
            phase=int(context.phase),
            phi_current_hash=array_hash(phi_current),
            geometry_hash=geometry_hash_before,
            boundary_source_hash=self.boundary_source_hash,
            residual_terms=tuple(term_traces),
            total_residual_hash=array_hash(total_residual),
            closure_trace=closure_trace,
            phi_next_hash=array_hash(phi_next),
            invariants=invariants,
            epoch=self.epoch_label,
        )
        self.trace_collector.append(trace)

        if not invariants.passed:
            raise ValueError(f"SOO invariant check failed: {invariants.details}")

        return phi_next


def build_declarative_soo_update_rule(
    recipe: SOORecipe,
    *,
    boundary_source_array: sfg.FloatArray | None = None,
    boundary_source_hash: str | None = None,
    epoch_label: str = "measurement",
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
    diagnostic_points: tuple[DiagnosticPoint, ...] = (),
) -> DeclarativeSOOScalarUpdateRule:
    return DeclarativeSOOScalarUpdateRule(
        recipe=recipe,
        boundary_source_array=boundary_source_array,
        boundary_source_hash=boundary_source_hash,
        epoch_label=epoch_label,
        supports=supports,
        path_construction_report=path_construction_report,
        diagnostic_points=diagnostic_points,
    )
