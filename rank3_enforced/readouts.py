from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .fingerprints import array_hash, stable_json_hash
from .immutable_result import ImmutableScalarFieldGeometryResult
from .rule_metadata import RuleMetadata, RuleStatus


@dataclass(frozen=True)
class ReadoutReport:
    name: str
    payload: dict[str, Any]
    fingerprint: str


class ReadoutRule(Protocol):
    name: str
    metadata: RuleMetadata

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        ...


@dataclass(frozen=True)
class ResultShapeReadout:
    name: str = "result_shape"
    metadata: RuleMetadata = RuleMetadata(
        name="result_shape",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_readout_result_shape",
        notes="Infrastructure readout.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        payload = {
            "n_states": len(result.states),
            "phi_shape": tuple(int(x) for x in result.phi.shape),
            "n_geometry_snapshots": len(result.geometry_snapshots),
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class StateVerificationReadout:
    name: str = "state_verification"
    metadata: RuleMetadata = RuleMetadata(
        name="state_verification",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_readout_state_verification",
        notes="Infrastructure readout.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        payload = {
            "all_states_verified": all(state.verify() for state in result.states),
            "state_fingerprints": [state.fingerprint for state in result.states],
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class PhiHistoryHashReadout:
    name: str = "phi_history_hash"
    metadata: RuleMetadata = RuleMetadata(
        name="phi_history_hash",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_readout_phi_history_hash",
        notes="Evidence hash readout.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        payload = {
            "phi_hash": array_hash(result.phi),
            "phi_writeable": bool(result.phi.flags.writeable),
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class GeometrySnapshotCountReadout:
    name: str = "geometry_snapshot_count"
    metadata: RuleMetadata = RuleMetadata(
        name="geometry_snapshot_count",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_readout_geometry_snapshot_count",
        notes="Infrastructure readout.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        payload = {
            "n_geometry_snapshots": len(result.geometry_snapshots),
            "geometry_hashes": [snap.fingerprint() for snap in result.geometry_snapshots],
            "all_geometry_arrays_frozen": all(
                (not snap.adjacency.flags.writeable)
                and (not snap.path_lengths.flags.writeable)
                and (not snap.pair_weights.flags.writeable)
                and (not snap.tensor_geometry.flags.writeable)
                for snap in result.geometry_snapshots
            ),
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class PathLengthSummaryReadout:
    name: str = "path_length_summary"
    metadata: RuleMetadata = RuleMetadata(
        name="path_length_summary",
        version="0.1.0",
        status=RuleStatus.CONTROL,
        source_hash="declared_readout_path_length_summary",
        notes="Derived path-length summary only; not physical evidence by itself.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        summaries: list[dict[str, float | int]] = []
        for snap in result.geometry_snapshots:
            finite = snap.path_lengths[np.isfinite(snap.path_lengths)]
            positive = finite[finite > 0]
            summaries.append(
                {
                    "ell": int(snap.ell),
                    "phase": int(snap.phase),
                    "reachable_pairs": int(positive.size),
                    "min_positive_L": float(np.min(positive)) if positive.size else float("nan"),
                    "max_positive_L": float(np.max(positive)) if positive.size else float("nan"),
                }
            )
        payload = {"summaries": summaries, "status": "derived_report_only"}
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


DEFAULT_READOUTS: tuple[ReadoutRule, ...] = (
    ResultShapeReadout(),
    StateVerificationReadout(),
    PhiHistoryHashReadout(),
    GeometrySnapshotCountReadout(),
)


@dataclass(frozen=True)
class CenterLocusReadout:
    """Locked center-locus readout for explicitly constructed paths.

    This is a diagnostic readout only. It does not classify physical admission.
    """

    path_report: object
    tolerance: float = 1e-9
    name: str = "center_locus_readout"
    metadata: RuleMetadata = RuleMetadata(
        name="center_locus_readout",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="declared_readout_center_locus_v0_1",
        notes="Locked center-locus diagnostic for explicit path construction.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        path_points = tuple(int(x) for x in getattr(self.path_report, "path_points"))
        L = len(path_points)
        if L % 2 == 1:
            center_points = (path_points[L // 2],)
            center_kind = "single_center"
        else:
            center_points = (path_points[L // 2 - 1], path_points[L // 2])
            center_kind = "center_pair"

        layers: list[dict[str, Any]] = []
        for ell in range(result.phi.shape[0]):
            values = [float(result.phi[ell, point]) for point in center_points]
            layer: dict[str, Any] = {
                "ell": int(ell),
                "center_points": center_points,
                "center_values": values,
                "center_kind": center_kind,
            }
            if center_kind == "single_center":
                layer["exact_center_zero"] = bool(values[0] == 0.0)
                layer["tolerance_center_zero"] = bool(abs(values[0]) <= self.tolerance)
            else:
                left, right = values
                layer["exact_center_balanced_edge"] = bool(left == -right and left != 0.0 and right != 0.0)
                layer["tolerance_center_balanced_edge"] = bool(
                    abs(left + right) <= self.tolerance
                    and abs(left) > self.tolerance
                    and abs(right) > self.tolerance
                )
            layers.append(layer)

        payload = {
            "status": "diagnostic_only",
            "path_report_hash": self.path_report.fingerprint(),
            "declared_path_length": int(getattr(self.path_report, "path_length")),
            "path_length_semantics": str(getattr(self.path_report, "semantics")),
            "orientation": str(getattr(self.path_report, "orientation")),
            "center_kind": center_kind,
            "center_points": center_points,
            "tolerance": float(self.tolerance),
            "layers": layers,
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class StructuralSilenceReadout:
    """Locked non-center zero/near-zero audit for explicit paths."""

    path_report: object
    tolerance: float = 1e-9
    name: str = "structural_silence_readout"
    metadata: RuleMetadata = RuleMetadata(
        name="structural_silence_readout",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="declared_readout_structural_silence_v0_1",
        notes="Locked exact-zero and tolerance-level non-center path audit.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        path_points = tuple(int(x) for x in getattr(self.path_report, "path_points"))
        L = len(path_points)
        center_points = (path_points[L // 2],) if L % 2 == 1 else (path_points[L // 2 - 1], path_points[L // 2])
        non_center = tuple(point for point in path_points if point not in set(center_points))
        layers: list[dict[str, Any]] = []
        for ell in range(result.phi.shape[0]):
            values = [float(result.phi[ell, point]) for point in non_center]
            exact_zero_count = sum(1 for value in values if value == 0.0)
            tolerance_zero_count = sum(1 for value in values if abs(value) <= self.tolerance)
            layers.append(
                {
                    "ell": int(ell),
                    "non_center_count": len(non_center),
                    "exact_noncenter_zero_count": int(exact_zero_count),
                    "tolerance_noncenter_near_zero_count": int(tolerance_zero_count),
                    "exact_noncenter_zero_points": [
                        int(point) for point, value in zip(non_center, values) if value == 0.0
                    ],
                    "tolerance_noncenter_near_zero_points": [
                        int(point) for point, value in zip(non_center, values) if abs(value) <= self.tolerance
                    ],
                }
            )
        payload = {
            "status": "diagnostic_only",
            "path_report_hash": self.path_report.fingerprint(),
            "declared_path_length": int(getattr(self.path_report, "path_length")),
            "path_length_semantics": str(getattr(self.path_report, "semantics")),
            "center_points_excluded": center_points,
            "non_center_points": non_center,
            "tolerance": float(self.tolerance),
            "layers": layers,
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class DeltaLClassificationReadout:
    """Locked Delta-L classifier over the explicit path record.

    The classifier is deliberately conservative. It classifies observed changes
    to the locked declared path record/edge-presence audit. It does not infer
    path addition/removal from center values alone and it does not certify the
    EAS theorem.
    """

    path_report: object
    name: str = "delta_l_classification"
    metadata: RuleMetadata = RuleMetadata(
        name="delta_l_classification",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="declared_readout_delta_l_classification_v0_1",
        notes="Locked declared-path Delta-L diagnostic for explicit path construction.",
    )

    def _expected_edges(self) -> tuple[tuple[int, int], ...]:
        points = tuple(int(x) for x in getattr(self.path_report, "path_points"))
        left_anchor = int(getattr(self.path_report, "left_anchor"))
        right_anchor = int(getattr(self.path_report, "right_anchor"))
        edges = [(left_anchor, points[0])]
        edges.extend((points[i], points[i + 1]) for i in range(len(points) - 1))
        edges.append((points[-1], right_anchor))
        return tuple(edges)

    @staticmethod
    def _edge_present(state: object, edge: tuple[int, int]) -> bool:
        source, target = edge
        row = tuple(int(x) for x in state.assoc[int(source)])
        return int(target) in row

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        expected_edges = self._expected_edges()
        path_points = tuple(int(x) for x in getattr(self.path_report, "path_points"))
        declared_L = int(getattr(self.path_report, "path_length"))
        edge_audits: list[dict[str, Any]] = []
        for state in result.states:
            present = [edge for edge in expected_edges if self._edge_present(state, edge)]
            missing = [edge for edge in expected_edges if edge not in set(present)]
            edge_audits.append(
                {
                    "state_step": int(state.step),
                    "expected_declared_edge_count": len(expected_edges),
                    "present_declared_edge_count": len(present),
                    "missing_declared_edges": missing,
                    "declared_path_intact": len(missing) == 0,
                }
            )

        initial_intact = bool(edge_audits[0]["declared_path_intact"]) if edge_audits else False
        final_intact = bool(edge_audits[-1]["declared_path_intact"]) if edge_audits else False
        # Current locked framework has no dynamic path-record mutation primitive.
        # Therefore the only certifiable Delta-L classification from this
        # readout is no observed declared path-length change, unless future
        # locked remap/readout support updates the explicit path record.
        if initial_intact and final_intact:
            delta = 0
            classification = "no_declared_path_length_change_observed"
        elif initial_intact and not final_intact:
            delta = "unclassified_declared_path_disrupted"
            classification = "unclassified_declared_path_disrupted"
        else:
            delta = "unclassified_initial_path_not_intact"
            classification = "unclassified_initial_path_not_intact"

        # Report ordinary graph shortest path as a cautionary derived summary,
        # not as the declared Delta-L classifier, because completed rank-3 filler
        # slots can create shortcut paths unrelated to the declared path record.
        graph_distances: list[dict[str, Any]] = []
        left_anchor = int(getattr(self.path_report, "left_anchor"))
        right_anchor = int(getattr(self.path_report, "right_anchor"))
        for snap in result.geometry_snapshots:
            value = float(snap.path_lengths[left_anchor, right_anchor])
            graph_distances.append(
                {
                    "ell": int(snap.ell),
                    "phase": int(snap.phase),
                    "graph_shortest_distance": value if np.isfinite(value) else "unreachable",
                }
            )

        payload = {
            "status": "diagnostic_only",
            "path_report_hash": self.path_report.fingerprint(),
            "declared_path_length": declared_L,
            "path_length_semantics": str(getattr(self.path_report, "semantics")),
            "support_anchor_graph_distance_edges_declared": int(getattr(self.path_report, "support_anchor_graph_distance_edges")),
            "orientation": str(getattr(self.path_report, "orientation")),
            "path_points": path_points,
            "expected_declared_edges": expected_edges,
            "edge_audits_by_state": edge_audits,
            "delta_declared_path_length": delta,
            "classification": classification,
            "graph_shortest_path_summary_not_classifier": graph_distances,
            "admission_note": "Declared-path diagnostic only; not theorem certification by itself.",
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class RolePathMidpointArrivalReadout:
    """Locked sign-resolved midpoint arrival diagnostic for declared role/path records.

    This readout is theorem-capable as a diagnostic: it reports same/opposite
    scalar arrival structure without mutating declared path length and without
    using orientation labels to produce the data. It is not, by itself, an
    admission gate for L -> L +/- 1.
    """

    path_report: object
    tolerance: float = 1e-9
    name: str = "role_path_midpoint_arrival_readout"
    metadata: RuleMetadata = RuleMetadata(
        name="role_path_midpoint_arrival_readout",
        version="0.1.22",
        status=RuleStatus.CANDIDATE,
        source_hash="declared_readout_role_path_midpoint_arrival_v0_1_22",
        notes="Sign-resolved midpoint arrival diagnostic over declared path points; readout only.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        path_points = tuple(int(x) for x in getattr(self.path_report, "path_points"))
        L = len(path_points)
        if not L:
            raise ValueError("role_path_midpoint_arrival_readout requires a nonempty path.")
        left_anchor = int(getattr(self.path_report, "left_anchor"))
        right_anchor = int(getattr(self.path_report, "right_anchor"))
        if L % 2 == 1:
            center_index = L // 2
            center_points = (path_points[center_index],)
            left_arrival_point = left_anchor if center_index == 0 else path_points[center_index - 1]
            right_arrival_point = right_anchor if center_index == L - 1 else path_points[center_index + 1]
            center_kind = "single_center"
        else:
            center_index = L // 2
            center_points = (path_points[center_index - 1], path_points[center_index])
            left_arrival_point = path_points[center_index - 1]
            right_arrival_point = path_points[center_index]
            center_kind = "center_pair"

        layers: list[dict[str, Any]] = []
        for ell in range(result.phi.shape[0]):
            left = float(result.phi[ell, left_arrival_point])
            right = float(result.phi[ell, right_arrival_point])
            center_values = [float(result.phi[ell, p]) for p in center_points]
            signed_sum = left + right
            signed_contrast = left - right
            pair_abs = abs(left) + abs(right)
            layers.append({
                "ell": int(ell),
                "center_kind": center_kind,
                "center_points": center_points,
                "center_values": center_values,
                "left_arrival_point": int(left_arrival_point),
                "right_arrival_point": int(right_arrival_point),
                "left_arrival": left,
                "right_arrival": right,
                "signed_sum_left_plus_right": signed_sum,
                "signed_contrast_left_minus_right": signed_contrast,
                "arrival_pair_abs": pair_abs,
                "reinforcement_ratio_abs_sum_over_pair_abs": float(abs(signed_sum) / (pair_abs + 1e-15)),
                "cancellation_ratio_abs_contrast_over_pair_abs": float(abs(signed_contrast) / (pair_abs + 1e-15)),
                "arrival_cancellation_within_tolerance": bool(abs(signed_sum) <= self.tolerance),
                "center_vacuum_equivalent_within_tolerance": bool(all(abs(v) <= self.tolerance for v in center_values)),
            })

        late_window = min(120, len(layers))
        late = layers[-late_window:]
        payload = {
            "status": "diagnostic_only",
            "path_report_hash": self.path_report.fingerprint(),
            "declared_path_length": int(getattr(self.path_report, "path_length")),
            "orientation_label_reported_but_not_used_for_update": str(getattr(self.path_report, "orientation")),
            "center_kind": center_kind,
            "center_points": center_points,
            "tolerance": float(self.tolerance),
            "late_window_layers": int(late_window),
            "late_abs_sum_mean": float(np.mean([abs(x["signed_sum_left_plus_right"]) for x in late])) if late else float("nan"),
            "late_abs_contrast_mean": float(np.mean([abs(x["signed_contrast_left_minus_right"]) for x in late])) if late else float("nan"),
            "late_reinforcement_ratio_mean": float(np.mean([x["reinforcement_ratio_abs_sum_over_pair_abs"] for x in late])) if late else float("nan"),
            "late_cancellation_ratio_mean": float(np.mean([x["cancellation_ratio_abs_contrast_over_pair_abs"] for x in late])) if late else float("nan"),
            "late_arrival_cancellation_fraction": float(np.mean([x["arrival_cancellation_within_tolerance"] for x in late])) if late else float("nan"),
            "late_center_vacuum_equivalent_fraction": float(np.mean([x["center_vacuum_equivalent_within_tolerance"] for x in late])) if late else float("nan"),
            "layers": layers,
            "admission_note": "Scalar midpoint diagnostic only; path-length mutation requires a separate admission gate.",
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class RelationCompletePacketReadout:
    """Relation-complete support packet readout for declared boundary/dressing records."""

    supports: tuple[object, ...]
    name: str = "relation_complete_packet_readout"
    metadata: RuleMetadata = RuleMetadata(
        name="relation_complete_packet_readout",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="declared_readout_relation_complete_packet_v0_1",
        notes="Computes chi_H,r = Phi(boundary_H,r)-Phi(dressing_H,r) as readout only.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        layers: list[dict[str, Any]] = []
        for ell in range(result.phi.shape[0]):
            support_records: list[dict[str, Any]] = []
            for support in self.supports:
                boundaries = tuple(int(x) for x in getattr(support, "boundary_points", ()))
                dressings = tuple(int(x) for x in getattr(support, "dressing_points", ()))
                phase_records: list[dict[str, Any]] = []
                for phase, (boundary, dressing) in enumerate(zip(boundaries, dressings)):
                    chi = float(result.phi[ell, boundary] - result.phi[ell, dressing])
                    phase_records.append(
                        {
                            "phase": int(phase),
                            "boundary_point": int(boundary),
                            "dressing_point": int(dressing),
                            "boundary_value": float(result.phi[ell, boundary]),
                            "dressing_value": float(result.phi[ell, dressing]),
                            "chi_boundary_minus_dressing": chi,
                        }
                    )
                support_records.append(
                    {
                        "support": str(getattr(support, "name", "support")),
                        "handedness": getattr(support, "handedness", None),
                        "phase_records": phase_records,
                    }
                )
            layers.append({"ell": int(ell), "supports": support_records})
        payload = {
            "status": "diagnostic_readout_only",
            "definition": "chi_H,r = Phi(boundary_H,r) - Phi(dressing_H,r)",
            "support_count": len(self.supports),
            "layers": layers,
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))


@dataclass(frozen=True)
class CommonModeZeroSumReadout:
    """Common-mode/zero-sum report over relation-complete packet chi triples."""

    supports: tuple[object, ...]
    name: str = "common_mode_zero_sum_report"
    metadata: RuleMetadata = RuleMetadata(
        name="common_mode_zero_sum_report",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="declared_readout_common_mode_zero_sum_v0_1",
        notes="Computes full-cycle common-mode and zero-sum packet readouts; readout only.",
    )

    def __call__(self, result: ImmutableScalarFieldGeometryResult) -> ReadoutReport:
        layers: list[dict[str, Any]] = []
        for ell in range(result.phi.shape[0]):
            support_records: list[dict[str, Any]] = []
            for support in self.supports:
                boundaries = tuple(int(x) for x in getattr(support, "boundary_points", ()))[:3]
                dressings = tuple(int(x) for x in getattr(support, "dressing_points", ()))[:3]
                chis = [float(result.phi[ell, b] - result.phi[ell, d]) for b, d in zip(boundaries, dressings)]
                common = float(sum(chis) / 3.0) if len(chis) == 3 else float("nan")
                zero_sum = [float(x - common) for x in chis] if len(chis) == 3 else []
                support_records.append(
                    {
                        "support": str(getattr(support, "name", "support")),
                        "handedness": getattr(support, "handedness", None),
                        "chi_triple": chis,
                        "common_mode": common,
                        "zero_sum": zero_sum,
                        "zero_sum_total": float(sum(zero_sum)) if zero_sum else float("nan"),
                    }
                )
            layers.append({"ell": int(ell), "supports": support_records})
        payload = {
            "status": "diagnostic_readout_only",
            "definition": "common=(chi0+chi1+chi2)/3; zero_sum=chi-common",
            "layers": layers,
        }
        return ReadoutReport(self.name, payload, stable_json_hash(payload))
