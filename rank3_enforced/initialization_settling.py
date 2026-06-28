from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

import scalar_field_geometry as sfg
from .active_association import build_A_theta
from .fingerprints import array_hash, stable_json_hash


@dataclass(frozen=True)
class InitializationSettlingSpec:
    enabled: bool = False
    witness_scope: str = "auto_influenced_exterior"
    witness_neighborhood_depth: int = 0
    min_cycles: int = 3
    max_cycles: int = 100
    consecutive_stable_cycles_required: int = 3
    recurrence_period_min: int = 1
    recurrence_period_max: int = 3
    tol_rms: float = 1.0e-10
    tol_q95: float = 1.0e-9
    tol_max: float = 1.0e-8
    tol_sign: float = 0.0
    zero_epsilon: float = 1.0e-12
    fail_if_not_steady: bool = True
    progress_interval_cycles: int = 10

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class InitializationSettlingReport:
    report_schema: str
    status: str
    enabled: bool
    witness_scope: str
    witness_rule: str
    witness_neighborhood_depth: int
    witness_points: tuple[int, ...]
    excluded_support_points: tuple[int, ...]
    initialization_scan_steps: int
    initialization_scan_rank3_cycles: int
    accepted_initialization_steps: int
    accepted_initialization_rank3_cycles: int
    measurement_starts_after_initialization: bool
    steady_state_reached: bool
    steady_state_type: str
    accepted_recurrence_period_cycles: int | None
    consecutive_stable_cycles: int
    tolerance_profile: dict[str, Any]
    per_cycle_witness_statistics: tuple[dict[str, Any], ...]
    phi_after_settling_hash: str | None
    phi_previous_for_measurement_hash: str | None
    measurement_initial_state_hash: str | None
    forbidden_interpretations: tuple[str, ...]
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def parse_settling_spec(raw: dict[str, Any] | None) -> InitializationSettlingSpec:
    data = dict(raw or {})
    enabled = bool(data.get("enabled", False))
    return InitializationSettlingSpec(
        enabled=enabled,
        witness_scope=str(data.get("witness_scope", "auto_influenced_exterior")),
        witness_neighborhood_depth=int(data.get("witness_neighborhood_depth", data.get("path_neighborhood_depth", 0))),
        min_cycles=int(data.get("min_cycles", 3)),
        max_cycles=int(data.get("max_cycles", 100)),
        consecutive_stable_cycles_required=int(data.get("consecutive_stable_cycles_required", 3)),
        recurrence_period_min=int(data.get("recurrence_period_min", 1)),
        recurrence_period_max=int(data.get("recurrence_period_max", 3)),
        tol_rms=float(data.get("tol_rms", 1.0e-10)),
        tol_q95=float(data.get("tol_q95", 1.0e-9)),
        tol_max=float(data.get("tol_max", 1.0e-8)),
        tol_sign=float(data.get("tol_sign", 0.0)),
        zero_epsilon=float(data.get("zero_epsilon", 1.0e-12)),
        fail_if_not_steady=bool(data.get("fail_if_not_steady", True)),
        progress_interval_cycles=int(data.get("progress_interval_cycles", 10)),
    )


def _support_owned_points(supports: Sequence[object]) -> set[int]:
    owned: set[int] = set()
    for support in supports:
        for attr in ("support_points", "boundary_points", "dressing_points"):
            for point in getattr(support, attr, ()):
                owned.add(int(point))
        for point in dict(getattr(support, "active_phase_map", {})).values():
            owned.add(int(point))
    return owned


def _path_sequence(path_report: object) -> tuple[int, ...]:
    return (
        int(getattr(path_report, "left_anchor")),
        *tuple(int(x) for x in getattr(path_report, "path_points", ())),
        int(getattr(path_report, "right_anchor")),
    )


def _expand_neighborhood(*, state: sfg.FrozenAssociationState, seeds: Sequence[int], depth: int) -> tuple[int, ...]:
    points = {int(x) for x in seeds}
    frontier = set(points)
    for _ in range(max(0, int(depth))):
        next_frontier: set[int] = set()
        for point in frontier:
            if 0 <= point < state.n_points:
                for target in state.assoc[point]:
                    next_frontier.add(int(target))
                # Include reverse neighbors as connected-to-path diagnostics. This
                # is witness selection only; it never alters SOO.
                reverse_sources = np.where(state.assoc == int(point))[0]
                for source in reverse_sources:
                    next_frontier.add(int(source))
        next_frontier -= points
        points |= next_frontier
        frontier = next_frontier
    return tuple(sorted(points))


