from __future__ import annotations

import numpy as np

import scalar_field_geometry as sfg
from .soo_schema import SOOResidualTermSpec


def active_association_contrast(
    context: sfg.ScalarUpdateContext,
    *,
    boundary_source_array: sfg.FloatArray | None = None,
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
) -> sfg.FloatArray:
    phi = np.asarray(context.phi_current, dtype=np.float64)
    state = context.geometry.state
    residual = np.zeros_like(phi, dtype=np.float64)
    for i in range(state.n_points):
        j = state.target(i, context.phase)
        residual[i] = phi[j] - phi[i]
    return residual


def completed_rank3_balance(
    context: sfg.ScalarUpdateContext,
    *,
    boundary_source_array: sfg.FloatArray | None = None,
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
) -> sfg.FloatArray:
    phi = np.asarray(context.phi_current, dtype=np.float64)
    state = context.geometry.state
    residual = np.zeros_like(phi, dtype=np.float64)
    for i in range(state.n_points):
        targets = [int(state.assoc[i, r]) for r in range(3)]
        target_mean = float(np.mean(phi[targets]))
        residual[i] = target_mean - phi[i]
    return residual


def tensor_completion_pressure(
    context: sfg.ScalarUpdateContext,
    *,
    boundary_source_array: sfg.FloatArray | None = None,
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
) -> sfg.FloatArray:
    phi = np.asarray(context.phi_current, dtype=np.float64)
    T = np.asarray(context.geometry.tensor_geometry, dtype=np.float64)
    n = context.geometry.state.n_points
    if T.shape != (n, n, n):
        raise ValueError("tensor_geometry has invalid shape for tensor_completion_pressure.")
    residual = np.zeros_like(phi, dtype=np.float64)
    # Signed, all-point tensor-mediated report. This reads derived tensor data;
    # it does not create primitive association geometry.
    for i in range(n):
        weighted_sum = 0.0
        weight_total = 0.0
        for j in range(n):
            for k in range(n):
                weight = float(T[i, j, k])
                if weight == 0.0:
                    continue
                pair_mean = 0.5 * (phi[j] + phi[k])
                weighted_sum += weight * (pair_mean - phi[i])
                weight_total += abs(weight)
        residual[i] = weighted_sum / weight_total if weight_total else 0.0
    return residual


def support_initialization_source(
    context: sfg.ScalarUpdateContext,
    *,
    boundary_source_array: sfg.FloatArray | None = None,
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
) -> sfg.FloatArray:
    """Locked initialization-only source operator.

    The source array is sealed before execution from declared support records.
    It is not supplied by arbitrary overlay code and it is not available from
    readouts or target verdicts.
    """

    n = context.geometry.state.n_points
    if boundary_source_array is None:
        raise ValueError(
            "support_initialization_source requires a sealed initialization source array. "
            "It is valid only during the initialization epoch."
        )
    source = np.asarray(boundary_source_array, dtype=np.float64)
    if source.shape != (n,):
        raise ValueError(f"initialization source shape {source.shape} does not match {(n,)}.")
    return source.copy()


def _support_packet_pair(support: object, phase: int) -> tuple[int, int]:
    boundary_points = tuple(int(x) for x in getattr(support, "boundary_points", ()))
    dressing_points = tuple(int(x) for x in getattr(support, "dressing_points", ()))
    if len(boundary_points) < 3 or len(dressing_points) < 3:
        raise ValueError("relation_complete_packet_contrast requires three boundary and three dressing points per support.")
    boundary = boundary_points[int(phase) % 3]
    active_map = {int(k): int(v) for k, v in dict(getattr(support, "active_phase_map", {})).items()}
    dressing = active_map.get(int(phase) % 3, dressing_points[int(phase) % 3])
    return boundary, dressing


def relation_complete_packet_contrast(
    context: sfg.ScalarUpdateContext,
    *,
    boundary_source_array: sfg.FloatArray | None = None,
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
) -> sfg.FloatArray:
    """Locked candidate relation-complete signed packet residual.

    For each active phase r, the support packet is read as
        chi_H,r = phi(boundary_H,r) - phi(dressing_H,r).

    The two support packets are propagated along the declared explicit path as
    signed relation-complete channels. This operator is not a final admitted SOO;
    it is a locked candidate channel that preserves the boundary/dressing sign
    information that raw scalar smoothing operators can erase.
    """

    if path_construction_report is None:
        raise ValueError("relation_complete_packet_contrast requires explicit path_construction_report.")
    if len(supports) < 2:
        raise ValueError("relation_complete_packet_contrast requires at least two declared supports.")

    phi = np.asarray(context.phi_current, dtype=np.float64)
    residual = np.zeros_like(phi, dtype=np.float64)
    phase = int(context.phase) % 3

    left_name = str(getattr(path_construction_report, "left_support"))
    right_name = str(getattr(path_construction_report, "right_support"))
    by_name = {str(getattr(s, "name")): s for s in supports}
    try:
        left_support = by_name[left_name]
        right_support = by_name[right_name]
    except KeyError as exc:
        raise ValueError("relation_complete_packet_contrast support names do not match path report.") from exc

    left_boundary, left_dressing = _support_packet_pair(left_support, phase)
    right_boundary, right_dressing = _support_packet_pair(right_support, phase)
    left_chi = float(phi[left_boundary] - phi[left_dressing])
    right_chi = float(phi[right_boundary] - phi[right_dressing])

    path_points = tuple(int(x) for x in getattr(path_construction_report, "path_points"))
    L = len(path_points)
    if L < 1:
        raise ValueError("relation_complete_packet_contrast requires a non-empty explicit path.")

    for idx, point in enumerate(path_points):
        # Distances are support-to-position counts along the declared path record.
        left_distance = float(idx + 1)
        right_distance = float(L - idx)
        residual[point] = (left_chi / left_distance) + (right_chi / right_distance)

    # Record a small direct packet echo at anchors so support channels remain traceable.
    left_anchor = int(getattr(path_construction_report, "left_anchor"))
    right_anchor = int(getattr(path_construction_report, "right_anchor"))
    residual[left_anchor] += left_chi
    residual[right_anchor] += right_chi
    return residual


SOO_RESIDUAL_OPERATORS = {
    "active_association_contrast": active_association_contrast,
    "completed_rank3_balance": completed_rank3_balance,
    "tensor_completion_pressure": tensor_completion_pressure,
    "support_initialization_source": support_initialization_source,
    "relation_complete_packet_contrast": relation_complete_packet_contrast,
}


def compute_residual_term(
    *,
    spec: SOOResidualTermSpec,
    context: sfg.ScalarUpdateContext,
    boundary_source_array: sfg.FloatArray | None = None,
    supports: tuple[object, ...] = (),
    path_construction_report: object | None = None,
) -> sfg.FloatArray:
    try:
        operator = SOO_RESIDUAL_OPERATORS[spec.operator_id]
    except KeyError as exc:
        raise ValueError(f"Unknown locked SOO residual operator: {spec.operator_id}") from exc
    return np.asarray(
        operator(
            context,
            boundary_source_array=boundary_source_array,
            supports=supports,
            path_construction_report=path_construction_report,
        ),
        dtype=np.float64,
    )
