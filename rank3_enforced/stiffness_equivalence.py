from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .fingerprints import stable_json_hash
from .stiffness_reports import PhaseIndexedStiffnessFamily


@dataclass(frozen=True)
class StiffnessClosureReport:
    report_schema: str
    verdict: str
    input_stiffness_family_hash: str
    induced_stiffness_family_hash: str
    equivalence_policy_id: str
    strong_closure_error_norm: float
    relative_closure_error_norm: float
    weak_closure_passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def _flat(family: PhaseIndexedStiffnessFamily) -> np.ndarray:
    return np.concatenate([family.K0.ravel(), family.K1.ravel(), family.K2.ravel()]).astype(np.float64)


def _signature(K: np.ndarray, *, tol: float = 1e-8) -> tuple[int, int, int]:
    vals = np.linalg.eigvalsh(0.5 * (K + K.T))
    pos = int(np.sum(vals > tol))
    neg = int(np.sum(vals < -tol))
    zero = int(len(vals) - pos - neg)
    return pos, neg, zero


def compare_stiffness_families(
    *,
    input_stiffness: PhaseIndexedStiffnessFamily,
    induced_stiffness: PhaseIndexedStiffnessFamily,
    equivalence_policy_id: str = "weak_projector_spectrum",
    tolerance: float = 1e-8,
) -> StiffnessClosureReport:
    a = _flat(input_stiffness)
    b = _flat(induced_stiffness)
    err = float(np.linalg.norm(a - b))
    denom = float(max(np.linalg.norm(a), tolerance))
    rel = err / denom
    strong = err <= tolerance

    signatures_match = all(
        _signature(ka) == _signature(kb)
        for ka, kb in zip(
            (input_stiffness.K0, input_stiffness.K1, input_stiffness.K2),
            (induced_stiffness.K0, induced_stiffness.K1, induced_stiffness.K2),
        )
    )
    ratios_match = True
    for ka, kb in zip(
        (input_stiffness.K0, input_stiffness.K1, input_stiffness.K2),
        (induced_stiffness.K0, induced_stiffness.K1, induced_stiffness.K2),
    ):
        va = np.linalg.eigvalsh(0.5 * (ka + ka.T))
        vb = np.linalg.eigvalsh(0.5 * (kb + kb.T))
        nz = np.abs(va) > tolerance
        if np.any(nz):
            scale = float(np.median(vb[nz] / va[nz]))
            if not np.allclose(vb[nz], scale * va[nz], atol=1e-6, rtol=1e-6):
                ratios_match = False
        else:
            ratios_match = ratios_match and bool(np.all(np.abs(vb) <= tolerance))
    weak = signatures_match and ratios_match
    if strong:
        verdict = "StrongClosed"
    elif weak:
        verdict = "WeakClosed"
    else:
        verdict = "NotClosed"
    return StiffnessClosureReport(
        report_schema="rank3_stiffness_closure_report_v1",
        verdict=verdict,
        input_stiffness_family_hash=input_stiffness.fingerprint(),
        induced_stiffness_family_hash=induced_stiffness.fingerprint(),
        equivalence_policy_id=equivalence_policy_id,
        strong_closure_error_norm=err,
        relative_closure_error_norm=rel,
        weak_closure_passed=weak,
        details={
            "signatures_match": signatures_match,
            "eigenvalue_ratios_match_up_to_scale": ratios_match,
            "strong_tolerance": tolerance,
            "weak_closure_is_structural_not_target_readout": True,
        },
    )
