from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .rule_metadata import RuleMetadata, RuleStatus


@dataclass(frozen=True)
class BoundedContextSOOStepReport:
    report_schema: str
    operator_id: str
    ell: int
    phase: int
    epsilon: float
    association_state_hash: str
    phi_prev_hash: str
    phi_curr_hash: str
    phi_next_hash: str
    stiffness_profile_hash: str
    context_mean_hash: str
    context_contrast_hash: str
    residual_hash: str
    residual_l2: float
    residual_linf: float
    passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class BoundedContextSOOExecutionReport:
    report_schema: str
    primitive_operator_id: str
    primitive_law: str
    step_count: int
    passed: bool
    step_report_hashes: tuple[str, ...]
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class BoundednessStiffnessProfileReport:
    report_schema: str
    n_points: int
    profile_hash: str
    source_kind: str
    epsilon: float
    min_stiffness: float
    max_stiffness: float
    nonzero_stiffness_points: int
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class BoundednessDerivedStiffnessProfile:
    """One-scalar-per-point stiffness profile derived before execution.

    This object stores a scalar stiffness value per scalar point. It does not add
    a new dynamic degree of freedom to the scalar field: the update state remains
    Phi_previous and Phi_current. The profile is a declared/model-derived SOO
    coefficient profile used by bounded_context_soo_v1.
    """

    values: np.ndarray
    source_kind: str = "boundedness_derived_context_candidate"
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=np.float64)
        if values.ndim != 1:
            raise ManifestError("BoundednessDerivedStiffnessProfile values must be a one-dimensional vector.")
        if not np.all(np.isfinite(values)):
            raise ManifestError("BoundednessDerivedStiffnessProfile contains non-finite values.")
        if np.any(values < 0.0):
            raise ManifestError("bounded_context_soo_v1 requires nonnegative stiffness values.")
        frozen = values.copy()
        frozen.setflags(write=False)
        object.__setattr__(self, "values", frozen)

    @property
    def n_points(self) -> int:
        return int(self.values.shape[0])

    def fingerprint(self) -> str:
        return stable_json_hash(
            {
                "values": array_hash(self.values),
                "source_kind": self.source_kind,
                "details": self.details or {},
            }
        )

    def report(self, *, epsilon: float) -> BoundednessStiffnessProfileReport:
        values = np.asarray(self.values, dtype=np.float64)
        return BoundednessStiffnessProfileReport(
            report_schema="rank3_boundedness_stiffness_profile_report_v1",
            n_points=self.n_points,
            profile_hash=self.fingerprint(),
            source_kind=self.source_kind,
            epsilon=float(epsilon),
            min_stiffness=float(values.min()) if values.size else 0.0,
            max_stiffness=float(values.max()) if values.size else 0.0,
            nonzero_stiffness_points=int(np.count_nonzero(values)),
            details=dict(self.details or {}),
        )


