from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .fingerprints import array_hash, stable_json_hash
from .soo_execution import SOOExecutionReport


@dataclass(frozen=True)
class ResponseBurdenReport:
    report_schema: str
    burden_rule_id: str
    input_execution_report_hash: str
    burden_value: float
    burden_vector_hash: str
    scalar_field_native: bool
    interface_facing: bool
    exploratory: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def _role_residuals(execution_report: SOOExecutionReport, predicates: tuple[str, ...]) -> np.ndarray:
    values: list[float] = []
    for step in execution_report.step_reports:
        for sample in getattr(step, "diagnostic_points", ()):
            role = str(getattr(sample, "role", ""))
            if any(p in role for p in predicates):
                values.append(float(getattr(sample, "soo_equation_residual_value", 0.0)))
    return np.asarray(values, dtype=np.float64)


def build_response_burden_report(
    *,
    execution_report: SOOExecutionReport,
    burden_rule_id: str = "soo_residual_burden_v0",
) -> ResponseBurdenReport:
    residuals = np.array([step.soo_residual_l2 for step in execution_report.step_reports], dtype=np.float64)
    scalar_native = True
    interface_facing = False
    exploratory = False

    if burden_rule_id == "soo_residual_burden_v0":
        vector = residuals
        value = float(np.sum(vector ** 2))
        details = {"definition": "Sum of squared association-indexed SOO equation residual norms over executed steps."}
    elif burden_rule_id in {"rank3_closure_burden_v0", "rank3_closure_burden_v0_1"}:
        vector = residuals
        value = float(np.sum(vector ** 2))
        details = {"definition": "Placeholder rank-3 closure burden using SOO residuals until a rank-3 closure functional is admitted."}
    elif burden_rule_id in {"path_sector_role_burden_v0", "path_sector_role_burden_v0_1"}:
        vector = _role_residuals(execution_report, ("declared_center", "support_anchor"))
        if vector.size == 0:
            vector = residuals
        value = float(np.sum(vector ** 2))
        details = {"definition": "Path-sector diagnostic burden from declared center/support-anchor SOO residual samples."}
    elif burden_rule_id in {"support_packet_role_burden_v0", "support_packet_role_burden_v0_1"}:
        vector = _role_residuals(execution_report, ("boundary", "dressing", "active_dressing"))
        if vector.size == 0:
            vector = residuals
        value = float(np.sum(vector ** 2))
        details = {"definition": "Support-packet role burden from boundary/dressing SOO residual samples."}
    elif burden_rule_id in {"charge_packet_burden_v0", "charge_packet_contrast_burden_v0", "charge_packet_contrast_burden_v0_1"}:
        vector = _role_residuals(execution_report, ("boundary", "dressing"))
        if vector.size == 0:
            vector = residuals
        value = float(np.sum(vector ** 2))
        scalar_native = False
        interface_facing = True
        exploratory = True
        details = {
            "definition": "Charge-facing packet burden placeholder over boundary/dressing residual samples.",
            "guardrail": "Must not be the sole stiffness selector for candidate/admission evidence.",
        }
    elif burden_rule_id in {"path_support_packet_burden_v0", "path_support_packet_burden_v0_1"}:
        vector = _role_residuals(execution_report, ("declared_center", "support_anchor", "boundary", "dressing", "active_dressing"))
        if vector.size == 0:
            vector = residuals
        value = float(np.sum(vector ** 2))
        scalar_native = False
        interface_facing = True
        exploratory = True
        details = {
            "definition": "Combined path/support/packet burden placeholder for charge path-sector diagnostics.",
            "guardrail": "Exploratory until the charge packet burden functional is formally admitted.",
        }
    elif burden_rule_id == "cyclic_return_burden_v0":
        vector = np.zeros(1, dtype=np.float64)
        value = 0.0
        exploratory = True
        details = {"definition": "Placeholder cyclic-return burden; requires automorphic-class metric before admission."}
    else:
        vector = residuals
        value = float(np.sum(vector ** 2))
        scalar_native = False
        exploratory = True
        details = {"warning": f"Unknown burden_rule_id {burden_rule_id!r}; classified exploratory."}

    return ResponseBurdenReport(
        report_schema="rank3_response_burden_report_v1",
        burden_rule_id=str(burden_rule_id),
        input_execution_report_hash=execution_report.fingerprint(),
        burden_value=value,
        burden_vector_hash=array_hash(vector),
        scalar_field_native=scalar_native,
        interface_facing=interface_facing,
        exploratory=exploratory,
        details=details,
    )
