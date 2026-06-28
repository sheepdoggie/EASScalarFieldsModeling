from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

import scalar_field_geometry as sfg
from .fingerprints import stable_json_hash
from .overlay_schema import SupportSpec
from .soo_validation import cyclic_matrix, load_l_path_state


@dataclass(frozen=True)
class InterpolatedProfileSpec:
    path_length: int
    orientation: str
    support_abs_value: float
    dressing_abs_value: float
    side_fraction: float
    center_value: float
    n_points: int
    path_points: tuple[int, ...]
    side_points: tuple[int, ...]
    support_points: tuple[int, ...]
    center_points: tuple[int, ...]
    sign_policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecurrentProfileSolveSummary:
    period_cycles: int
    constraint_policy: str
    constrained_dim: int
    free_dim: int
    full_l2_residual: float
    full_rms_residual: float
    full_max_abs_residual: float
    witness_l2_residual: float
    witness_rms_residual: float
    witness_max_abs_residual: float
    current_profile_rms_error: float
    current_profile_max_abs_error: float
    prev_profile_rms_error: float | None
    prev_profile_max_abs_error: float | None
    solution_max_abs: float
    exact_full_passed: bool
    exact_witness_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PhaseConsistentLedgerSummary:
    omega: float
    cos_omega: float
    ledger_policy: str
    steps: int
    initial_max_abs: float
    run_max_abs: float
    final_max_abs: float
    growth_factor_over_initial: float
    all_points_ever_nonzero: bool
    ever_nonzero_count: int
    n_points: int
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DirectRecurrentInitializationReport:
    report_schema: str
    report_id: str
    profile_spec: InterpolatedProfileSpec
    epsilon: float
    stiffness_lambda: float
    period_max: int
    exact_tolerance: float
    best_full_current_only: RecurrentProfileSolveSummary
    best_witness_current_only: RecurrentProfileSolveSummary
    best_full_both_ledgers: RecurrentProfileSolveSummary
    best_witness_both_ledgers: RecurrentProfileSolveSummary
    exact_full_recurrent_profile_found: bool
    exact_witness_recurrent_profile_found: bool
    phase_consistent_ledger: PhaseConsistentLedgerSummary
    conclusions: tuple[str, ...]
    artifacts: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def _handedness_sign(handedness: str) -> float:
    return 1.0 if str(handedness).lower() == "right" else -1.0


def _support_sets(supports: Sequence[SupportSpec]) -> tuple[set[int], set[int], dict[int, float]]:
    all_support: set[int] = set()
    dressing: set[int] = set()
    signed_values: dict[int, float] = {}
    for support in supports:
        sign = _handedness_sign(support.handedness)
        for point in support.support_points:
            all_support.add(int(point))
        for point in support.boundary_points:
            signed_values[int(point)] = sign
        for point in support.dressing_points:
            dressing.add(int(point))
            signed_values[int(point)] = -sign
    return all_support, dressing, signed_values


