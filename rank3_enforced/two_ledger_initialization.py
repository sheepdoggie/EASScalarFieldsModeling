from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .active_association import build_A_theta, operator_hash
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .initialization_trace import InitializationSourceTrace


@dataclass(frozen=True)
class InitialTwoLedgerReport:
    """Evidence report for a locked two-ledger measurement initial state.

    This report certifies only how (Phi_{ell-1}, Phi_ell) was seeded before
    association-indexed SOO begins. It does not certify a charge/gravity result
    and it does not alter the primitive SOO law.
    """

    report_schema: str
    initializer_id: str
    phi_previous_hash: str
    phi_current_hash: str
    theta_current: int
    A_theta_current_hash: str
    pi_A_current_hash: str
    source_trace_hash: str
    support_seeded: bool
    path_seeded: bool
    passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def build_support_seeded_two_ledger_pair(
    *,
    initial_state: sfg.FrozenAssociationState,
    declared_initial_phi: np.ndarray,
    source_array: np.ndarray,
    source_trace: InitializationSourceTrace,
    theta_current: int = 0,
    initializer_id: str = "support_seeded_two_ledger_v0_1",
    path_report: object | None = None,
) -> tuple[np.ndarray, np.ndarray, InitialTwoLedgerReport]:
    """Create a locked support-seeded two-ledger start.

    The conservative initial pair is:

        Phi_prev = declared_initial_phi
        Phi_curr = declared_initial_phi + support/path source

    The association-indexed ordered difference is reported as:

        Pi_A_curr = Phi_curr - A_theta_curr Phi_prev.
    """

    phi_prev = np.asarray(declared_initial_phi, dtype=np.float64).copy()
    source = np.asarray(source_array, dtype=np.float64).copy()
    if phi_prev.shape != (initial_state.n_points,):
        raise ManifestError("two-ledger phi_previous shape does not match association state.")
    if source.shape != (initial_state.n_points,):
        raise ManifestError("two-ledger source_array shape does not match association state.")
    phi_curr = phi_prev + source
    theta = int(theta_current) % 3
    A_theta = build_A_theta(initial_state, theta)
    pi_A = phi_curr - A_theta @ phi_prev
    passed = bool(
        source_trace.passed
        and np.all(np.isfinite(phi_prev))
        and np.all(np.isfinite(phi_curr))
        and np.all(np.isfinite(pi_A))
    )
    report = InitialTwoLedgerReport(
        report_schema="rank3_initial_two_ledger_report_v1",
        initializer_id=initializer_id,
        phi_previous_hash=array_hash(phi_prev),
        phi_current_hash=array_hash(phi_curr),
        theta_current=theta,
        A_theta_current_hash=operator_hash(A_theta),
        pi_A_current_hash=array_hash(pi_A),
        source_trace_hash=source_trace.fingerprint(),
        support_seeded=True,
        path_seeded=path_report is not None,
        passed=passed,
        details={
            "two_ledger_pair": "Phi_prev=declared_initial_phi; Phi_curr=declared_initial_phi+sealed_source_array",
            "ordered_difference": "Pi_A_curr = Phi_curr - A_theta_curr Phi_prev",
            "source_rule": source_trace.source_rule,
            "source_hash": source_trace.source_hash,
            "path_report_hash": path_report.fingerprint() if path_report is not None else None,
            "zero_is_scalar_value_not_absence": True,
            "does_not_run_soo_during_initialization": True,
        },
    )
    if not report.passed:
        raise ManifestError(f"Two-ledger initialization failed: {report.details}")
    return phi_prev, phi_curr, report
