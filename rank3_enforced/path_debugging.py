from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

from .fingerprints import array_hash, stable_json_hash


@dataclass(frozen=True)
class RunDebuggingSpec:
    enabled: bool = True
    path_neighborhood_depth: int = 1
    include_phi_history: bool = True
    include_ordered_differences: bool = True
    include_association_rows: bool = True
    include_soo_step_report_links: bool = True
    include_point_records: bool = True
    max_points: int = 256
    notes: str = "optional diagnostic instrumentation only; does not alter SOO"

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class PathFacingAssociationReport:
    report_schema: str
    status: str
    path_report_hash: str
    association_state_hash: str
    path_points: tuple[int, ...]
    left_anchor: int
    right_anchor: int
    path_slot: int
    reverse_slot: int
    records: tuple[dict[str, Any], ...]
    forbidden_interpretations: tuple[str, ...]
    report_hash: str

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class RunDebuggingReport:
    report_schema: str
    status: str
    instrumentation_module: str
    spec_hash: str
    path_report_hash: str | None
    path_facing_report_hash: str | None
    neighborhood_depth: int
    debug_point_count: int
    debug_points: tuple[int, ...]
    debug_point_roles: tuple[dict[str, Any], ...]
    transition_records: tuple[dict[str, Any], ...]
    soo_step_report_hashes: tuple[str, ...]
    warnings: tuple[str, ...]
    forbidden_interpretations: tuple[str, ...]
    report_hash: str

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def spec_from_optional_modules(modules: Sequence[object]) -> RunDebuggingSpec | None:
    for module in modules:
        if str(getattr(module, "module_id", "")) != "run_debugging":
            continue
        params = dict(getattr(module, "params", {}) or {})
        # Fail safe: merely having the module schema available must not invoke
        # expensive instrumentation. Debugging is opt-in only.
        if not bool(params.get("enabled", False)):
            return None
        depth = int(params.get("path_neighborhood_depth", params.get("depth", 1)))
        if depth < 0:
            raise ValueError("run_debugging.path_neighborhood_depth must be non-negative")
        max_points = int(params.get("max_points", 256))
        if max_points < 1:
            raise ValueError("run_debugging.max_points must be positive")
        return RunDebuggingSpec(
            enabled=True,
            path_neighborhood_depth=depth,
            include_phi_history=bool(params.get("include_phi_history", True)),
            include_ordered_differences=bool(params.get("include_ordered_differences", True)),
            include_association_rows=bool(params.get("include_association_rows", True)),
            include_soo_step_report_links=bool(params.get("include_soo_step_report_links", True)),
            include_point_records=bool(params.get("include_point_records", True)),
            max_points=max_points,
            notes=str(params.get("notes", "optional diagnostic instrumentation only; does not alter SOO")),
        )
    return None


def _path_sequence(path_report: object) -> tuple[int, ...]:
    return (
        int(getattr(path_report, "left_anchor")),
        *tuple(int(x) for x in getattr(path_report, "path_points")),
        int(getattr(path_report, "right_anchor")),
    )


def build_path_facing_association_report(*, path_report: object | None, initial_state: object | None) -> PathFacingAssociationReport | None:
    if path_report is None or initial_state is None:
        return None
    sequence = _path_sequence(path_report)
    path_slot = int(getattr(path_report, "path_slot")) % 3
    reverse_slot = int(getattr(path_report, "reverse_slot")) % 3
    records: list[dict[str, Any]] = []
    for index, point in enumerate(sequence):
        row = tuple(int(x) for x in initial_state.assoc[int(point)])
        expected_prev = sequence[index - 1] if index > 0 else None
        expected_next = sequence[index + 1] if index + 1 < len(sequence) else None
        path_target = row[path_slot]
        reverse_target = row[reverse_slot]
        records.append(
            {
                "point": int(point),
                "role": "left_anchor" if index == 0 else ("right_anchor" if index + 1 == len(sequence) else "declared_path_point"),
                "association_row": row,
                "path_facing_slot": path_slot,
                "path_facing_target": int(path_target),
                "expected_next_path_point": None if expected_next is None else int(expected_next),
                "path_slot_matches_declared_next": bool(expected_next is not None and int(path_target) == int(expected_next)),
                "reverse_slot": reverse_slot,
                "reverse_target": int(reverse_target),
                "expected_previous_path_point": None if expected_prev is None else int(expected_prev),
                "reverse_slot_matches_declared_previous": bool(expected_prev is not None and int(reverse_target) == int(expected_prev)),
                "scalar_value_requirement": "none",
            }
        )
    payload = {
        "report_schema": "rank3_path_facing_association_report_v1",
        "status": "association_role_report_only",
        "path_report_hash": path_report.fingerprint(),
        "association_state_hash": str(initial_state.fingerprint),
        "path_points": tuple(int(x) for x in getattr(path_report, "path_points")),
        "left_anchor": int(getattr(path_report, "left_anchor")),
        "right_anchor": int(getattr(path_report, "right_anchor")),
        "path_slot": path_slot,
        "reverse_slot": reverse_slot,
        "records": tuple(records),
        "forbidden_interpretations": (
            "path_facing_as_scalar_carrier_status",
            "path_points_as_special_SOO_update_domain",
            "nonzero_phi_required_for_path_participation",
        ),
    }
    return PathFacingAssociationReport(**payload, report_hash=stable_json_hash(payload))


def _completed_neighbors(assoc: np.ndarray, point: int) -> set[int]:
    p = int(point)
    outgoing = {int(x) for x in assoc[p]}
    incoming = {int(i) for i in np.where(assoc == p)[0]}
    return outgoing | incoming


