from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .fingerprints import stable_json_hash


@dataclass(frozen=True)
class DiagnosticPointSample:
    point_index: int
    role: str
    phi_current_value: float
    raw_residual_value: float
    weighted_residual_value: float


@dataclass(frozen=True)
class ClosurePointSample:
    point_index: int
    role: str
    total_residual_value: float
    delta_phi_value: float
    phi_next_value: float


@dataclass(frozen=True)
class ResidualTermTrace:
    term_id: str
    operator_id: str
    weight: float
    residual_hash: str
    residual_l1: float
    residual_l2: float
    residual_min: float
    residual_max: float
    signed_sum: float
    nonzero_count: int
    considered_points: int
    point_samples: tuple[DiagnosticPointSample, ...] = ()


@dataclass(frozen=True)
class ClosureTrace:
    closure_id: str
    solver: str
    iterations: int
    tolerance: float
    converged: bool
    delta_phi_hash: str
    delta_l1: float
    delta_l2: float
    delta_min: float
    delta_max: float
    signed_sum: float
    point_samples: tuple[ClosurePointSample, ...] = ()


@dataclass(frozen=True)
class SOOInvariantReport:
    shape_passed: bool
    finite_passed: bool
    all_points_considered_passed: bool
    no_geometry_mutation_passed: bool
    no_clamp_passed: bool
    zero_admissibility_passed: bool
    closure_convergence_passed: bool
    target_blindness_passed: bool
    details: dict[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return (
            self.shape_passed
            and self.finite_passed
            and self.all_points_considered_passed
            and self.no_geometry_mutation_passed
            and self.no_clamp_passed
            and self.zero_admissibility_passed
            and self.closure_convergence_passed
            and self.target_blindness_passed
        )


@dataclass(frozen=True)
class SOOUpdateTrace:
    ell: int
    phase: int
    phi_current_hash: str
    geometry_hash: str
    boundary_source_hash: str | None
    residual_terms: tuple[ResidualTermTrace, ...]
    total_residual_hash: str
    closure_trace: ClosureTrace
    phi_next_hash: str
    invariants: SOOInvariantReport
    epoch: str = "measurement"

    def fingerprint(self) -> str:
        return stable_json_hash(self)


@dataclass
class SOOTraceCollector:
    """Mutable trace sink owned by a locked SOO rule instance.

    The collector is intentionally separate from the overlay: the overlay cannot
    write traces or suppress traces. The certified runner resets it before the
    primary run and audits it after execution.
    """

    traces: list[SOOUpdateTrace] = field(default_factory=list)

    def append(self, trace: SOOUpdateTrace) -> None:
        self.traces.append(trace)

    def reset(self) -> None:
        self.traces.clear()

    def as_tuple(self) -> tuple[SOOUpdateTrace, ...]:
        return tuple(self.traces)

    def fingerprint(self) -> str:
        return stable_json_hash([trace.fingerprint() for trace in self.traces])