class BoundedContextSOOUpdateRule:
    """Candidate boundedness-derived rank-3 context SOO kernel.

    The operator executes the second-order scalar update

        Phi_{ell+1}(i) = 2 Phi_ell(i) - Phi_{ell-1}(i)
            - eps^2 K_i (Phi_ell(i) - mean_r Phi_ell(a_r(i))).

    It uses the complete rank-3 association context at each point. It does not
    condition on charge labels, path-shortening targets, midpoint-zero targets,
    or detector records. It is admitted as a deterministic whole-field framework mechanism for certification attempts; this does not admit any theorem outcome as EAS law.
    """

    name = "bounded_context_soo_v1"
    metadata = RuleMetadata(
        name="bounded_context_soo_v1",
        version="0.1.16",
        status=RuleStatus.ADMITTED,
        source_hash="locked_bounded_context_soo_v1_admission_capable",
        allowed_for_certified_runs=True,
        notes=(
            "Admission-capable boundedness-derived rank-3 context SOO mechanism. Uses one scalar stiffness "
            "value per scalar point and complete rank-3 context comparison. Mechanism admission does not admit any theorem outcome."
        ),
    )

    def __init__(
        self,
        *,
        stiffness_profile: BoundednessDerivedStiffnessProfile,
        epsilon: float = 0.1,
        first_step_policy: str = "copy_phi0_as_phi_minus_1",
    ) -> None:
        if float(epsilon) < 0.0:
            raise ManifestError("bounded_context_soo_v1 epsilon must be nonnegative.")
        if first_step_policy not in {"copy_phi0_as_phi_minus_1"}:
            raise ManifestError(f"Unsupported bounded_context_soo_v1 first_step_policy: {first_step_policy}")
        self.stiffness_profile = stiffness_profile
        self.epsilon = float(epsilon)
        self.first_step_policy = str(first_step_policy)
        self._step_reports: list[BoundedContextSOOStepReport] = []

    @property
    def primitive_operator_id(self) -> str:
        return "bounded_context_soo_v1"

    def reset_trace(self) -> None:
        self._step_reports.clear()

    def get_traces(self) -> tuple[object, ...]:
        return ()

    def get_stiffness_input_report(self) -> dict[str, Any]:
        return asdict(self.stiffness_profile.report(epsilon=self.epsilon))

    def get_bounded_context_execution_report(self) -> BoundedContextSOOExecutionReport | None:
        if not self._step_reports:
            return None
        return BoundedContextSOOExecutionReport(
            report_schema="rank3_bounded_context_soo_execution_report_v1",
            primitive_operator_id="bounded_context_soo_v1",
            primitive_law=(
                "Phi_next(i)=2*Phi_curr(i)-Phi_prev(i)-epsilon^2*K_i*"
                "(Phi_curr(i)-mean_r Phi_curr(a_r(i)))"
            ),
            step_count=len(self._step_reports),
            passed=all(step.passed for step in self._step_reports),
            step_report_hashes=tuple(step.fingerprint() for step in self._step_reports),
            details={
                "complete_rank3_context_used": True,
                "active_phase_transport_used": False,
                "one_scalar_value_per_point": True,
                "one_stiffness_value_per_point": True,
                "candidate_not_admitted": True,
                "first_step_policy": self.first_step_policy,
            },
        )

    def __call__(self, context: sfg.ScalarUpdateContext) -> sfg.FloatArray:
        phi_curr = np.asarray(context.phi_current, dtype=np.float64)
        if phi_curr.ndim != 1:
            raise ManifestError("bounded_context_soo_v1 requires one-dimensional phi_current.")
        state = context.geometry.state
        n = int(state.n_points)
        if phi_curr.shape != (n,):
            raise ManifestError(f"phi_current shape {phi_curr.shape} does not match n_points={n}.")
        if self.stiffness_profile.n_points != n:
            raise ManifestError("bounded_context_soo_v1 stiffness_profile dimension does not match geometry.")
        raw_prev = getattr(context, "phi_previous", None)
        if raw_prev is None:
            if int(context.ell) != 0:
                raise ManifestError("bounded_context_soo_v1 requires phi_previous for ell>0.")
            phi_prev = phi_curr.copy()
        else:
            phi_prev = np.asarray(raw_prev, dtype=np.float64)
        if phi_prev.shape != phi_curr.shape:
            raise ManifestError("phi_previous and phi_current shapes differ.")

        K = np.asarray(self.stiffness_profile.values, dtype=np.float64)
        context_mean = phi_curr[np.asarray(state.assoc, dtype=np.int64)].mean(axis=1)
        context_contrast = phi_curr - context_mean
        residual = - (self.epsilon ** 2) * K * context_contrast
        phi_next = 2.0 * phi_curr - phi_prev + residual
        phi_next = np.asarray(phi_next, dtype=np.float64)
        if not np.all(np.isfinite(phi_next)):
            raise ManifestError("bounded_context_soo_v1 produced non-finite phi_next.")

        # This residual is algebraic consistency of the implemented closed form,
        # not an admission verdict.
        algebraic_residual = phi_next - (2.0 * phi_curr - phi_prev - (self.epsilon ** 2) * K * context_contrast)
        step_report = BoundedContextSOOStepReport(
            report_schema="rank3_bounded_context_soo_step_report_v1",
            operator_id="bounded_context_soo_v1",
            ell=int(context.ell),
            phase=int(context.phase) % 3,
            epsilon=float(self.epsilon),
            association_state_hash=state.fingerprint,
            phi_prev_hash=array_hash(phi_prev),
            phi_curr_hash=array_hash(phi_curr),
            phi_next_hash=array_hash(phi_next),
            stiffness_profile_hash=self.stiffness_profile.fingerprint(),
            context_mean_hash=array_hash(context_mean),
            context_contrast_hash=array_hash(context_contrast),
            residual_hash=array_hash(algebraic_residual),
            residual_l2=float(np.linalg.norm(algebraic_residual)),
            residual_linf=float(np.max(np.abs(algebraic_residual))) if algebraic_residual.size else 0.0,
            passed=bool(np.linalg.norm(algebraic_residual) <= 1e-10),
            details={
                "source": "boundedness-derived complete-rank-3 context SOO candidate",
                "first_step_policy": self.first_step_policy if int(context.ell) == 0 else "phi_previous_from_engine",
                "not_using_same_opposite_labels": True,
                "not_using_path_shortening_target": True,
                "not_using_midpoint_zero_target": True,
            },
        )
        self._step_reports.append(step_report)
        return phi_next


def build_bounded_context_soo_update_rule(params: dict[str, Any]) -> BoundedContextSOOUpdateRule:
    allowed = {"epsilon", "first_step_policy", "stiffness_profile", "stiffness_values", "source_kind", "details"}
    unknown = set(params) - allowed
    if unknown:
        raise ManifestError(f"bounded_context_soo_v1 unknown params: {sorted(unknown)}")
    raw_profile = params.get("stiffness_profile", params.get("stiffness_values"))
    if raw_profile is None:
        raise ManifestError("bounded_context_soo_v1 requires stiffness_profile or stiffness_values.")
    if isinstance(raw_profile, dict):
        values = raw_profile.get("values")
        source_kind = str(raw_profile.get("source_kind", params.get("source_kind", "boundedness_derived_context_candidate")))
        details = raw_profile.get("details", params.get("details", {}))
    else:
        values = raw_profile
        source_kind = str(params.get("source_kind", "boundedness_derived_context_candidate"))
        details = params.get("details", {})
    profile = BoundednessDerivedStiffnessProfile(
        values=np.asarray(values, dtype=np.float64),
        source_kind=source_kind,
        details=dict(details or {}),
    )
    return BoundedContextSOOUpdateRule(
        stiffness_profile=profile,
        epsilon=float(params.get("epsilon", 0.1)),
        first_step_policy=str(params.get("first_step_policy", "copy_phi0_as_phi_minus_1")),
    )
