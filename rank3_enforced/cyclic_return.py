from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .active_association import build_A_theta, is_invertible, is_orthogonal, operator_hash
from .fingerprints import array_hash, stable_json_hash
from .stiffness_reports import PhaseIndexedStiffnessFamily


@dataclass(frozen=True)
class PhaseStepMapReport:
    report_schema: str
    phase_current: int
    phase_next: int
    matrix_hash: str
    shape: tuple[int, int]
    determinant: float | None
    rank: int
    condition_number: float | None
    A_current_hash: str
    A_next_hash: str
    K_current_hash: str
    solve_policy: str
    single_valued: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class CyclicReturnMapReport:
    report_schema: str
    cyclic_return_hash: str
    step_reports: tuple[PhaseStepMapReport, ...]
    determinant: float | None
    rank: int
    eigenvalues: tuple[dict[str, float], ...]
    stable_elliptic_candidate_count: int
    unit_modulus_count: int
    hyperbolic_or_unstable_count: int
    passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def build_phase_step_matrix(
    *,
    state: sfg.FrozenAssociationState,
    stiffness_family: PhaseIndexedStiffnessFamily,
    phase_current: int,
    solve_policy: str,
) -> np.ndarray:
    n = int(state.n_points)
    theta = int(phase_current) % 3
    theta_next = (theta + 1) % 3
    A_curr = build_A_theta(state, theta)
    A_next = build_A_theta(state, theta_next)
    K = stiffness_family.matrix_for_phase(theta)
    eps2 = float(stiffness_family.epsilon) ** 2
    if solve_policy == "orthogonal_required":
        if not is_orthogonal(A_next):
            raise ValueError("A_theta_next is not orthogonal/permutation-like on this finite sector.")
        lower_left = -A_next @ A_curr
        lower_right = A_next @ (2.0 * np.eye(n) - eps2 * K)
    elif solve_policy == "invertible_adjoint_required":
        adj_inv = np.linalg.inv(A_next.T)
        lower_left = -adj_inv @ A_curr
        lower_right = A_next + adj_inv @ (np.eye(n) - eps2 * K)
    else:
        raise ValueError(f"Unsupported solve_policy: {solve_policy}")
    M = np.block([[np.zeros((n, n)), np.eye(n)], [lower_left, lower_right]])
    return np.asarray(M, dtype=np.float64)


def _summarize_matrix(M: np.ndarray) -> tuple[float | None, int, float | None]:
    rank = int(np.linalg.matrix_rank(M))
    det: float | None = None
    cond: float | None = None
    if M.shape[0] <= 512:
        try:
            det = float(np.linalg.det(M))
        except np.linalg.LinAlgError:
            det = None
        try:
            raw = float(np.linalg.cond(M))
            cond = raw if np.isfinite(raw) else None
        except np.linalg.LinAlgError:
            cond = None
    return det, rank, cond


def build_cyclic_return_report(
    *,
    state: sfg.FrozenAssociationState,
    stiffness_family: PhaseIndexedStiffnessFamily,
    solve_policy: str,
) -> CyclicReturnMapReport:
    matrices: list[np.ndarray] = []
    step_reports: list[PhaseStepMapReport] = []
    for phase in (0, 1, 2):
        M = build_phase_step_matrix(
            state=state,
            stiffness_family=stiffness_family,
            phase_current=phase,
            solve_policy=solve_policy,
        )
        matrices.append(M)
        det, rank, cond = _summarize_matrix(M)
        A_curr = build_A_theta(state, phase)
        A_next = build_A_theta(state, (phase + 1) % 3)
        step_reports.append(
            PhaseStepMapReport(
                report_schema="rank3_phase_step_map_report_v1",
                phase_current=phase,
                phase_next=(phase + 1) % 3,
                matrix_hash=array_hash(M),
                shape=tuple(int(x) for x in M.shape),
                determinant=det,
                rank=rank,
                condition_number=cond,
                A_current_hash=operator_hash(A_curr),
                A_next_hash=operator_hash(A_next),
                K_current_hash=array_hash(stiffness_family.matrix_for_phase(phase)),
                solve_policy=solve_policy,
                single_valued=(solve_policy == "orthogonal_required" and is_orthogonal(A_next)) or (solve_policy == "invertible_adjoint_required" and is_invertible(A_next.T)),
                details={"phase_step_definition": "(Phi_{l-1}, Phi_l) -> (Phi_l, Phi_{l+1}) under association-indexed SOO."},
            )
        )
    # Matrices act on second-order state. Standard cycle order F2 o F1 o F0.
    Mcyc = matrices[2] @ matrices[1] @ matrices[0]
    det, rank, _cond = _summarize_matrix(Mcyc)
    eigvals = np.linalg.eigvals(Mcyc)
    eig_payload: list[dict[str, float]] = []
    unit_count = 0
    elliptic_count = 0
    unstable_count = 0
    for z in eigvals:
        mag = float(abs(z))
        angle = float(np.angle(z))
        eig_payload.append({"real": float(z.real), "imag": float(z.imag), "modulus": mag, "angle": angle})
        if abs(mag - 1.0) <= 1e-8:
            unit_count += 1
            if abs(angle) > 1e-8 and abs(abs(angle) - np.pi) > 1e-8:
                elliptic_count += 1
        else:
            unstable_count += 1
    passed = all(r.single_valued for r in step_reports)
    return CyclicReturnMapReport(
        report_schema="rank3_cyclic_return_map_report_v1",
        cyclic_return_hash=array_hash(Mcyc),
        step_reports=tuple(step_reports),
        determinant=det,
        rank=rank,
        eigenvalues=tuple(eig_payload),
        stable_elliptic_candidate_count=int(elliptic_count),
        unit_modulus_count=int(unit_count),
        hyperbolic_or_unstable_count=int(unstable_count),
        passed=passed,
        details={
            "definition": "F_cyc,A = F_2,A o F_1,A o F_0,A",
            "rank3_phase_global": True,
            "local_rank3_phase_forbidden": True,
        },
    )
