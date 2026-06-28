from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .fingerprints import array_hash, stable_json_hash


@dataclass(frozen=True)
class SOOStepDiagnosticPoint:
    point_index: int
    role: str
    phi_prev_value: float
    phi_curr_value: float
    A_theta_curr_phi_prev_value: float
    pi_A_curr_value: float
    K_theta_curr_phi_curr_value: float
    phi_next_value: float
    soo_equation_residual_value: float


@dataclass(frozen=True)
class SOOStepExecutionReport:
    report_schema: str
    operator_id: str
    ell: int
    phase_current: int
    phase_next: int
    epsilon: float
    association_state_hash: str
    A_theta_current_hash: str
    A_theta_next_hash: str
    A_theta_next_adjoint_hash: str
    K_theta_current_hash: str
    phi_prev_hash: str
    phi_curr_hash: str
    phi_next_hash: str
    pi_A_current_hash: str
    stiffness_action_hash: str
    solve_policy: str
    solve_method: str
    A_theta_next_orthogonal: bool
    A_theta_next_invertible: bool
    soo_residual_l2: float
    soo_residual_linf: float
    diagnostic_points: tuple[SOOStepDiagnosticPoint, ...]
    passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class SOOExecutionReport:
    report_schema: str
    primitive_operator_id: str
    primitive_law: str
    solve_policy: str
    step_count: int
    passed: bool
    step_report_hashes: tuple[str, ...]
    step_reports: tuple[SOOStepExecutionReport, ...]
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))
