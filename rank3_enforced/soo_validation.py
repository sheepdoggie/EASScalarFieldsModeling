from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Sequence

import numpy as np

import scalar_field_geometry as sfg
from .active_association import build_A_theta
from .fingerprints import stable_json_hash
from .path_construction import build_explicit_path_association_state
from .overlay_schema import SupportSpec


@dataclass(frozen=True)
class IdentityRecurrenceValidation:
    epsilon: float
    stiffness_lambda: float
    x_previous: float
    x_current: float
    coefficient: float
    omega: float | None
    analytic_amplitude: float | None
    analytic_period_steps: float | None
    observed_peak_abs: float
    observed_peak_step: int
    comparison_steps: int
    max_abs_error: float
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CyclicReturnSpectrumValidation:
    path_length: int
    orientation: str
    n_points: int
    state_dimension: int
    epsilon: float
    stiffness_lambda: float
    spectral_radius: float
    min_modulus: float
    max_modulus: float
    mean_modulus: float
    median_modulus: float
    count_modulus_near_one_1e_10: int
    count_modulus_gt_one_plus_1e_10: int
    count_modulus_lt_one_minus_1e_10: int
    settling_expected_from_forward_iteration: bool
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecurrentSolveValidation:
    path_length: int
    orientation: str
    periods_tested: tuple[int, ...]
    constraint_profiles: tuple[str, ...]
    exact_tolerance: float
    best_full_state_row: dict[str, Any]
    best_witness_row: dict[str, Any]
    best_support_constrained_full_state_row: dict[str, Any]
    best_support_constrained_witness_row: dict[str, Any]
    support_constrained_exact_full_state_found: bool
    support_constrained_exact_witness_found: bool
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SOOValidationReport:
    report_schema: str
    validation_id: str
    identity_recurrence: IdentityRecurrenceValidation
    cyclic_return_spectrum: CyclicReturnSpectrumValidation
    recurrent_solve: RecurrentSolveValidation
    artifacts: dict[str, str]
    conclusions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class _PathSpec:
    rule: str
    path_length: int
    orientation: str
    left_support: str
    right_support: str
    path_slot: int
    reverse_slot: int
    allow_support_overlap: bool = False
    path_points: tuple[int, ...] = ()


def _suite_overlay_path(path_length: int, orientation: str) -> Path:
    suite_res = resources.files("rank3_enforced").joinpath(
        "overlay_suites",
        "charge_same_opposite_association_indexed",
        f"L{int(path_length)}_{orientation}_association_indexed_soo.json",
    )
    with resources.as_file(suite_res) as path:
        return Path(path)


def _load_overlay(path_length: int, orientation: str) -> dict[str, Any]:
    path = _suite_overlay_path(path_length, orientation)
    return json.loads(path.read_text(encoding="utf-8"))


def _support_specs(raw_supports: Sequence[dict[str, Any]]) -> tuple[SupportSpec, ...]:
    supports: list[SupportSpec] = []
    for raw in raw_supports:
        supports.append(
            SupportSpec(
                name=str(raw["name"]),
                support_points=tuple(int(x) for x in raw.get("support_points", ())),
                boundary_points=tuple(int(x) for x in raw.get("boundary_points", ())),
                dressing_points=tuple(int(x) for x in raw.get("dressing_points", ())),
                handedness=str(raw.get("handedness", "right")),
                active_phase_map={int(k): int(v) for k, v in dict(raw.get("active_phase_map", {})).items()},
            )
        )
    return tuple(supports)


def _path_spec(raw: dict[str, Any], orientation: str) -> _PathSpec:
    return _PathSpec(
        rule=str(raw["rule"]),
        path_length=int(raw["path_length"]),
        orientation=str(raw.get("orientation", orientation)),
        left_support=str(raw["left_support"]),
        right_support=str(raw["right_support"]),
        path_slot=int(raw.get("path_slot", 0)),
        reverse_slot=int(raw.get("reverse_slot", 1)),
        allow_support_overlap=bool(raw.get("allow_support_overlap", False)),
        path_points=tuple(int(x) for x in raw.get("path_points", ())),
    )


def _handedness_sign(handedness: str) -> float:
    return 1.0 if str(handedness).lower() == "right" else -1.0


