from __future__ import annotations

import csv
import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

import scalar_field_geometry as sfg
from .active_association import build_A_theta, operator_hash
from .fingerprints import array_hash, stable_json_hash
from .recurrent_initialization_solver import build_interpolated_profile
from .soo_validation import load_l_path_state


@dataclass(frozen=True)
class FeedbackSOOSearchConfig:
    report_schema: str
    framework_version: str
    search_level: str
    path_length: int
    orientation: str
    epsilon: float
    period_max: int
    exact_tolerance: float
    k_grid: tuple[float, ...]
    grid_mode: str
    max_cartesian_candidates: int
    candidate_count: int
    objective_terms: tuple[str, ...]
    forbidden_objective_terms: tuple[str, ...]
    leakage_flags: dict[str, bool]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class FeedbackSOOSearchReport:
    report_schema: str
    report_id: str
    config_hash: str
    association_state_hash: str
    profile_hash: str
    path_report_hash: str
    support_count: int
    n_points: int
    state_dimension: int
    best_by_full_current_residual: dict[str, Any]
    best_by_witness_current_residual: dict[str, Any]
    best_by_full_both_ledgers_residual: dict[str, Any]
    best_by_witness_both_ledgers_residual: dict[str, Any]
    candidates_tested: int
    candidates_with_all_stability_bounds: int
    candidates_with_exact_full_current: int
    candidates_with_exact_witness_current: int
    candidates_spectral_radius_lt_one: int
    candidates_spectral_radius_near_one: int
    candidates_spectral_radius_gt_one: int
    baseline_like_candidate: dict[str, Any] | None
    conclusions: tuple[str, ...]
    artifacts: dict[str, str]
    leakage_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def write_csv(path: str | Path, rows: Sequence[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    field_order: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                field_order.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_order, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _step_matrix_phase_scalar(
    state: sfg.FrozenAssociationState,
    phase: int,
    *,
    epsilon: float,
    k_phase: float,
) -> np.ndarray:
    """Closed-form two-ledger SOO step with K_theta = k_theta I.

    This preserves the locked association-indexed SOO form.  It changes only the
    scalar stiffness coefficient assigned to the active phase; it does not give
    path points, supports, midpoint points, or verdict classes special handling.
    """

    n = int(state.n_points)
    A_curr = build_A_theta(state, int(phase) % 3)
    A_next = build_A_theta(state, (int(phase) + 1) % 3)
    eps2 = float(epsilon) ** 2
    coeff = 2.0 - eps2 * float(k_phase)
    top_left = A_next @ (coeff * np.eye(n, dtype=np.float64))
    top_right = -A_next @ A_curr
    top = np.hstack([top_left, top_right])
    bottom = np.hstack([np.eye(n, dtype=np.float64), np.zeros((n, n), dtype=np.float64)])
    return np.vstack([top, bottom])


def cyclic_matrix_phase_scalar(
    state: sfg.FrozenAssociationState,
    *,
    epsilon: float,
    k_by_phase: Sequence[float],
) -> np.ndarray:
    if len(k_by_phase) != 3:
        raise ValueError("k_by_phase must contain exactly three phase stiffness scalars")
    m0 = _step_matrix_phase_scalar(state, 0, epsilon=epsilon, k_phase=float(k_by_phase[0]))
    m1 = _step_matrix_phase_scalar(state, 1, epsilon=epsilon, k_phase=float(k_by_phase[1]))
    m2 = _step_matrix_phase_scalar(state, 2, epsilon=epsilon, k_phase=float(k_by_phase[2]))
    return m2 @ m1 @ m0


def _candidate_grid(k_grid: Sequence[float], grid_mode: str, max_cartesian_candidates: int) -> list[tuple[float, float, float]]:
    values = tuple(float(k) for k in k_grid)
    if not values:
        raise ValueError("k_grid cannot be empty")
    if grid_mode == "tied":
        return [(k, k, k) for k in values]
    if grid_mode == "cartesian":
        candidates = list(itertools.product(values, values, values))
        if len(candidates) > int(max_cartesian_candidates):
            raise ValueError(
                f"Cartesian k grid would create {len(candidates)} candidates, exceeding "
                f"max_cartesian_candidates={int(max_cartesian_candidates)}. "
                "Use --grid-mode tied or raise the cap explicitly."
            )
        return [(float(a), float(b), float(c)) for a, b, c in candidates]
    raise ValueError(f"Unsupported grid_mode: {grid_mode}")


def _stability_bounds(epsilon: float, k_by_phase: Sequence[float]) -> tuple[bool, tuple[bool, ...], float, float]:
    eps2 = float(epsilon) ** 2
    vals = tuple(eps2 * float(k) for k in k_by_phase)
    phase_pass = tuple(bool(0.0 < v < 4.0) for v in vals)
    return bool(all(phase_pass)), phase_pass, float(min(vals)), float(max(vals))


def _spectral_rows_and_summary(
    M: np.ndarray,
    *,
    candidate_index: int,
    k_by_phase: Sequence[float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    vals = np.linalg.eigvals(M)
    mods = np.abs(vals)
    near = np.abs(mods - 1.0) <= 1.0e-10
    rows = []
    for i, val in enumerate(vals):
        rows.append(
            {
                "candidate_index": int(candidate_index),
                "k0": float(k_by_phase[0]),
                "k1": float(k_by_phase[1]),
                "k2": float(k_by_phase[2]),
                "eigen_index": int(i),
                "real": float(val.real),
                "imag": float(val.imag),
                "modulus": float(abs(val)),
                "angle": float(math.atan2(val.imag, val.real)),
            }
        )
    summary = {
        "spectral_radius": float(np.max(mods)),
        "min_modulus": float(np.min(mods)),
        "max_modulus": float(np.max(mods)),
        "mean_modulus": float(np.mean(mods)),
        "median_modulus": float(np.median(mods)),
        "count_modulus_near_one_1e_10": int(np.sum(near)),
        "count_modulus_gt_one_plus_1e_10": int(np.sum(mods > 1.0 + 1.0e-10)),
        "count_modulus_lt_one_minus_1e_10": int(np.sum(mods < 1.0 - 1.0e-10)),
    }
    return rows, summary


def _constraint_system(profile: np.ndarray, policy: str) -> tuple[np.ndarray, np.ndarray]:
    n = int(profile.size)
    if policy == "current_profile_only":
        return np.arange(n, dtype=np.int64), np.asarray(profile, dtype=np.float64)
    if policy == "both_ledgers_profile":
        idx = np.concatenate([np.arange(n, dtype=np.int64), n + np.arange(n, dtype=np.int64)])
        vals = np.concatenate([profile, profile]).astype(np.float64)
        return idx, vals
    raise ValueError(f"Unknown constraint policy: {policy}")


def _solve_min_recurrence(
    A_full: np.ndarray,
    constrained_idx: np.ndarray,
    constrained_vals: np.ndarray,
    *,
    residual_rows: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    A_used = A_full if residual_rows is None else A_full[residual_rows, :]
    ncols = int(A_full.shape[1])
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
    full_residual = A_full @ v
    used_residual = A_used @ v
    return v, {
        "free_dim": int(free.size),
        "constrained_dim": int(constrained_idx.size),
        "used_l2_residual": float(np.linalg.norm(used_residual)),
        "used_rms_residual": float(np.sqrt(np.mean(used_residual * used_residual))) if used_residual.size else 0.0,
        "used_max_abs_residual": float(np.max(np.abs(used_residual))) if used_residual.size else 0.0,
        "full_l2_residual": float(np.linalg.norm(full_residual)),
        "full_rms_residual": float(np.sqrt(np.mean(full_residual * full_residual))) if full_residual.size else 0.0,
        "full_max_abs_residual": float(np.max(np.abs(full_residual))) if full_residual.size else 0.0,
    }


def _residual_stats(residual: np.ndarray) -> dict[str, float]:
    residual = np.asarray(residual, dtype=np.float64)
    return {
        "l2_residual": float(np.linalg.norm(residual)),
        "rms_residual": float(np.sqrt(np.mean(residual * residual))) if residual.size else 0.0,
        "max_abs_residual": float(np.max(np.abs(residual))) if residual.size else 0.0,
    }


def _solve_candidate_recurrence(
    M_cycle: np.ndarray,
    *,
    candidate_index: int,
    k_by_phase: Sequence[float],
    profile: np.ndarray,
    path_points: Sequence[int],
    period_max: int,
    exact_tolerance: float,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    n = int(profile.size)
    eye = np.eye(2 * n, dtype=np.float64)
    M_power = np.eye(2 * n, dtype=np.float64)
    witness_points = np.asarray(tuple(int(p) for p in path_points), dtype=np.int64)
    witness_rows = np.concatenate([witness_points, n + witness_points])
    rows: list[dict[str, Any]] = []
    best: dict[str, dict[str, Any]] = {}
    policies = ("current_profile_only", "both_ledgers_profile")
    scopes = ("full_residual", "witness_residual_only")
    for period in range(1, int(period_max) + 1):
        M_power = M_cycle @ M_power
        A = M_power - eye
        for policy in policies:
            cidx, cvals = _constraint_system(profile, policy)
            for scope in scopes:
                residual_selector = None if scope == "full_residual" else witness_rows
                v, solve_stats = _solve_min_recurrence(A, cidx, cvals, residual_rows=residual_selector)
                residual_full = A @ v
                residual_witness = residual_full[witness_rows]
                full_stats = _residual_stats(residual_full)
                witness_stats = _residual_stats(residual_witness)
                row = {
                    "candidate_index": int(candidate_index),
                    "k0": float(k_by_phase[0]),
                    "k1": float(k_by_phase[1]),
                    "k2": float(k_by_phase[2]),
                    "period_cycles": int(period),
                    "constraint_policy": policy,
                    "solve_scope": scope,
                    "full_l2_residual": full_stats["l2_residual"],
                    "full_rms_residual": full_stats["rms_residual"],
                    "full_max_abs_residual": full_stats["max_abs_residual"],
                    "witness_l2_residual": witness_stats["l2_residual"],
                    "witness_rms_residual": witness_stats["rms_residual"],
                    "witness_max_abs_residual": witness_stats["max_abs_residual"],
                    "free_dim": solve_stats["free_dim"],
                    "constrained_dim": solve_stats["constrained_dim"],
                    "solution_max_abs": float(np.max(np.abs(v))) if v.size else 0.0,
                    "exact_full_passed": bool(full_stats["max_abs_residual"] <= float(exact_tolerance)),
                    "exact_witness_passed": bool(witness_stats["max_abs_residual"] <= float(exact_tolerance)),
                    "charge_verdict_target_used": False,
                    "path_length_target_used": False,
                    "center_zero_target_used": False,
                    "same_opposite_label_used_in_optimizer": False,
                }
                rows.append(row)
                key = f"{policy}::{scope}"
                score_key = "full_max_abs_residual" if scope == "full_residual" else "witness_max_abs_residual"
                if key not in best or float(row[score_key]) < float(best[key][score_key]):
                    best[key] = row
    return rows, best


def _compact_candidate_row(
    *,
    candidate_index: int,
    k_by_phase: Sequence[float],
    epsilon: float,
    spectrum_summary: dict[str, Any],
    best: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    stability_passed, phase_pass, eps2k_min, eps2k_max = _stability_bounds(epsilon, k_by_phase)
    current_full = best["current_profile_only::full_residual"]
    current_witness = best["current_profile_only::witness_residual_only"]
    both_full = best["both_ledgers_profile::full_residual"]
    both_witness = best["both_ledgers_profile::witness_residual_only"]
    return {
        "candidate_index": int(candidate_index),
        "k0": float(k_by_phase[0]),
        "k1": float(k_by_phase[1]),
        "k2": float(k_by_phase[2]),
        "eps2k_min": float(eps2k_min),
        "eps2k_max": float(eps2k_max),
        "phase0_stability_bound_passed": bool(phase_pass[0]),
        "phase1_stability_bound_passed": bool(phase_pass[1]),
        "phase2_stability_bound_passed": bool(phase_pass[2]),
        "all_phase_stability_bounds_passed": bool(stability_passed),
        **spectrum_summary,
        "best_full_current_period": int(current_full["period_cycles"]),
        "best_full_current_max_abs_residual": float(current_full["full_max_abs_residual"]),
        "best_witness_current_period": int(current_witness["period_cycles"]),
        "best_witness_current_max_abs_residual": float(current_witness["witness_max_abs_residual"]),
        "best_full_both_ledgers_period": int(both_full["period_cycles"]),
        "best_full_both_ledgers_max_abs_residual": float(both_full["full_max_abs_residual"]),
        "best_witness_both_ledgers_period": int(both_witness["period_cycles"]),
        "best_witness_both_ledgers_max_abs_residual": float(both_witness["witness_max_abs_residual"]),
        "exact_full_current_found": bool(current_full["exact_full_passed"]),
        "exact_witness_current_found": bool(current_witness["exact_witness_passed"]),
        "exact_full_both_ledgers_found": bool(both_full["exact_full_passed"]),
        "exact_witness_both_ledgers_found": bool(both_witness["exact_witness_passed"]),
        "charge_verdict_target_used": False,
        "path_length_target_used": False,
        "center_zero_target_used": False,
        "same_opposite_label_used_in_optimizer": False,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_feedback_soo_search(
    *,
    output_dir: str | Path,
    path_length: int = 31,
    orientation: str = "same",
    epsilon: float = 0.1,
    period_max: int = 512,
    exact_tolerance: float = 1.0e-9,
    k_grid: Sequence[float] = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0),
    grid_mode: str = "tied",
    max_cartesian_candidates: int = 1000,
    emit_spectrum_rows: bool = True,
    emit_recurrence_rows: bool = True,
) -> FeedbackSOOSearchReport:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    orientation = str(orientation)
    _overlay, state, path_report, supports, _source = load_l_path_state(path_length, orientation)
    profile, profile_spec, profile_rows = build_interpolated_profile(
        state=state,
        path_report=path_report,
        supports=supports,
    )
    candidates = _candidate_grid(k_grid, grid_mode, max_cartesian_candidates)
    leakage_flags = {
        "charge_verdict_target_used": False,
        "path_length_target_used": False,
        "center_zero_target_used": False,
        "same_opposite_labels_used_in_optimizer": False,
        "path_points_updated_specially": False,
        "support_points_updated_specially": False,
    }
    config = FeedbackSOOSearchConfig(
        report_schema="feedback_soo_config.v0_1",
        framework_version="0.1.15-feedback-soo-stiffness-search",
        search_level="level_1_phase_scalar_stiffness_grid",
        path_length=int(path_length),
        orientation=orientation,
        epsilon=float(epsilon),
        period_max=int(period_max),
        exact_tolerance=float(exact_tolerance),
        k_grid=tuple(float(k) for k in k_grid),
        grid_mode=str(grid_mode),
        max_cartesian_candidates=int(max_cartesian_candidates),
        candidate_count=len(candidates),
        objective_terms=(
            "cyclic_return_spectrum",
            "current_profile_full_recurrence_residual",
            "current_profile_witness_recurrence_residual",
            "both_ledgers_profile_full_recurrence_residual",
            "both_ledgers_profile_witness_recurrence_residual",
        ),
        forbidden_objective_terms=(
            "charge verdict",
            "path-length change target",
            "center-zero target",
            "same/opposite theorem label",
            "support attraction/repulsion label",
        ),
        leakage_flags=leakage_flags,
        notes=(
            "The orientation argument selects the declarative overlay to load; it is not used as an optimizer target or ranking signal.",
            "K_theta is restricted to k_theta times the identity, so no point class receives special SOO handling.",
            "This is a constrained stiffness search only, not a charge run and not an induced feedback-closure proof.",
        ),
    )

    candidate_rows: list[dict[str, Any]] = []
    spectrum_rows: list[dict[str, Any]] = []
    recurrence_rows: list[dict[str, Any]] = []
    for idx, k_by_phase in enumerate(candidates):
        M = cyclic_matrix_phase_scalar(state, epsilon=epsilon, k_by_phase=k_by_phase)
        spec_rows, spectrum_summary = _spectral_rows_and_summary(M, candidate_index=idx, k_by_phase=k_by_phase)
        rec_rows, best = _solve_candidate_recurrence(
            M,
            candidate_index=idx,
            k_by_phase=k_by_phase,
            profile=profile,
            path_points=path_report.path_points,
            period_max=period_max,
            exact_tolerance=exact_tolerance,
        )
        candidate_rows.append(
            _compact_candidate_row(
                candidate_index=idx,
                k_by_phase=k_by_phase,
                epsilon=epsilon,
                spectrum_summary=spectrum_summary,
                best=best,
            )
        )
        if emit_spectrum_rows:
            spectrum_rows.extend(spec_rows)
        if emit_recurrence_rows:
            recurrence_rows.extend(rec_rows)

    best_full_current = min(candidate_rows, key=lambda r: float(r["best_full_current_max_abs_residual"]))
    best_witness_current = min(candidate_rows, key=lambda r: float(r["best_witness_current_max_abs_residual"]))
    best_full_both = min(candidate_rows, key=lambda r: float(r["best_full_both_ledgers_max_abs_residual"]))
    best_witness_both = min(candidate_rows, key=lambda r: float(r["best_witness_both_ledgers_max_abs_residual"]))
    baseline_like = None
    for row in candidate_rows:
        if abs(float(row["k0"]) - 1.0) <= 1.0e-15 and abs(float(row["k1"]) - 1.0) <= 1.0e-15 and abs(float(row["k2"]) - 1.0) <= 1.0e-15:
            baseline_like = row
            break

    artifacts = {
        "config": "FEEDBACK_SOO_CONFIG.json",
        "search_report": "FEEDBACK_SOO_SEARCH_REPORT.json",
        "grid_report": "K_SEARCH_GRID_REPORT.json",
        "candidate_spectrum_report": "K_CANDIDATE_SPECTRUM_REPORT.json",
        "recurrence_residual_report": "K_RECURRENCE_RESIDUAL_REPORT.json",
        "candidate_rows": "k_candidate_rows.csv",
        "spectrum_rows": "spectrum_rows.csv",
        "recurrence_residual_rows": "recurrence_residual_rows.csv",
        "profile_rows": "interpolated_profile_rows.csv",
        "feedback_closure_report": "FEEDBACK_CLOSURE_REPORT.json",
        "initialization_settling_report": "INITIALIZATION_SETTLING_REPORT.json",
    }

    spectral_lt = int(sum(float(r["spectral_radius"]) < 1.0 - 1.0e-10 for r in candidate_rows))
    spectral_near = int(sum(abs(float(r["spectral_radius"]) - 1.0) <= 1.0e-10 for r in candidate_rows))
    spectral_gt = int(sum(float(r["spectral_radius"]) > 1.0 + 1.0e-10 for r in candidate_rows))
    conclusions = (
        "This search changes only the phase-scalar stiffness K_theta = k_theta I; SOO remains whole-field and point-blind.",
        "Spectral radius below one would be evidence of forward damping/settling; unit-modulus or above-one spectra do not certify settling.",
        "A smaller finite-period residual is an initialization-search result only. It is not a charge verdict and not a path-length accommodation claim.",
        "Level 1 does not close K through response burden. It selects candidate stiffness values for a later induced feedback-closure test.",
    )
    report = FeedbackSOOSearchReport(
        report_schema="feedback_soo_search_report.v0_1",
        report_id=f"feedback_soo_search_L{int(path_length)}_{orientation}_{grid_mode}",
        config_hash=config.fingerprint(),
        association_state_hash=state.fingerprint,
        profile_hash=array_hash(profile),
        path_report_hash=stable_json_hash(getattr(path_report, "to_dict", lambda: asdict(path_report))()),
        support_count=int(len(supports)),
        n_points=int(state.n_points),
        state_dimension=int(2 * state.n_points),
        best_by_full_current_residual=best_full_current,
        best_by_witness_current_residual=best_witness_current,
        best_by_full_both_ledgers_residual=best_full_both,
        best_by_witness_both_ledgers_residual=best_witness_both,
        candidates_tested=int(len(candidate_rows)),
        candidates_with_all_stability_bounds=int(sum(bool(r["all_phase_stability_bounds_passed"]) for r in candidate_rows)),
        candidates_with_exact_full_current=int(sum(bool(r["exact_full_current_found"]) for r in candidate_rows)),
        candidates_with_exact_witness_current=int(sum(bool(r["exact_witness_current_found"]) for r in candidate_rows)),
        candidates_spectral_radius_lt_one=spectral_lt,
        candidates_spectral_radius_near_one=spectral_near,
        candidates_spectral_radius_gt_one=spectral_gt,
        baseline_like_candidate=baseline_like,
        conclusions=conclusions,
        artifacts=artifacts,
        leakage_flags=leakage_flags,
    )

    _write_json(output / artifacts["config"], config)
    _write_json(
        output / artifacts["grid_report"],
        {
            "report_schema": "k_search_grid_report.v0_1",
            "config_hash": config.fingerprint(),
            "candidate_count": len(candidates),
            "k_candidates": [
                {"candidate_index": i, "k0": k0, "k1": k1, "k2": k2}
                for i, (k0, k1, k2) in enumerate(candidates)
            ],
            "leakage_flags": leakage_flags,
        },
    )
    _write_json(
        output / artifacts["candidate_spectrum_report"],
        {
            "report_schema": "k_candidate_spectrum_report.v0_1",
            "config_hash": config.fingerprint(),
            "candidate_count": len(candidate_rows),
            "spectral_radius_lt_one_count": spectral_lt,
            "spectral_radius_near_one_count": spectral_near,
            "spectral_radius_gt_one_count": spectral_gt,
            "candidate_summary_rows_hash": stable_json_hash(candidate_rows),
            "spectrum_rows_hash": stable_json_hash(spectrum_rows) if spectrum_rows else None,
            "leakage_flags": leakage_flags,
        },
    )
    _write_json(
        output / artifacts["recurrence_residual_report"],
        {
            "report_schema": "k_recurrence_residual_report.v0_1",
            "config_hash": config.fingerprint(),
            "exact_tolerance": float(exact_tolerance),
            "period_max": int(period_max),
            "best_by_full_current_residual": best_full_current,
            "best_by_witness_current_residual": best_witness_current,
            "best_by_full_both_ledgers_residual": best_full_both,
            "best_by_witness_both_ledgers_residual": best_witness_both,
            "candidate_summary_rows_hash": stable_json_hash(candidate_rows),
            "recurrence_rows_hash": stable_json_hash(recurrence_rows) if recurrence_rows else None,
            "leakage_flags": leakage_flags,
        },
    )
    _write_json(
        output / artifacts["feedback_closure_report"],
        {
            "report_schema": "feedback_closure_report.v0_1",
            "status": "not_run",
            "reason": "Level 1 phase-scalar grid search does not implement K -> SOO response -> response burden -> K' closure.",
            "next_required_stage": "level_3_induced_stiffness_closure",
            "leakage_flags": leakage_flags,
        },
    )
    _write_json(
        output / artifacts["initialization_settling_report"],
        {
            "report_schema": "initialization_settling_report.v0_1",
            "status": "not_certified",
            "reason": "This stage ranks cyclic spectra and finite-period recurrence residuals. Forward SOO settling must be tested separately after selecting candidate K values.",
            "best_candidate_for_followup": best_full_current,
            "leakage_flags": leakage_flags,
        },
    )
    _write_json(output / artifacts["search_report"], report)
    write_csv(output / artifacts["candidate_rows"], candidate_rows)
    write_csv(output / artifacts["spectrum_rows"], spectrum_rows)
    write_csv(output / artifacts["recurrence_residual_rows"], recurrence_rows)
    write_csv(output / artifacts["profile_rows"], profile_rows)
    (output / "README.md").write_text(
        "# Feedback-SOO stiffness search\n\n"
        "This is a SOO-only phase-scalar stiffness search.  It does not run a charge theorem test, "
        "does not use a path-length target, and does not update path points specially.\n\n"
        f"Report hash: `{report.fingerprint()}`\n",
        encoding="utf-8",
    )
    return report
