from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .fingerprints import array_hash, stable_json_hash


@dataclass(frozen=True)
class ActiveAssociationOperatorReport:
    report_schema: str
    slot: int
    n_points: int
    operator_hash: str
    adjoint_hash: str
    maps_sector_to_itself: bool
    permutation_like: bool
    orthogonal: bool
    invertible: bool
    determinant: float | None
    rank: int
    condition_number: float | None
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def build_A_s(state: sfg.FrozenAssociationState, slot: int) -> np.ndarray:
    """Return the finite active-association operator As with (As phi)(x)=phi(as(x))."""
    s = int(slot) % 3
    n = int(state.n_points)
    A = np.zeros((n, n), dtype=np.float64)
    for x in range(n):
        A[x, int(state.assoc[x, s])] = 1.0
    A.setflags(write=False)
    return A


def build_A_theta(state: sfg.FrozenAssociationState, theta: int) -> np.ndarray:
    return build_A_s(state, int(theta) % 3)


def build_A_adjoint(A: np.ndarray) -> np.ndarray:
    adj = np.asarray(A, dtype=np.float64).T.copy()
    adj.setflags(write=False)
    return adj


def operator_hash(A: np.ndarray) -> str:
    return array_hash(np.asarray(A, dtype=np.float64))


def is_permutation_like(A: np.ndarray) -> bool:
    A = np.asarray(A, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        return False
    return (
        np.all((A == 0.0) | (A == 1.0))
        and np.all(np.sum(A, axis=1) == 1.0)
        and np.all(np.sum(A, axis=0) == 1.0)
    )


def is_orthogonal(A: np.ndarray, *, atol: float = 1e-10) -> bool:
    A = np.asarray(A, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        return False
    I = np.eye(A.shape[0], dtype=np.float64)
    return bool(np.allclose(A.T @ A, I, atol=atol) and np.allclose(A @ A.T, I, atol=atol))


def is_invertible(A: np.ndarray, *, atol: float = 1e-12) -> bool:
    A = np.asarray(A, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        return False
    return int(np.linalg.matrix_rank(A, tol=atol)) == int(A.shape[0])


def summarize_active_association_operator(state: sfg.FrozenAssociationState, slot: int) -> ActiveAssociationOperatorReport:
    A = build_A_s(state, slot)
    adj = build_A_adjoint(A)
    rank = int(np.linalg.matrix_rank(A))
    inv = is_invertible(A)
    det: float | None = None
    cond: float | None = None
    if A.shape[0] <= 256:
        try:
            det = float(np.linalg.det(A))
        except np.linalg.LinAlgError:
            det = None
        try:
            cond_raw = float(np.linalg.cond(A))
            cond = cond_raw if np.isfinite(cond_raw) else None
        except np.linalg.LinAlgError:
            cond = None
    return ActiveAssociationOperatorReport(
        report_schema="rank3_active_association_operator_report_v1",
        slot=int(slot) % 3,
        n_points=int(state.n_points),
        operator_hash=operator_hash(A),
        adjoint_hash=operator_hash(adj),
        maps_sector_to_itself=True,
        permutation_like=is_permutation_like(A),
        orthogonal=is_orthogonal(A),
        invertible=inv,
        determinant=det,
        rank=rank,
        condition_number=cond,
        details={
            "definition": "(A_s phi)(x) = phi(a_s(x)) on the finite scalar-point sector.",
            "global_phase_only": True,
            "pointwise_phase_selector_allowed": False,
        },
    )