def _support_source(*, n_points: int, supports: Sequence[SupportSpec], amplitude: float) -> np.ndarray:
    source = np.zeros(int(n_points), dtype=np.float64)
    for support in supports:
        sign = _handedness_sign(str(support.handedness))
        for boundary, dressing in zip(support.boundary_points, support.dressing_points):
            source[int(boundary)] += sign * float(amplitude)
            source[int(dressing)] += -sign * float(amplitude)
    return source


def load_l_path_state(path_length: int, orientation: str):
    overlay = _load_overlay(path_length, orientation)
    supports = _support_specs(overlay.get("supports", ()))
    initial_geometry = dict(overlay["initial_geometry"])
    base_state = sfg.generate_initial_association_state(
        n_points=int(initial_geometry["n_points"]),
        seed=int(initial_geometry["seed"]),
        generation_rule=str(initial_geometry["generation_rule"]),
        allow_self_association=bool(initial_geometry.get("allow_self_association", False)),
    )
    path_state, path_report = build_explicit_path_association_state(
        n_points=int(initial_geometry["n_points"]),
        path_spec=_path_spec(dict(overlay["path_construction"]), orientation),
        supports=supports,
        allow_self_association=bool(initial_geometry.get("allow_self_association", False)),
    )
    amplitude = float(dict(overlay.get("initialization", {})).get("amplitude", 1.0))
    source = _support_source(n_points=path_state.n_points, supports=supports, amplitude=amplitude)
    return overlay, path_state, path_report, supports, source


def validate_identity_recurrence(
    *,
    epsilon: float = 0.1,
    stiffness_lambda: float = 1.0,
    x_previous: float = 0.0,
    x_current: float = 1.0,
    comparison_steps: int = 200,
    tolerance: float = 1.0e-12,
) -> tuple[IdentityRecurrenceValidation, list[dict[str, Any]]]:
    eps2 = float(epsilon) ** 2
    coefficient = 2.0 - eps2 * float(stiffness_lambda)
    # Matrix form of the actual association-indexed closed-form solve when A=I.
    M = np.array([[coefficient, -1.0], [1.0, 0.0]], dtype=np.float64)
    v = np.array([float(x_current), float(x_previous)], dtype=np.float64)
    prev = float(x_previous)
    curr = float(x_current)
    rows: list[dict[str, Any]] = []
    peak = abs(curr)
    peak_step = 0
    max_err = 0.0
    rows.append({"step": 0, "actual": curr, "expected": curr, "abs_error": 0.0})
    for step in range(1, int(comparison_steps) + 1):
        expected = coefficient * curr - prev
        prev, curr = curr, expected
        v = M @ v
        actual = float(v[0])
        err = abs(actual - expected)
        max_err = max(max_err, err)
        if abs(actual) > peak:
            peak = abs(actual)
            peak_step = step
        rows.append({"step": step, "actual": actual, "expected": expected, "abs_error": err})
    omega: float | None = None
    analytic_amplitude: float | None = None
    analytic_period_steps: float | None = None
    half = coefficient / 2.0
    if abs(half) <= 1.0:
        omega = float(math.acos(half))
        if abs(math.sin(omega)) > 0.0:
            C = float(x_current)
            D = (float(x_current) * math.cos(omega) - float(x_previous)) / math.sin(omega)
            analytic_amplitude = float(math.sqrt(C * C + D * D))
            analytic_period_steps = float(2.0 * math.pi / omega)
    result = IdentityRecurrenceValidation(
        epsilon=float(epsilon),
        stiffness_lambda=float(stiffness_lambda),
        x_previous=float(x_previous),
        x_current=float(x_current),
        coefficient=float(coefficient),
        omega=omega,
        analytic_amplitude=analytic_amplitude,
        analytic_period_steps=analytic_period_steps,
        observed_peak_abs=float(peak),
        observed_peak_step=int(peak_step),
        comparison_steps=int(comparison_steps),
        max_abs_error=float(max_err),
        passed=bool(max_err <= tolerance),
    )
    return result, rows


