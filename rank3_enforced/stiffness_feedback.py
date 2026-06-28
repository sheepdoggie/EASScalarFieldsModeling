from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .fingerprints import stable_json_hash
from .response_burden import ResponseBurdenReport, build_response_burden_report
from .second_variation import InducedStiffnessReport, estimate_induced_stiffness
from .soo_execution import SOOExecutionReport
from .stiffness_equivalence import StiffnessClosureReport, compare_stiffness_families
from .stiffness_reports import PhaseIndexedStiffnessFamily


@dataclass(frozen=True)
class StiffnessFeedbackClosureSpec:
    schema_version: str = "1.0"
    closure_id: str = "stiffness_feedback_closure_v1"
    mode: str = "closure_diagnostic"
    response_burden_rule_id: str = "soo_residual_burden_v0"
    second_variation_estimator_id: str = "soo_residual_identity_hessian_v0"
    equivalence_policy_id: str = "weak_projector_spectrum"

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class StiffnessFeedbackClosureRunReport:
    report_schema: str
    closure_spec_hash: str
    input_stiffness_family_hash: str
    soo_execution_report_hash: str
    response_burden_report_hash: str
    induced_stiffness_report_hash: str
    stiffness_closure_report_hash: str
    verdict: str
    passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def run_stiffness_feedback_closure(
    *,
    spec: StiffnessFeedbackClosureSpec,
    input_stiffness: PhaseIndexedStiffnessFamily,
    execution_report: SOOExecutionReport,
) -> tuple[ResponseBurdenReport, InducedStiffnessReport, StiffnessClosureReport, StiffnessFeedbackClosureRunReport]:
    if spec.mode != "closure_diagnostic":
        # Iterative closure is intentionally not candidate/admission-capable.
        pass
    burden = build_response_burden_report(
        execution_report=execution_report,
        burden_rule_id=spec.response_burden_rule_id,
    )
    Kp, induced = estimate_induced_stiffness(
        input_stiffness=input_stiffness,
        burden_report=burden,
        estimator_id=spec.second_variation_estimator_id,
    )
    closure = compare_stiffness_families(
        input_stiffness=input_stiffness,
        induced_stiffness=Kp,
        equivalence_policy_id=spec.equivalence_policy_id,
    )
    run_report = StiffnessFeedbackClosureRunReport(
        report_schema="rank3_stiffness_feedback_closure_run_report_v1",
        closure_spec_hash=spec.fingerprint(),
        input_stiffness_family_hash=input_stiffness.fingerprint(),
        soo_execution_report_hash=execution_report.fingerprint(),
        response_burden_report_hash=burden.fingerprint(),
        induced_stiffness_report_hash=induced.fingerprint(),
        stiffness_closure_report_hash=closure.fingerprint(),
        verdict=closure.verdict,
        passed=closure.verdict in {"StrongClosed", "WeakClosed"},
        details={
            "mode": spec.mode,
            "closure_loop": "K -> association-indexed SOO sector -> response burden -> K' -> closure verdict",
            "does_not_update_K_during_candidate_run": True,
        },
    )
    return burden, induced, closure, run_report
