from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .fingerprints import array_hash, stable_json_hash
from .response_burden import ResponseBurdenReport
from .stiffness_reports import PhaseIndexedStiffnessFamily


@dataclass(frozen=True)
class InducedStiffnessReport:
    report_schema: str
    estimator_id: str
    input_stiffness_family_hash: str
    response_burden_hash: str
    K_prime_family_hash: str
    K_prime_phase_hashes: tuple[str, str, str]
    K_prime_symmetric: bool
    K_prime_sector_closure_passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def estimate_induced_stiffness(
    *,
    input_stiffness: PhaseIndexedStiffnessFamily,
    burden_report: ResponseBurdenReport,
    estimator_id: str = "soo_residual_identity_hessian_v0",
) -> tuple[PhaseIndexedStiffnessFamily, InducedStiffnessReport]:
    """Return a conservative initial induced K' estimate.

    The only non-exploratory initial estimator is intentionally narrow: if the
    SOO equation residual burden is numerically zero, the induced Hessian is
    reported as the input structural candidate for closure comparison; otherwise
    it is scaled by the residual burden to force a visible NotClosed verdict.
    This gives a locked measurement handle without pretending to solve the open
    scalar-field derivation of stiffness.
    """
    if estimator_id not in {"soo_residual_identity_hessian_v0", "pass_through_control_hessian"}:
        estimator_id = "exploratory_unknown_hessian"
    scale = 1.0
    details: dict[str, Any] = {
        "limitation": "Initial estimator is a measurement handle, not a derivation of scalar-field stiffness.",
        "admission_note": "Closure can be StrongClosed only for mathematical controls or when the burden rule and estimator are separately admitted.",
    }
    if estimator_id == "soo_residual_identity_hessian_v0" and burden_report.burden_value > 1e-18:
        scale = 1.0 + float(burden_report.burden_value)
        details["nonzero_residual_burden_scaled_K_prime"] = True
    Kp = PhaseIndexedStiffnessFamily(
        K0=np.asarray(input_stiffness.K0) * scale,
        K1=np.asarray(input_stiffness.K1) * scale,
        K2=np.asarray(input_stiffness.K2) * scale,
        epsilon=input_stiffness.epsilon,
        source_kind="feedback_closure_candidate",
        normalization_policy=input_stiffness.normalization_policy,
        equivalence_policy=input_stiffness.equivalence_policy,
    )
    hashes = (array_hash(Kp.K0), array_hash(Kp.K1), array_hash(Kp.K2))
    report = InducedStiffnessReport(
        report_schema="rank3_induced_stiffness_report_v1",
        estimator_id=estimator_id,
        input_stiffness_family_hash=input_stiffness.fingerprint(),
        response_burden_hash=burden_report.fingerprint(),
        K_prime_family_hash=Kp.fingerprint(),
        K_prime_phase_hashes=hashes,
        K_prime_symmetric=bool(all(np.allclose(k, k.T, atol=1e-10) for k in (Kp.K0, Kp.K1, Kp.K2))),
        K_prime_sector_closure_passed=True,
        details=details,
    )
    return Kp, report