def build_interpolated_profile(
    *,
    state: sfg.FrozenAssociationState,
    path_report: Any,
    supports: Sequence[SupportSpec],
    support_abs_value: float = 1.0,
    dressing_abs_value: float = 0.5,
    side_fraction: float = 0.5,
    center_value: float = 0.0,
) -> tuple[np.ndarray, InterpolatedProfileSpec, list[dict[str, Any]]]:
    """Build the user's proposed nonzero interpolated initialization profile.

    This function defines profile values only. It does not alter SOO and does not
    give path points special SOO handling.
    """

    n = int(state.n_points)
    profile = np.zeros(n, dtype=np.float64)
    support_points, dressing_points, signed_support_values = _support_sets(supports)
    for point, sign in signed_support_values.items():
        profile[point] = float(sign) * (float(dressing_abs_value) if point in dressing_points else float(support_abs_value))

    path_points = tuple(int(p) for p in path_report.path_points)
    m = len(path_points)
    if m <= 0:
        raise ValueError("Path report does not contain path points")
    left_anchor_sign = float(profile[int(path_report.left_anchor)])
    right_anchor_sign = float(profile[int(path_report.right_anchor)])
    # Fall back to first/last support signs if anchor values are absent.
    if left_anchor_sign == 0.0:
        left_anchor_sign = -float(dressing_abs_value)
    if right_anchor_sign == 0.0:
        right_anchor_sign = -float(dressing_abs_value)

    center_indices: set[int]
    if m % 2 == 1:
        center_idx = m // 2
        center_indices = {center_idx}
        for i, point in enumerate(path_points):
            if i <= center_idx:
                t = i / center_idx if center_idx else 1.0
                val = (1.0 - t) * left_anchor_sign + t * float(center_value)
            else:
                denom = (m - 1 - center_idx)
                t = (i - center_idx) / denom if denom else 1.0
                val = (1.0 - t) * float(center_value) + t * right_anchor_sign
            profile[point] = val
    else:
        left_center = m // 2 - 1
        right_center = m // 2
        center_indices = {left_center, right_center}
        for i, point in enumerate(path_points):
            if i <= left_center:
                t = i / left_center if left_center else 1.0
                val = (1.0 - t) * left_anchor_sign + t * float(center_value)
            elif i >= right_center:
                denom = (m - 1 - right_center)
                t = (i - right_center) / denom if denom else 1.0
                val = (1.0 - t) * float(center_value) + t * right_anchor_sign
            else:
                val = float(center_value)
            profile[point] = val

    path_set = set(path_points)
    side_values: dict[int, list[float]] = {}
    assoc = np.asarray(state.assoc, dtype=np.int64)
    for path_point in path_points:
        for slot in range(3):
            nb = int(assoc[int(path_point), slot])
            if nb not in path_set and nb not in support_points:
                side_values.setdefault(nb, []).append(float(profile[int(path_point)]) * float(side_fraction))
        # Also catch reverse associations to the path.
        hits = np.argwhere(assoc == int(path_point))
        for row, _slot in hits:
            nb = int(row)
            if nb not in path_set and nb not in support_points:
                side_values.setdefault(nb, []).append(float(profile[int(path_point)]) * float(side_fraction))
    for point, values in side_values.items():
        if values:
            profile[int(point)] = float(np.mean(values))

    rows: list[dict[str, Any]] = []
    center_points = tuple(path_points[i] for i in sorted(center_indices))
    side_points = tuple(sorted(side_values))
    for point in range(n):
        if point in support_points:
            category = "support_owned"
        elif point in path_set:
            category = "declared_path_exterior"
        elif point in side_values:
            category = "beside_path_exterior"
        else:
            category = "other"
        rows.append({
            "point": point,
            "category": category,
            "profile_value": float(profile[point]),
            "abs_profile_value": float(abs(profile[point])),
            "is_center": bool(point in center_points),
        })
    spec = InterpolatedProfileSpec(
        path_length=int(path_report.path_length),
        orientation=str(path_report.orientation),
        support_abs_value=float(support_abs_value),
        dressing_abs_value=float(dressing_abs_value),
        side_fraction=float(side_fraction),
        center_value=float(center_value),
        n_points=n,
        path_points=path_points,
        side_points=side_points,
        support_points=tuple(sorted(support_points)),
        center_points=center_points,
        sign_policy="support handedness signs; dressing sign opposite boundary; path halves interpolate anchor dressing signs to zero center",
    )
    return profile, spec, rows


def _constraint_system(
    profile: np.ndarray,
    *,
    policy: str,
) -> tuple[np.ndarray, np.ndarray]:
    n = int(profile.size)
    if policy == "current_profile_only":
        idx = np.arange(n, dtype=np.int64)
        vals = profile.copy()
    elif policy == "both_ledgers_profile":
        idx = np.concatenate([np.arange(n, dtype=np.int64), n + np.arange(n, dtype=np.int64)])
        vals = np.concatenate([profile, profile])
    else:
        raise ValueError(f"Unknown constraint policy: {policy}")
    return idx, vals


