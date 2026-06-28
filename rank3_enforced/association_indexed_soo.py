from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .active_association import (
    build_A_adjoint,
    build_A_theta,
    is_invertible,
    is_orthogonal,
    operator_hash,
)
from .cyclic_return import CyclicReturnMapReport, build_cyclic_return_report
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .rule_metadata import RuleMetadata, RuleStatus
from .soo_execution import SOOExecutionReport, SOOStepDiagnosticPoint, SOOStepExecutionReport
from .stiffness_feedback import (
    StiffnessFeedbackClosureRunReport,
    StiffnessFeedbackClosureSpec,
    run_stiffness_feedback_closure,
)
from .stiffness_reports import PhaseIndexedStiffnessFamily, build_stiffness_family_from_params


@dataclass(frozen=True)
class AssociationIndexedSOOStepSpec:
    schema_version: str = "1.0"
    operator_id: str = "association_indexed_soo_v1"
    epsilon: float = 1.0
    solve_policy: str = "orthogonal_required"
    phase_rule: str = "cyclic_0_1_2"
    feedback_enabled: bool = True
    feedback_spec: StiffnessFeedbackClosureSpec = field(default_factory=StiffnessFeedbackClosureSpec)

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


class AssociationIndexedSOOUpdateRule:
    """Locked point-to-associate second-order SOO scalar update rule.

    This is not a residual recipe. It executes the finite-sector relation

        (Phi_l - A_theta_l Phi_{l-1})
        - A^*_{theta_{l+1}}(Phi_{l+1} - A_theta_{l+1} Phi_l)
        - epsilon^2 K_theta_l Phi_l = 0.

    The rule requires ScalarUpdateContext.phi_previous. The first transition can
    either use an explicitly supplied previous field or, for a controlled seed,
    copy Phi_0 as Phi_{-1}. That seed choice is reported.
    """

    name = "association_indexed_soo_v1"
    metadata = RuleMetadata(
        name="association_indexed_soo_v1",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="locked_association_indexed_soo_v1",
        allowed_for_certified_runs=False,
        notes="Locked association-indexed second-order SOO core with explicit stiffness-feedback diagnostic reports. Candidate, not admitted.",
    )

    def __init__(
        self,
        *,
        stiffness_family: PhaseIndexedStiffnessFamily,
        solve_policy: str = "orthogonal_required",
        first_step_policy: str = "copy_phi0_as_phi_minus_1",
        diagnostic_points: tuple[tuple[int, str], ...] = (),
        feedback_spec: StiffnessFeedbackClosureSpec | None = None,
    ) -> None:
        if solve_policy not in {"orthogonal_required", "invertible_adjoint_required"}:
            raise ManifestError(f"Unsupported association-indexed SOO solve_policy: {solve_policy}")
        if first_step_policy not in {"copy_phi0_as_phi_minus_1"}:
            raise ManifestError(f"Unsupported first_step_policy: {first_step_policy}")
        self.stiffness_family = stiffness_family
        self.solve_policy = solve_policy
        self.first_step_policy = first_step_policy
        self.diagnostic_points = tuple(diagnostic_points)
        self.feedback_spec = feedback_spec or StiffnessFeedbackClosureSpec()
        self._step_reports: list[SOOStepExecutionReport] = []
        self._cyclic_return_report: CyclicReturnMapReport | None = None
        self._response_burden_report = None
        self._induced_stiffness_report = None
        self._stiffness_closure_report = None
        self._stiffness_feedback_report: StiffnessFeedbackClosureRunReport | None = None

    @property
    def primitive_operator_id(self) -> str:
        return "association_indexed_soo_v1"

    def reset_trace(self) -> None:
        self._step_reports.clear()
        self._cyclic_return_report = None
        self._response_burden_report = None
        self._induced_stiffness_report = None
        self._stiffness_closure_report = None
        self._stiffness_feedback_report = None

    def get_traces(self) -> tuple[object, ...]:
        # The legacy trace audit expects SOOUpdateTrace only for residual recipes.
        return ()

    def get_soo_execution_report(self) -> SOOExecutionReport | None:
        if not self._step_reports:
            return None
        return SOOExecutionReport(
            report_schema="rank3_association_indexed_soo_execution_report_v1",
            primitive_operator_id="association_indexed_soo_v1",
            primitive_law=(
                "(Phi_l - A_theta_l Phi_{l-1}) - A^*_{theta_{l+1}}"
                "(Phi_{l+1} - A_theta_{l+1} Phi_l) - epsilon^2 K_theta_l Phi_l = 0"
            ),
            solve_policy=self.solve_policy,
            step_count=len(self._step_reports),
            passed=all(step.passed for step in self._step_reports),
            step_report_hashes=tuple(step.fingerprint() for step in self._step_reports),
            step_reports=tuple(self._step_reports),
            details={
                "two_ledger_state_required": True,
                "point_to_self_is_only_identity_association_control": True,
                "residual_recipe_used": False,
                "first_step_policy": self.first_step_policy,
            },
        )

    def get_cyclic_return_report(self) -> CyclicReturnMapReport | None:
        return self._cyclic_return_report

    def get_stiffness_input_report(self) -> dict[str, Any]:
        return self.stiffness_family.family_report()

    def get_response_burden_report(self):
        return self._response_burden_report

    def get_induced_stiffness_report(self):
        return self._induced_stiffness_report

    def get_stiffness_closure_report(self):
        return self._stiffness_closure_report

    def get_stiffness_feedback_report(self):
        return self._stiffness_feedback_report

    def _solve_next_phi(
        self,
        *,
        phi_prev: np.ndarray,
        phi_curr: np.ndarray,
        state: sfg.FrozenAssociationState,
        phase: int,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        theta = int(phase) % 3
        theta_next = (theta + 1) % 3
        A_curr = build_A_theta(state, theta)
        A_next = build_A_theta(state, theta_next)
        A_next_adj = build_A_adjoint(A_next)
        K = self.stiffness_family.matrix_for_phase(theta)
        eps2 = float(self.stiffness_family.epsilon) ** 2

        pi_curr = phi_curr - A_curr @ phi_prev
        stiffness_action = K @ phi_curr
        rhs = phi_curr - A_curr @ phi_prev - eps2 * stiffness_action

        if self.solve_policy == "orthogonal_required":
            if not is_orthogonal(A_next):
                raise ManifestError("association_indexed_soo_v1 requires orthogonal A_theta_next under solve_policy='orthogonal_required'.")
            phi_next = A_next @ ((2.0 * np.eye(state.n_points) - eps2 * K) @ phi_curr - A_curr @ phi_prev)
            solve_method = "orthogonal_closed_form"
        elif self.solve_policy == "invertible_adjoint_required":
            if not is_invertible(A_next_adj):
                raise ManifestError("association_indexed_soo_v1 requires invertible A_theta_next^*." )
            phi_next = A_next @ phi_curr + np.linalg.solve(A_next_adj, rhs)
            solve_method = "solve_A_adjoint_linear_system"
        else:  # defensive, constructor already rejects
            raise ManifestError(f"Unsupported solve_policy: {self.solve_policy}")

        pi_next = phi_next - A_next @ phi_curr
        residual = pi_curr - A_next_adj @ pi_next - eps2 * stiffness_action
        payload = {
            "theta": theta,
            "theta_next": theta_next,
            "A_curr": A_curr,
            "A_next": A_next,
            "A_next_adj": A_next_adj,
            "K": K,
            "pi_curr": pi_curr,
            "stiffness_action": stiffness_action,
            "residual": residual,
            "solve_method": solve_method,
        }
        return np.asarray(phi_next, dtype=np.float64), payload

    def __call__(self, context: sfg.ScalarUpdateContext) -> sfg.FloatArray:
        phi_curr = np.asarray(context.phi_current, dtype=np.float64)
        raw_prev = getattr(context, "phi_previous", None)
        if raw_prev is None:
            if context.ell != 0:
                raise ManifestError("association_indexed_soo_v1 requires phi_previous for ell>0.")
            phi_prev = phi_curr.copy()
        else:
            phi_prev = np.asarray(raw_prev, dtype=np.float64)
        if phi_prev.shape != phi_curr.shape:
            raise ManifestError("phi_previous and phi_current shapes differ.")
        if self.stiffness_family.n_points != phi_curr.shape[0]:
            raise ManifestError("Stiffness family dimension does not match scalar field dimension.")

        if self._cyclic_return_report is None:
            self._cyclic_return_report = build_cyclic_return_report(
                state=context.geometry.state,
                stiffness_family=self.stiffness_family,
                solve_policy=self.solve_policy,
            )

        phi_next, payload = self._solve_next_phi(
            phi_prev=phi_prev,
            phi_curr=phi_curr,
            state=context.geometry.state,
            phase=context.phase,
        )
        residual = payload["residual"]
        point_samples: list[SOOStepDiagnosticPoint] = []
        for point, role in self.diagnostic_points:
            p = int(point)
            if 0 <= p < phi_curr.shape[0]:
                point_samples.append(
                    SOOStepDiagnosticPoint(
                        point_index=p,
                        role=str(role),
                        phi_prev_value=float(phi_prev[p]),
                        phi_curr_value=float(phi_curr[p]),
                        A_theta_curr_phi_prev_value=float((payload["A_curr"] @ phi_prev)[p]),
                        pi_A_curr_value=float(payload["pi_curr"][p]),
                        K_theta_curr_phi_curr_value=float(payload["stiffness_action"][p]),
                        phi_next_value=float(phi_next[p]),
                        soo_equation_residual_value=float(residual[p]),
                    )
                )
        step_report = SOOStepExecutionReport(
            report_schema="rank3_association_indexed_soo_step_execution_report_v1",
            operator_id="association_indexed_soo_v1",
            ell=int(context.ell),
            phase_current=int(context.phase) % 3,
            phase_next=(int(context.phase) + 1) % 3,
            epsilon=float(self.stiffness_family.epsilon),
            association_state_hash=context.geometry.state.fingerprint,
            A_theta_current_hash=operator_hash(payload["A_curr"]),
            A_theta_next_hash=operator_hash(payload["A_next"]),
            A_theta_next_adjoint_hash=operator_hash(payload["A_next_adj"]),
            K_theta_current_hash=array_hash(payload["K"]),
            phi_prev_hash=array_hash(phi_prev),
            phi_curr_hash=array_hash(phi_curr),
            phi_next_hash=array_hash(phi_next),
            pi_A_current_hash=array_hash(payload["pi_curr"]),
            stiffness_action_hash=array_hash(payload["stiffness_action"]),
            solve_policy=self.solve_policy,
            solve_method=str(payload["solve_method"]),
            A_theta_next_orthogonal=is_orthogonal(payload["A_next"]),
            A_theta_next_invertible=is_invertible(payload["A_next"]),
            soo_residual_l2=float(np.linalg.norm(residual)),
            soo_residual_linf=float(np.max(np.abs(residual))) if residual.size else 0.0,
            diagnostic_points=tuple(point_samples),
            passed=bool(np.all(np.isfinite(phi_next)) and np.linalg.norm(residual) <= 1e-8),
            details={
                "source": "locked association-indexed SOO core",
                "first_step_policy": self.first_step_policy if context.ell == 0 else "phi_previous_from_engine",
            },
        )
        self._step_reports.append(step_report)
        return phi_next

    def finalize_feedback_reports(self) -> None:
        execution = self.get_soo_execution_report()
        if execution is None:
            return
        burden, induced, closure, feedback = run_stiffness_feedback_closure(
            spec=self.feedback_spec,
            input_stiffness=self.stiffness_family,
            execution_report=execution,
        )
        self._response_burden_report = burden
        self._induced_stiffness_report = induced
        self._stiffness_closure_report = closure
        self._stiffness_feedback_report = feedback


def build_association_indexed_soo_update_rule(
    params: dict[str, Any],
    *,
    n_points: int,
    diagnostic_points: tuple[tuple[int, str], ...] = (),
) -> AssociationIndexedSOOUpdateRule:
    allowed = {
        "epsilon",
        "response_epsilon",
        "solve_policy",
        "first_step_policy",
        "stiffness",
        "feedback_closure",
    }
    unknown = set(params) - allowed
    if unknown:
        raise ManifestError(f"association_indexed_soo_v1 unknown params: {sorted(unknown)}")
    raw_stiffness = params.get("stiffness", None)
    if raw_stiffness is None:
        # Locked default while SOO-stiffness feedback is being developed: phase-specific
        # identity stiffness K0=K1=K2=I. This is a declared control/candidate default,
        # not a derived stiffness result.
        raw_stiffness = {"K": "identity", "source_kind": "identity_control"}
    if not isinstance(raw_stiffness, dict):
        raise ManifestError("association_indexed_soo_v1 requires scalar_update_params.stiffness object when supplied.")
    merged = dict(raw_stiffness)
    if "epsilon" not in merged and "response_epsilon" not in merged:
        if "epsilon" in params:
            merged["epsilon"] = params["epsilon"]
        elif "response_epsilon" in params:
            merged["response_epsilon"] = params["response_epsilon"]
    stiffness_family = build_stiffness_family_from_params(merged, n_points=n_points)
    raw_feedback = params.get("feedback_closure", {})
    if raw_feedback is None:
        raw_feedback = {}
    if not isinstance(raw_feedback, dict):
        raise ManifestError("feedback_closure must be an object.")
    spec = StiffnessFeedbackClosureSpec(
        schema_version=str(raw_feedback.get("schema_version", "1.0")),
        closure_id=str(raw_feedback.get("closure_id", "stiffness_feedback_closure_v1")),
        mode=str(raw_feedback.get("mode", "closure_diagnostic")),
        response_burden_rule_id=str(raw_feedback.get("response_burden_rule", raw_feedback.get("response_burden_rule_id", "soo_residual_burden_v0"))),
        second_variation_estimator_id=str(raw_feedback.get("second_variation_estimator", raw_feedback.get("second_variation_estimator_id", "soo_residual_identity_hessian_v0"))),
        equivalence_policy_id=str(raw_feedback.get("equivalence_policy", raw_feedback.get("equivalence_policy_id", stiffness_family.equivalence_policy))),
    )
    return AssociationIndexedSOOUpdateRule(
        stiffness_family=stiffness_family,
        solve_policy=str(params.get("solve_policy", "orthogonal_required")),
        first_step_policy=str(params.get("first_step_policy", "copy_phi0_as_phi_minus_1")),
        diagnostic_points=diagnostic_points,
        feedback_spec=spec,
    )