def build_influenced_witness_points(
    *,
    initial_state: sfg.FrozenAssociationState,
    supports: Sequence[object],
    path_report: object | None,
    spec: InitializationSettlingSpec,
) -> tuple[tuple[int, ...], tuple[int, ...], str]:
    support_owned = _support_owned_points(supports)
    if len(supports) >= 2 and path_report is not None:
        path_points = tuple(int(x) for x in getattr(path_report, "path_points", ()))
        seeds = path_points or tuple(p for p in _path_sequence(path_report) if p not in support_owned)
        rule = "relational_path_exterior_witness"
    elif len(supports) == 1:
        support = supports[0]
        seeds = tuple(int(x) for x in getattr(support, "dressing_points", ()))
        if not seeds:
            seeds = tuple(int(x) for x in getattr(support, "boundary_points", ()))
        rule = "single_support_dressing_exterior_witness"
    else:
        seeds = tuple(range(initial_state.n_points))
        rule = "no_support_whole_field_fallback_control"

    expanded = _expand_neighborhood(
        state=initial_state,
        seeds=seeds,
        depth=spec.witness_neighborhood_depth,
    )
    # For two-support path witnesses, exclude support-owned interior/anchor
    # points from the settling statistic unless the neighborhood contains no
    # exterior records. For one-support witnesses, dressing points are retained
    # because they are the declared one-support exterior-facing witnesses.
    if len(supports) >= 2:
        exterior = tuple(p for p in expanded if p not in support_owned)
        witness = exterior if exterior else expanded
    else:
        witness = expanded
    if not witness:
        witness = tuple(int(x) for x in seeds)
    return tuple(sorted(set(int(x) for x in witness))), tuple(sorted(support_owned)), rule


def _pi_A_for_layer(*, phi: np.ndarray, state: sfg.FrozenAssociationState, ell: int) -> np.ndarray | None:
    if ell <= 0:
        return None
    theta = int(ell) % 3
    A = build_A_theta(state, theta)
    return np.asarray(phi[ell], dtype=np.float64) - A @ np.asarray(phi[ell - 1], dtype=np.float64)


def _variation_stats(curr: np.ndarray, prev: np.ndarray, *, zero_epsilon: float) -> dict[str, Any]:
    curr = np.asarray(curr, dtype=np.float64)
    prev = np.asarray(prev, dtype=np.float64)
    delta = curr - prev
    abs_delta = np.abs(delta)
    rms = float(np.sqrt(np.mean(delta * delta))) if delta.size else 0.0
    q95 = float(np.quantile(abs_delta, 0.95)) if delta.size else 0.0
    max_abs = float(np.max(abs_delta)) if delta.size else 0.0
    comparable = (np.abs(curr) > zero_epsilon) | (np.abs(prev) > zero_epsilon)
    denom = int(np.sum(comparable))
    if denom:
        sign_changed = (np.sign(curr[comparable]) != np.sign(prev[comparable]))
        sign_fraction = float(np.sum(sign_changed) / denom)
    else:
        sign_fraction = 0.0
    return {
        "rms_delta": rms,
        "q95_abs_delta": q95,
        "max_abs_delta": max_abs,
        "sign_change_fraction": sign_fraction,
        "comparable_point_count": denom,
    }


def _passes(stats: dict[str, Any], spec: InitializationSettlingSpec) -> bool:
    return bool(
        float(stats["rms_delta"]) <= spec.tol_rms
        and float(stats["q95_abs_delta"]) <= spec.tol_q95
        and float(stats["max_abs_delta"]) <= spec.tol_max
        and float(stats["sign_change_fraction"]) <= spec.tol_sign
    )