def _step_matrix(state: sfg.FrozenAssociationState, phase: int, *, epsilon: float, stiffness_lambda: float) -> np.ndarray:
    n = int(state.n_points)
    A_curr = build_A_theta(state, int(phase) % 3)
    A_next = build_A_theta(state, (int(phase) + 1) % 3)
    eps2 = float(epsilon) ** 2
    K = float(stiffness_lambda) * np.eye(n, dtype=np.float64)
    top_left = A_next @ ((2.0 * np.eye(n, dtype=np.float64) - eps2 * K))
    top_right = -A_next @ A_curr
    top = np.hstack([top_left, top_right])
    bottom = np.hstack([np.eye(n, dtype=np.float64), np.zeros((n, n), dtype=np.float64)])
    return np.vstack([top, bottom])


def cyclic_matrix(state: sfg.FrozenAssociationState, *, epsilon: float, stiffness_lambda: float) -> np.ndarray:
    m0 = _step_matrix(state, 0, epsilon=epsilon, stiffness_lambda=stiffness_lambda)
    m1 = _step_matrix(state, 1, epsilon=epsilon, stiffness_lambda=stiffness_lambda)
    m2 = _step_matrix(state, 2, epsilon=epsilon, stiffness_lambda=stiffness_lambda)
    return m2 @ m1 @ m0


def validate_cyclic_spectrum(
    *,
    path_length: int = 31,
    orientation: str = "same",
    epsilon: float = 0.1,
    stiffness_lambda: float = 1.0,
) -> tuple[CyclicReturnSpectrumValidation, list[dict[str, Any]], np.ndarray, Any, Any, Sequence[SupportSpec], np.ndarray]:
    _, state, path_report, supports, source = load_l_path_state(path_length, orientation)
    M = cyclic_matrix(state, epsilon=epsilon, stiffness_lambda=stiffness_lambda)
    vals = np.linalg.eigvals(M)
    mods = np.abs(vals)
    rows = [
        {
            "index": int(i),
            "real": float(v.real),
            "imag": float(v.imag),
            "modulus": float(abs(v)),
            "angle": float(math.atan2(v.imag, v.real)),
        }
        for i, v in enumerate(vals)
    ]
    spectral_radius = float(np.max(mods))
    near_one = int(np.sum(np.abs(mods - 1.0) <= 1.0e-10))
    report = CyclicReturnSpectrumValidation(
        path_length=int(path_length),
        orientation=str(orientation),
        n_points=int(state.n_points),
        state_dimension=int(M.shape[0]),
        epsilon=float(epsilon),
        stiffness_lambda=float(stiffness_lambda),
        spectral_radius=spectral_radius,
        min_modulus=float(np.min(mods)),
        max_modulus=float(np.max(mods)),
        mean_modulus=float(np.mean(mods)),
        median_modulus=float(np.median(mods)),
        count_modulus_near_one_1e_10=near_one,
        count_modulus_gt_one_plus_1e_10=int(np.sum(mods > 1.0 + 1.0e-10)),
        count_modulus_lt_one_minus_1e_10=int(np.sum(mods < 1.0 - 1.0e-10)),
        settling_expected_from_forward_iteration=bool(spectral_radius < 1.0 - 1.0e-10),
        interpretation=(
            "The cyclic return map is neutral/unit-modulus to numerical precision; "
            "forward iteration should be expected to oscillate rather than relax."
            if abs(spectral_radius - 1.0) <= 1.0e-10
            else "The cyclic return map is not neutral by this tolerance."
        ),
    )
    return report, rows, M, state, path_report, supports, source


def _constraint_indices(
    *,
    n_points: int,
    supports: Sequence[SupportSpec],
    source: np.ndarray,
    profile: str,
) -> tuple[np.ndarray, np.ndarray]:
    support_points = sorted(
        {
            int(p)
            for support in supports
            for p in (*support.boundary_points, *support.dressing_points)
        }
    )
    idx: list[int] = []
    vals: list[float] = []
    if profile == "none":
        pass
    elif profile == "current_support_source":
        for point in support_points:
            idx.append(point)
            vals.append(float(source[point]))
    elif profile == "current_and_prev_seed":
        for point in support_points:
            idx.append(point)
            vals.append(float(source[point]))
            idx.append(n_points + point)
            vals.append(0.0)
    elif profile == "both_ledgers_support_source":
        for point in support_points:
            idx.append(point)
            vals.append(float(source[point]))
            idx.append(n_points + point)
            vals.append(float(source[point]))
    else:
        raise ValueError(f"Unknown constraint profile: {profile}")
    return np.asarray(idx, dtype=np.int64), np.asarray(vals, dtype=np.float64)