def _neighborhood_by_depth(*, assoc: np.ndarray, seeds: Sequence[int], depth: int, max_points: int) -> tuple[tuple[int, ...], tuple[dict[str, Any], ...], tuple[str, ...]]:
    seed_set = {int(x) for x in seeds}
    visited = set(seed_set)
    frontier = set(seed_set)
    roles: dict[int, dict[str, Any]] = {int(x): {"point": int(x), "min_depth_from_declared_path": 0, "seed_role": "declared_path_or_anchor"} for x in seed_set}
    warnings: list[str] = []
    for d in range(1, depth + 1):
        next_frontier: set[int] = set()
        for point in sorted(frontier):
            next_frontier |= _completed_neighbors(assoc, point)
        next_frontier -= visited
        for point in sorted(next_frontier):
            roles[int(point)] = {"point": int(point), "min_depth_from_declared_path": int(d), "seed_role": "connected_by_rank3_association"}
        visited |= next_frontier
        frontier = next_frontier
        if len(visited) > max_points:
            warnings.append(f"debug neighborhood truncated at max_points={max_points}")
            visited = set(sorted(visited)[:max_points])
            roles = {p: roles[p] for p in sorted(visited)}
            break
    points = tuple(sorted(visited))
    return points, tuple(roles[p] for p in points), tuple(warnings)


def _array_value_list(phi_row: np.ndarray, points: Sequence[int]) -> list[dict[str, Any]]:
    return [{"point": int(p), "phi": float(phi_row[int(p)])} for p in points]


def build_run_debugging_report(
    *,
    spec: RunDebuggingSpec | None,
    result: object,
    path_report: object | None,
    initial_phi_previous: np.ndarray | None = None,
    path_facing_report: PathFacingAssociationReport | None = None,
    soo_execution_report: object | None = None,
) -> RunDebuggingReport | None:
    if spec is None or not spec.enabled:
        return None
    warnings: list[str] = []
    if path_report is None:
        warnings.append("run_debugging requested without explicit path report; no path neighborhood can be built")
        debug_points: tuple[int, ...] = ()
        roles: tuple[dict[str, Any], ...] = ()
        path_hash: str | None = None
    else:
        sequence = _path_sequence(path_report)
        initial_state = result.states[0]
        debug_points, roles, ns_warnings = _neighborhood_by_depth(
            assoc=np.asarray(initial_state.assoc, dtype=np.int64),
            seeds=sequence,
            depth=int(spec.path_neighborhood_depth),
            max_points=int(spec.max_points),
        )
        warnings.extend(ns_warnings)
        path_hash = path_report.fingerprint()

    transition_records: list[dict[str, Any]] = []
    phi = np.asarray(result.phi, dtype=np.float64)
    for ell in range(phi.shape[0]):
        layer: dict[str, Any] = {"ell": int(ell)}
        if spec.include_phi_history:
            layer["phi_values"] = _array_value_list(phi[ell], debug_points)
        if ell < len(result.states) and spec.include_association_rows:
            state = result.states[ell]
            layer["association_rows"] = [
                {"point": int(p), "row": tuple(int(x) for x in state.assoc[int(p)])}
                for p in debug_points
            ]
        if ell < phi.shape[0] - 1:
            state = result.states[ell]
            phase = int(result.geometry_snapshots[ell].phase) if ell < len(result.geometry_snapshots) else ell % 3
            phi_prev = phi[ell - 1] if ell > 0 else (initial_phi_previous if initial_phi_previous is not None else None)
            records: list[dict[str, Any]] = []
            for point in debug_points:
                p = int(point)
                rec: dict[str, Any] = {
                    "point": p,
                    "phase": phase,
                    "phi_curr": float(phi[ell, p]),
                    "phi_next": float(phi[ell + 1, p]),
                    "delta_phi_next_minus_curr": float(phi[ell + 1, p] - phi[ell, p]),
                    "active_associate": int(state.assoc[p, phase % 3]),
                }
                if spec.include_ordered_differences and phi_prev is not None:
                    active = int(state.assoc[p, phase % 3])
                    rec["A_theta_phi_prev"] = float(phi_prev[active])
                    rec["Pi_A_curr"] = float(phi[ell, p] - phi_prev[active])
                elif spec.include_ordered_differences:
                    rec["ordered_difference_status"] = "unavailable_first_previous_ledger_not_recorded"
                records.append(rec)
            layer["soo_change_records"] = records
        transition_records.append(layer)

    step_hashes: tuple[str, ...] = ()
    if spec.include_soo_step_report_links and soo_execution_report is not None:
        step_hashes = tuple(str(x) for x in getattr(soo_execution_report, "step_report_hashes", ()))

    payload = {
        "report_schema": "rank3_run_debugging_report_v1",
        "status": "diagnostic_instrumentation_only",
        "instrumentation_module": "run_debugging",
        "spec_hash": spec.fingerprint(),
        "path_report_hash": path_hash,
        "path_facing_report_hash": path_facing_report.fingerprint() if path_facing_report is not None else None,
        "neighborhood_depth": int(spec.path_neighborhood_depth),
        "debug_point_count": len(debug_points),
        "debug_points": debug_points,
        "debug_point_roles": roles,
        "transition_records": tuple(transition_records),
        "soo_step_report_hashes": step_hashes,
        "warnings": tuple(warnings),
        "forbidden_interpretations": (
            "debug_points_as_special_SOO_update_domain",
            "path_neighborhood_as_scalar_carrier_initialization",
            "debug_report_as_admission_verdict",
        ),
    }
    return RunDebuggingReport(**payload, report_hash=stable_json_hash(payload))
