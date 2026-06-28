from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash


@dataclass(frozen=True)
class StiffnessMatrixReport:
    report_schema: str
    phase: int
    n_points: int
    matrix_hash: str
    source_kind: str
    self_adjoint: bool
    maps_sector_to_itself: bool
    spectrum: tuple[float, ...]
    epsilon_squared_spectrum: tuple[float, ...]
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class PhaseIndexedStiffnessFamily:
    K0: np.ndarray
    K1: np.ndarray
    K2: np.ndarray
    epsilon: float
    source_kind: str = "explicit_matrix_control"
    normalization_policy: str = "declared_scale"
    equivalence_policy: str = "weak_projector_spectrum"

    def __post_init__(self) -> None:
        matrices = [np.asarray(k, dtype=np.float64) for k in (self.K0, self.K1, self.K2)]
        shapes = {m.shape for m in matrices}
        if len(shapes) != 1:
            raise ManifestError("K0, K1, K2 must have identical shapes.")
        shape = matrices[0].shape
        if len(shape) != 2 or shape[0] != shape[1]:
            raise ManifestError("Stiffness matrices must be square.")
        for name, matrix in zip(("K0", "K1", "K2"), matrices):
            if not np.all(np.isfinite(matrix)):
                raise ManifestError(f"{name} contains non-finite values.")
            frozen = matrix.copy()
            frozen.setflags(write=False)
            object.__setattr__(self, name, frozen)
        if float(self.epsilon) < 0.0:
            raise ManifestError("epsilon must be non-negative.")

    @property
    def n_points(self) -> int:
        return int(self.K0.shape[0])

    def matrix_for_phase(self, phase: int) -> np.ndarray:
        return (self.K0, self.K1, self.K2)[int(phase) % 3]

    def fingerprint(self) -> str:
        return stable_json_hash(
            {
                "K0": array_hash(self.K0),
                "K1": array_hash(self.K1),
                "K2": array_hash(self.K2),
                "epsilon": float(self.epsilon),
                "source_kind": self.source_kind,
                "normalization_policy": self.normalization_policy,
                "equivalence_policy": self.equivalence_policy,
            }
        )

    def report_for_phase(self, phase: int) -> StiffnessMatrixReport:
        K = self.matrix_for_phase(phase)
        self_adjoint = bool(np.allclose(K, K.T, atol=1e-10))
        spectrum: tuple[float, ...]
        if self_adjoint:
            vals = np.linalg.eigvalsh(K)
        else:
            vals = np.linalg.eigvals(K).real
        spectrum = tuple(float(x) for x in vals)
        eps2 = float(self.epsilon) ** 2
        return StiffnessMatrixReport(
            report_schema="rank3_phase_indexed_stiffness_matrix_report_v1",
            phase=int(phase) % 3,
            n_points=self.n_points,
            matrix_hash=array_hash(K),
            source_kind=self.source_kind,
            self_adjoint=self_adjoint,
            maps_sector_to_itself=True,
            spectrum=spectrum,
            epsilon_squared_spectrum=tuple(float(eps2 * x) for x in vals),
            details={
                "K_is_report_level_not_ontology": True,
                "stability_note": "For association-indexed SOO, stability is decided by F_cyc,A; 0<epsilon^2 lambda<4 is only the identity-association limiting control.",
                "normalization_policy": self.normalization_policy,
                "equivalence_policy": self.equivalence_policy,
            },
        )

    def family_report(self) -> dict[str, Any]:
        return {
            "report_schema": "rank3_phase_indexed_stiffness_family_report_v1",
            "family_hash": self.fingerprint(),
            "epsilon": float(self.epsilon),
            "source_kind": self.source_kind,
            "normalization_policy": self.normalization_policy,
            "equivalence_policy": self.equivalence_policy,
            "phase_reports": [asdict(self.report_for_phase(p)) for p in (0, 1, 2)],
        }


def _matrix_from_spec(raw: Any, *, n_points: int, label: str) -> np.ndarray:
    if raw is None:
        raise ManifestError(f"Missing stiffness matrix {label}.")
    if raw == "identity":
        return np.eye(n_points, dtype=np.float64)
    if raw == "zero":
        return np.zeros((n_points, n_points), dtype=np.float64)
    if isinstance(raw, (int, float)):
        return float(raw) * np.eye(n_points, dtype=np.float64)
    if not isinstance(raw, list):
        raise ManifestError(f"{label} must be a matrix, scalar, 'identity', or 'zero'.")
    matrix = np.asarray(raw, dtype=np.float64)
    if matrix.shape != (n_points, n_points):
        raise ManifestError(f"{label} shape {matrix.shape} does not equal {(n_points, n_points)}.")
    return matrix


def build_stiffness_family_from_params(params: dict[str, Any], *, n_points: int) -> PhaseIndexedStiffnessFamily:
    epsilon = float(params.get("epsilon", params.get("response_epsilon", 1.0)))
    source_kind = str(params.get("source_kind", "explicit_matrix_control"))
    allowed_sources = {
        "explicit_matrix_control",
        "projector_parameterized_candidate",
        "feedback_closure_candidate",
        "identity_control",
        "zero_stiffness_control",
    }
    if source_kind not in allowed_sources:
        raise ManifestError(f"Unsupported stiffness source_kind {source_kind!r}.")
    if "K" in params:
        K0 = K1 = K2 = _matrix_from_spec(params["K"], n_points=n_points, label="K")
    else:
        K0 = _matrix_from_spec(params.get("K0", "zero"), n_points=n_points, label="K0")
        K1 = _matrix_from_spec(params.get("K1", "zero"), n_points=n_points, label="K1")
        K2 = _matrix_from_spec(params.get("K2", "zero"), n_points=n_points, label="K2")
    return PhaseIndexedStiffnessFamily(
        K0=K0,
        K1=K1,
        K2=K2,
        epsilon=epsilon,
        source_kind=source_kind,
        normalization_policy=str(params.get("normalization_policy", "declared_scale")),
        equivalence_policy=str(params.get("equivalence_policy", "weak_projector_spectrum")),
    )