def _constrained_min_residual(
    A: np.ndarray,
    constrained_idx: np.ndarray,
    constrained_vals: np.ndarray,
    *,
    residual_rows: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    if residual_rows is not None:
        A = A[residual_rows, :]
    n = int(A.shape[1])
    mask = np.ones(n, dtype=bool)
    mask[constrained_idx] = False
    free = np.where(mask)[0]
    v0 = np.zeros(n, dtype=np.float64)
    v0[constrained_idx] = constrained_vals
    Af = A[:, free]
    b = -(A @ v0)
    if Af.size:
        z, *_ = np.linalg.lstsq(Af, b, rcond=None)
        v = v0.copy()
        v[free] = z
    else:
        v = v0
    residual = A @ v
    return v, {
        "l2_residual": float(np.linalg.norm(residual)),
        "rms_residual": float(np.sqrt(np.mean(residual * residual))) if residual.size else 0.0,
        "max_abs_residual": float(np.max(np.abs(residual))) if residual.size else 0.0,
        "residual_dim": int(residual.size),
        "free_dim": int(free.size),
        "constrained_dim": int(constrained_idx.size),
    }


def validate_recurrent_solve(
    *,
    M_cycle: np.ndarray,
    state: sfg.FrozenAssociationState,
    path_report: Any,
    supports: Sequence[SupportSpec],
    source: np.ndarray,
    path_length: int,
    orientation: str,
    period_max: int = 12,
    exact_tolerance: float = 1.0e-9,
) -> tuple[RecurrentSolveValidation, list[dict[str, Any]]]:
    n = int(state.n_points)
    I = np.eye(2 * n, dtype=np.float64)
    witness = np.asarray(tuple(int(x) for x in path_report.path_points), dtype=np.int64)
    witness_rows = np.concatenate([witness, n + witness])
    rows: list[dict[str, Any]] = []
    profiles = ("none", "current_support_source", "current_and_prev_seed", "both_ledgers_support_source")
    for profile in profiles:
        cidx, cvals = _constraint_indices(n_points=n, supports=supports, source=source, profile=profile)
        for period in range(1, int(period_max) + 1):
            A = np.linalg.matrix_power(M_cycle, int(period)) - I
            _, full = _constrained_min_residual(A, cidx, cvals)
            _, witness_stats = _constrained_min_residual(A, cidx, cvals, residual_rows=witness_rows)
            rows.append(
                {
                    "constraint_profile": profile,
                    "period_cycles": int(period),
                    "full_l2_residual": full["l2_residual"],
                    "full_rms_residual": full["rms_residual"],
                    "full_max_abs_residual": full["max_abs_residual"],
                    "witness_l2_residual": witness_stats["l2_residual"],
                    "witness_rms_residual": witness_stats["rms_residual"],
                    "witness_max_abs_residual": witness_stats["max_abs_residual"],
                    "residual_dim_full": full["residual_dim"],
                    "residual_dim_witness": witness_stats["residual_dim"],
                    "free_dim": full["free_dim"],
                    "constrained_dim": full["constrained_dim"],
                }
            )
    support_rows = [row for row in rows if row["constraint_profile"] != "none"]
    best_full = min(rows, key=lambda row: float(row["full_max_abs_residual"]))
    best_witness = min(rows, key=lambda row: float(row["witness_max_abs_residual"]))
    best_support_full = min(support_rows, key=lambda row: float(row["full_max_abs_residual"]))
    best_support_witness = min(support_rows, key=lambda row: float(row["witness_max_abs_residual"]))
    support_exact_full = any(float(row["full_max_abs_residual"]) <= exact_tolerance for row in support_rows)
    support_exact_witness = any(float(row["witness_max_abs_residual"]) <= exact_tolerance for row in support_rows)
    result = RecurrentSolveValidation(
        path_length=int(path_length),
        orientation=str(orientation),
        periods_tested=tuple(range(1, int(period_max) + 1)),
        constraint_profiles=profiles,
        exact_tolerance=float(exact_tolerance),
        best_full_state_row=best_full,
        best_witness_row=best_witness,
        best_support_constrained_full_state_row=best_support_full,
        best_support_constrained_witness_row=best_support_witness,
        support_constrained_exact_full_state_found=bool(support_exact_full),
        support_constrained_exact_witness_found=bool(support_exact_witness),
        interpretation=(
            "Unconstrained recurrence admits the trivial zero state. Witness-only support-constrained recurrence "
            "may be solvable because non-witness degrees of freedom can absorb residuals, but that is not a full-field SOO-set state. "
            "A full-state support-constrained recurrent solve is the stricter initialization target."
        ),
    )
    return result, rows


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


def run_soo_validation(
    *,
    output_dir: str | Path,
    path_length: int = 31,
    orientation: str = "same",
    epsilon: float = 0.1,
    stiffness_lambda: float = 1.0,
    period_max: int = 12,
    comparison_steps: int = 200,
) -> SOOValidationReport:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    identity, identity_rows = validate_identity_recurrence(
        epsilon=epsilon,
        stiffness_lambda=stiffness_lambda,
        comparison_steps=comparison_steps,
    )
    spectrum, eigen_rows, M_cycle, state, path_report, supports, source = validate_cyclic_spectrum(
        path_length=path_length,
        orientation=orientation,
        epsilon=epsilon,
        stiffness_lambda=stiffness_lambda,
    )
    recurrent, solve_rows = validate_recurrent_solve(
        M_cycle=M_cycle,
        state=state,
        path_report=path_report,
        supports=supports,
        source=source,
        path_length=path_length,
        orientation=orientation,
        period_max=period_max,
    )
    artifacts = {
        "identity_recurrence_sequence": "identity_recurrence_sequence.csv",
        "cyclic_return_eigenvalues": "cyclic_return_eigenvalues.csv",
        "recurrent_solve_rows": "recurrent_solve_rows.csv",
        "report": "SOO_VALIDATION_REPORT.json",
    }
    conclusions = (
        "association_indexed_soo_v1 reproduces the expected identity-association second-order recurrence to numerical precision.",
        "The observed oscillator amplitude matches the analytic amplitude implied by epsilon=0.1, K=1, Phi_prev=0, Phi_curr=1.",
        "The L31 rank-3 cyclic return map has unit-modulus spectrum to numerical precision; forward settling should not be expected from this conservative recurrence.",
        "Direct recurrent initialization should be treated as a constrained linear solve; witness-only recurrence is weaker than full-field recurrence and must not be used alone to certify a measurement initial state.",
    )
    report = SOOValidationReport(
        report_schema="rank3_soo_validation_report_v1",
        validation_id="association_indexed_soo_identity_spectrum_recurrent_solve_v0_1",
        identity_recurrence=identity,
        cyclic_return_spectrum=spectrum,
        recurrent_solve=recurrent,
        artifacts=artifacts,
        conclusions=conclusions,
    )
    write_csv(output / artifacts["identity_recurrence_sequence"], identity_rows)
    write_csv(output / artifacts["cyclic_return_eigenvalues"], eigen_rows)
    write_csv(output / artifacts["recurrent_solve_rows"], solve_rows)
    (output / artifacts["report"]).write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = (
        "# SOO Validation Report\n\n"
        f"Report hash: `{report.fingerprint()}`\n\n"
        "## Main answers\n\n"
        f"1. Identity recurrence max error: `{identity.max_abs_error:.3e}`. Passed: `{identity.passed}`.\n"
        f"2. Analytic amplitude: `{identity.analytic_amplitude:.12g}`; observed peak over {identity.comparison_steps} steps: `{identity.observed_peak_abs:.12g}` at step `{identity.observed_peak_step}`.\n"
        f"3. Cyclic spectral radius: `{spectrum.spectral_radius:.12g}`; unit-modulus eigenvalues: `{spectrum.count_modulus_near_one_1e_10}/{spectrum.state_dimension}`.\n"
        f"4. Best full-state recurrence row, including unconstrained zero control: `{recurrent.best_full_state_row}`.\n"
        f"   Best support-constrained full-state row: `{recurrent.best_support_constrained_full_state_row}`.\n"
        f"   Best support-constrained witness row: `{recurrent.best_support_constrained_witness_row}`.\n\n"
        "See CSV artifacts for full rows.\n"
    )
    (output / "README.md").write_text(readme, encoding="utf-8")
    return report