def analyze_settling_scan(
    *,
    phi: np.ndarray,
    states: Sequence[sfg.FrozenAssociationState],
    witness_points: Sequence[int],
    spec: InitializationSettlingSpec,
) -> tuple[int | None, int | None, str, int, tuple[dict[str, Any], ...]]:
    witness = np.asarray(tuple(int(x) for x in witness_points), dtype=np.int64)
    period_min = max(1, int(spec.recurrence_period_min))
    period_max = max(period_min, int(spec.recurrence_period_max))
    required = max(1, int(spec.consecutive_stable_cycles_required))
    min_cycles = max(0, int(spec.min_cycles))
    per_cycle: list[dict[str, Any]] = []
    stable_run_by_period: dict[int, int] = {p: 0 for p in range(period_min, period_max + 1)}

    max_complete_cycle = (phi.shape[0] - 1) // 3
    accepted_layer: int | None = None
    accepted_period: int | None = None
    accepted_type = "not_reached"
    accepted_stable_run = 0

    for cycle in range(1, max_complete_cycle + 1):
        cycle_records: list[dict[str, Any]] = []
        for period in range(period_min, period_max + 1):
            if cycle - period < 0:
                continue
            phase_records: list[dict[str, Any]] = []
            period_passed = True
            # Last three same-phase layer returns ending at layer 3*cycle.
            for phase_offset in (0, 1, 2):
                ell = 3 * cycle - 2 + phase_offset
                prev_ell = ell - 3 * period
                if prev_ell < 0 or ell >= phi.shape[0]:
                    period_passed = False
                    continue
                state = states[min(ell, len(states) - 1)]
                phi_stats = _variation_stats(
                    phi[ell, witness],
                    phi[prev_ell, witness],
                    zero_epsilon=spec.zero_epsilon,
                )
                pi_curr = _pi_A_for_layer(phi=phi, state=state, ell=ell)
                pi_prev = _pi_A_for_layer(phi=phi, state=states[min(prev_ell, len(states)-1)], ell=prev_ell)
                if pi_curr is not None and pi_prev is not None:
                    pi_stats = _variation_stats(
                        pi_curr[witness],
                        pi_prev[witness],
                        zero_epsilon=spec.zero_epsilon,
                    )
                else:
                    pi_stats = {
                        "rms_delta": 0.0,
                        "q95_abs_delta": 0.0,
                        "max_abs_delta": 0.0,
                        "sign_change_fraction": 0.0,
                        "comparable_point_count": 0,
                    }
                phase_passed = _passes(phi_stats, spec) and _passes(pi_stats, spec)
                period_passed = period_passed and phase_passed
                phase_records.append(
                    {
                        "ell": int(ell),
                        "phase": int(ell % 3),
                        "previous_ell": int(prev_ell),
                        "phi": phi_stats,
                        "pi_A": pi_stats,
                        "passed": bool(phase_passed),
                    }
                )
            if cycle < min_cycles:
                period_passed = False
            stable_run_by_period[period] = stable_run_by_period.get(period, 0) + 1 if period_passed else 0
            record = {
                "cycle": int(cycle),
                "candidate_recurrence_period_cycles": int(period),
                "cycle_passed": bool(period_passed),
                "consecutive_stable_cycles_for_period": int(stable_run_by_period.get(period, 0)),
                "phase_records": phase_records,
            }
            cycle_records.append(record)
            if (
                accepted_layer is None
                and period_passed
                and stable_run_by_period.get(period, 0) >= required
            ):
                accepted_layer = 3 * cycle
                accepted_period = period
                accepted_type = "fixed" if period == 1 else "recurrent"
                accepted_stable_run = int(stable_run_by_period[period])
        per_cycle.extend(cycle_records)

    return accepted_layer, accepted_period, accepted_type, accepted_stable_run, tuple(per_cycle)


def disabled_settling_report(
    *,
    spec: InitializationSettlingSpec,
    phi_current: np.ndarray,
    phi_previous: np.ndarray | None,
    witness_points: Sequence[int] = (),
    excluded_support_points: Sequence[int] = (),
    witness_rule: str = "disabled",
) -> InitializationSettlingReport:
    return InitializationSettlingReport(
        report_schema="rank3_initialization_settling_report_v1",
        status="disabled",
        enabled=False,
        witness_scope=spec.witness_scope,
        witness_rule=witness_rule,
        witness_neighborhood_depth=int(spec.witness_neighborhood_depth),
        witness_points=tuple(int(x) for x in witness_points),
        excluded_support_points=tuple(int(x) for x in excluded_support_points),
        initialization_scan_steps=0,
        initialization_scan_rank3_cycles=0,
        accepted_initialization_steps=0,
        accepted_initialization_rank3_cycles=0,
        measurement_starts_after_initialization=True,
        steady_state_reached=True,
        steady_state_type="not_required",
        accepted_recurrence_period_cycles=None,
        consecutive_stable_cycles=0,
        tolerance_profile=asdict(spec),
        per_cycle_witness_statistics=(),
        phi_after_settling_hash=array_hash(phi_current),
        phi_previous_for_measurement_hash=(array_hash(phi_previous) if phi_previous is not None else None),
        measurement_initial_state_hash=stable_json_hash({
            "phi_current_hash": array_hash(phi_current),
            "phi_previous_hash": array_hash(phi_previous) if phi_previous is not None else None,
        }),
        forbidden_interpretations=(
            "disabled settling report is not evidence that a support-influenced exterior steady state was reached",
        ),
        details={"initialization_settling_enabled": False},
    )