def _solve_min_recurrence(
    A: np.ndarray,
    constrained_idx: np.ndarray,
    constrained_vals: np.ndarray,
    *,
    residual_rows: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    A_used = A if residual_rows is None else A[residual_rows, :]
    ncols = int(A.shape[1])
    mask = np.ones(ncols, dtype=bool)
    mask[constrained_idx] = False
    free = np.where(mask)[0]
    v = np.zeros(ncols, dtype=np.float64)
    v[constrained_idx] = constrained_vals
    Af = A_used[:, free]
    b = -(A_used @ v)
    if Af.size:
        z, *_ = np.linalg.lstsq(Af, b, rcond=None)
        v[free] = z
    full_residual = A @ v
    used_residual = A_used @ v
    return v, {
        "full_l2_residual": float(np.linalg.norm(full_residual)),
        "full_rms_residual": float(np.sqrt(np.mean(full_residual * full_residual))) if full_residual.size else 0.0,
        "full_max_abs_residual": float(np.max(np.abs(full_residual))) if full_residual.size else 0.0,
        "used_l2_residual": float(np.linalg.norm(used_residual)),
        "used_rms_residual": float(np.sqrt(np.mean(used_residual * used_residual))) if used_residual.size else 0.0,
        "used_max_abs_residual": float(np.max(np.abs(used_residual))) if used_residual.size else 0.0,
        "free_dim": int(free.size),
        "constrained_dim": int(constrained_idx.size),
    }


def _row_from_solution(
    *,
    period: int,
    policy: str,
    v: np.ndarray,
    stats: dict[str, Any],
    profile: np.ndarray,
    witness_rows: np.ndarray,
    A: np.ndarray,
    exact_tolerance: float,
    witness_solved: bool,
) -> RecurrentProfileSolveSummary:
    n = int(profile.size)
    current = v[:n]
    previous = v[n:]
    full_residual = A @ v
    witness_residual = full_residual[witness_rows]
    current_err = current - profile
    prev_err = previous - profile
    return RecurrentProfileSolveSummary(
        period_cycles=int(period),
        constraint_policy=str(policy) + ("::witness_residual_only" if witness_solved else "::full_residual"),
        constrained_dim=int(stats["constrained_dim"]),
        free_dim=int(stats["free_dim"]),
        full_l2_residual=float(np.linalg.norm(full_residual)),
        full_rms_residual=float(np.sqrt(np.mean(full_residual * full_residual))) if full_residual.size else 0.0,
        full_max_abs_residual=float(np.max(np.abs(full_residual))) if full_residual.size else 0.0,
        witness_l2_residual=float(np.linalg.norm(witness_residual)),
        witness_rms_residual=float(np.sqrt(np.mean(witness_residual * witness_residual))) if witness_residual.size else 0.0,
        witness_max_abs_residual=float(np.max(np.abs(witness_residual))) if witness_residual.size else 0.0,
        current_profile_rms_error=float(np.sqrt(np.mean(current_err * current_err))),
        current_profile_max_abs_error=float(np.max(np.abs(current_err))),
        prev_profile_rms_error=float(np.sqrt(np.mean(prev_err * prev_err))) if "both_ledgers" in policy else None,
        prev_profile_max_abs_error=float(np.max(np.abs(prev_err))) if "both_ledgers" in policy else None,
        solution_max_abs=float(np.max(np.abs(v))),
        exact_full_passed=bool(float(np.max(np.abs(full_residual))) <= exact_tolerance),
        exact_witness_passed=bool(float(np.max(np.abs(witness_residual))) <= exact_tolerance),
    )


def solve_recurrent_profile(
    *,
    M_cycle: np.ndarray,
    profile: np.ndarray,
    path_points: Sequence[int],
    period_max: int,
    exact_tolerance: float,
) -> tuple[list[RecurrentProfileSolveSummary], list[dict[str, Any]]]:
    n = int(profile.size)
    I = np.eye(2 * n, dtype=np.float64)
    witness = np.asarray(tuple(int(x) for x in path_points), dtype=np.int64)
    witness_rows = np.concatenate([witness, n + witness])
    rows: list[RecurrentProfileSolveSummary] = []
    detail_rows: list[dict[str, Any]] = []
    for policy in ("current_profile_only", "both_ledgers_profile"):
        cidx, cvals = _constraint_system(profile, policy=policy)
        for period in range(1, int(period_max) + 1):
            A = np.linalg.matrix_power(M_cycle, int(period)) - I
            v_full, stats_full = _solve_min_recurrence(A, cidx, cvals)
            summary_full = _row_from_solution(period=period, policy=policy, v=v_full, stats=stats_full, profile=profile, witness_rows=witness_rows, A=A, exact_tolerance=exact_tolerance, witness_solved=False)
            rows.append(summary_full)
            d = summary_full.to_dict(); d["solve_scope"] = "full_residual"; detail_rows.append(d)
            v_witness, stats_witness = _solve_min_recurrence(A, cidx, cvals, residual_rows=witness_rows)
            summary_witness = _row_from_solution(period=period, policy=policy, v=v_witness, stats=stats_witness, profile=profile, witness_rows=witness_rows, A=A, exact_tolerance=exact_tolerance, witness_solved=True)
            rows.append(summary_witness)
            d = summary_witness.to_dict(); d["solve_scope"] = "witness_residual_only"; detail_rows.append(d)
    return rows, detail_rows


def simulate_phase_consistent_ledger(
    *,
    state: sfg.FrozenAssociationState,
    profile: np.ndarray,
    epsilon: float,
    stiffness_lambda: float,
    steps: int,
) -> tuple[PhaseConsistentLedgerSummary, list[dict[str, Any]], list[dict[str, Any]]]:
    coeff = 2.0 - float(epsilon) ** 2 * float(stiffness_lambda)
    cos_omega = coeff / 2.0
    omega = float(math.acos(max(-1.0, min(1.0, cos_omega))))
    # Identity-inspired phase-consistent ledger: removes the artificial x_prev=0 jump.
    prev = np.asarray(profile, dtype=np.float64) * float(cos_omega)
    curr = np.asarray(profile, dtype=np.float64).copy()
    n = int(profile.size)
    run_max = float(np.max(np.abs(curr))) if n else 0.0
    initial_max = run_max
    ever = np.abs(curr) > 1.0e-12
    layer_rows: list[dict[str, Any]] = [{
        "step": 0,
        "phase": 0,
        "max_abs_phi": float(np.max(np.abs(curr))),
        "rms_phi": float(np.sqrt(np.mean(curr * curr))),
        "nonzero_count": int(np.sum(np.abs(curr) > 1.0e-12)),
    }]
    # Use the same closed matrix one-step form as the SOO validation controls.
    from .soo_validation import _step_matrix
    for step in range(1, int(steps) + 1):
        phase = (step - 1) % 3
        M = _step_matrix(state, phase, epsilon=epsilon, stiffness_lambda=stiffness_lambda)
        v = M @ np.concatenate([curr, prev])
        next_curr = v[:n]
        prev, curr = curr, next_curr
        ever |= np.abs(curr) > 1.0e-12
        run_max = max(run_max, float(np.max(np.abs(curr))))
        if step <= 20 or step % 25 == 0 or step == int(steps):
            layer_rows.append({
                "step": int(step),
                "phase": int(step % 3),
                "max_abs_phi": float(np.max(np.abs(curr))),
                "rms_phi": float(np.sqrt(np.mean(curr * curr))),
                "nonzero_count": int(np.sum(np.abs(curr) > 1.0e-12)),
            })
    point_rows = []
    # Re-run or approximate not needed; record profile categories externally by joining if desired.
    for point in range(n):
        point_rows.append({"point": int(point), "initial_profile_value": float(profile[point]), "ever_nonzero": bool(ever[point])})
    summary = PhaseConsistentLedgerSummary(
        omega=omega,
        cos_omega=float(cos_omega),
        ledger_policy="Phi_prev = cos(omega) * Phi_curr profile, identity-limit phase-consistent ledger",
        steps=int(steps),
        initial_max_abs=float(initial_max),
        run_max_abs=float(run_max),
        final_max_abs=float(np.max(np.abs(curr))),
        growth_factor_over_initial=float(run_max / initial_max) if initial_max > 0 else 0.0,
        all_points_ever_nonzero=bool(np.all(ever)),
        ever_nonzero_count=int(np.sum(ever)),
        n_points=n,
        interpretation="This identity-limit phase ledger is a diagnostic only. For the rank-3 association state, it does not generally suppress growth unless the profile is also compatible with the association-cyclic modes; it remains oscillatory and is not a settling mechanism.",
    )
    return summary, layer_rows, point_rows


def write_csv(path: str | Path, rows: Sequence[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = tuple(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_direct_recurrent_initialization(
    *,
    output_dir: str | Path,
    path_length: int = 31,
    orientation: str = "same",
    epsilon: float = 0.1,
    stiffness_lambda: float = 1.0,
    period_max: int = 128,
    exact_tolerance: float = 1.0e-9,
    phase_consistent_steps: int = 600,
) -> DirectRecurrentInitializationReport:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _overlay, state, path_report, supports, _source = load_l_path_state(path_length, orientation)
    profile, spec, profile_rows = build_interpolated_profile(state=state, path_report=path_report, supports=supports)
    M = cyclic_matrix(state, epsilon=epsilon, stiffness_lambda=stiffness_lambda)
    solve_rows, solve_detail_rows = solve_recurrent_profile(M_cycle=M, profile=profile, path_points=path_report.path_points, period_max=period_max, exact_tolerance=exact_tolerance)
    best_full_current = min((r for r in solve_rows if r.constraint_policy.startswith("current_profile_only") and r.constraint_policy.endswith("full_residual")), key=lambda r: r.full_max_abs_residual)
    best_witness_current = min((r for r in solve_rows if r.constraint_policy.startswith("current_profile_only") and "witness_residual_only" in r.constraint_policy), key=lambda r: r.witness_max_abs_residual)
    best_full_both = min((r for r in solve_rows if r.constraint_policy.startswith("both_ledgers_profile") and r.constraint_policy.endswith("full_residual")), key=lambda r: r.full_max_abs_residual)
    best_witness_both = min((r for r in solve_rows if r.constraint_policy.startswith("both_ledgers_profile") and "witness_residual_only" in r.constraint_policy), key=lambda r: r.witness_max_abs_residual)
    phase_summary, layer_rows, point_rows = simulate_phase_consistent_ledger(state=state, profile=profile, epsilon=epsilon, stiffness_lambda=stiffness_lambda, steps=phase_consistent_steps)
    artifacts = {
        "report": "DIRECT_RECURRENT_INITIALIZATION_REPORT.json",
        "profile_rows": "interpolated_profile_rows.csv",
        "recurrent_solve_rows": "direct_recurrent_solve_rows.csv",
        "phase_consistent_layer_rows": "phase_consistent_layer_rows.csv",
        "phase_consistent_point_rows": "phase_consistent_point_rows.csv",
    }
    conclusions = (
        "The interpolated profile is a better physical initial profile than a zero-to-source jump, but under the current conservative SOO map it is not automatically a finite-period recurrent state.",
        "Exact finite-cycle recurrence subject to the full interpolated current-profile constraints must be checked directly with (F_cyc^P - I)v = 0.",
        "A witness-only solve is diagnostic only; it can hide residuals in non-witness degrees of freedom and must not certify a full measurement initial state.",
        "The identity-limit phase-consistent ledger Phi_prev = cos(omega) Phi_curr is not sufficient for rank-3 association-cyclic compatibility; it remains oscillatory and may still show modal amplification.",
    )
    report = DirectRecurrentInitializationReport(
        report_schema="direct_recurrent_initialization_report.v0_1",
        report_id="direct_recurrent_initialization_L%d_%s" % (int(path_length), str(orientation)),
        profile_spec=spec,
        epsilon=float(epsilon),
        stiffness_lambda=float(stiffness_lambda),
        period_max=int(period_max),
        exact_tolerance=float(exact_tolerance),
        best_full_current_only=best_full_current,
        best_witness_current_only=best_witness_current,
        best_full_both_ledgers=best_full_both,
        best_witness_both_ledgers=best_witness_both,
        exact_full_recurrent_profile_found=bool(any(r.exact_full_passed for r in solve_rows if "full_residual" in r.constraint_policy)),
        exact_witness_recurrent_profile_found=bool(any(r.exact_witness_passed for r in solve_rows)),
        phase_consistent_ledger=phase_summary,
        conclusions=conclusions,
        artifacts=artifacts,
    )
    (output / artifacts["report"]).write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(output / artifacts["profile_rows"], profile_rows)
    write_csv(output / artifacts["recurrent_solve_rows"], solve_detail_rows)
    write_csv(output / artifacts["phase_consistent_layer_rows"], layer_rows)
    write_csv(output / artifacts["phase_consistent_point_rows"], point_rows)
    (output / "README.md").write_text(
        "# Direct recurrent initialization solve\n\n"
        "This package tests the interpolated-profile initialization hypothesis as a direct recurrent two-ledger solve. "
        "The witness set and profile constraints do not alter SOO.\n\n"
        f"Report hash: `{report.fingerprint()}`\n",
        encoding="utf-8",
    )
    return report
