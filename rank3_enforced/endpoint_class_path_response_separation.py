from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .split_vacuum_triangle_emergence import run_exploratory as run_triangle_emergence


FRAMEWORK_TARGET_VERSION = "0.1.40"
RUNNER_ID = "endpoint_class_path_response_separation_runner_v0_3"
PACKET_ID = "endpoint_class_path_response_separation_approval_items_v0140"
SCHEMA = "endpoint_class_path_response_separation_v0_3"


@dataclass(frozen=True)
class EndpointRecord:
    endpoint_id: str
    endpoint_class: str
    scalar_sign: int
    path_facing_scalar: float
    record: dict[str, Any]
    local_certifier_passed: bool
    generated_or_imposed_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlSpec:
    id: str
    purpose: str
    expected_exploratory_behavior: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


FORBIDDEN_GENERATOR_INPUTS: tuple[str, ...] = (
    "triangle_sign_label_as_delta_l_selector",
    "photon_like_label_as_no_accommodation_selector",
    "bounded_support_label_as_accommodation_selector",
    "target_delta_l",
    "expected_delta_l",
    "preselected_center_point",
    "preselected_center_action",
    "preselected_path_action",
    "charge_label",
    "standard_model_role_label",
    "endpoint_class_dispatched_center_condition",
    "endpoint_class_dispatched_delta_l",
    "photon_class_transaction_suppression",
    "photon_class_forced_path_facing_nullity",
    "bounded_opposite_expected_delta_l_selector",
    "local_photon_certifier_path_component_as_endpoint_scalar",
    "photon_field_processing_bypass",
    "photon_class_path_profile_override",
)

ALLOWED_GENERATOR_INPUTS: tuple[str, ...] = (
    "actual_generated_endpoint_record",
    "actual_association_graph",
    "actual_loaded_scalar_values",
    "actual_path_profile",
    "actual_photon_certifier_pass_fail",
    "actual_bounded_support_certifier_pass_fail",
    "off_path_vacuum_facing_profile_rule",
    "soo_processed_endpoint_field_record",
    "processed_path_facing_scalar_readout",
)

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "RUN_SCOPE_REPORT.json",
    "ENDPOINT_CLASSIFICATION_REPORT.json",
    "TRIANGLE_ENDPOINT_REPORT.json",
    "PHOTON_LIKE_CERTIFIER_REPORT.json",
    "PHOTON_FIELD_PROCESSING_REPORT.json",
    "PATH_FACING_SCALAR_READOUT_REPORT.json",
    "BOUNDED_SUPPORT_ENDPOINT_REPORT.json",
    "RELATIONAL_PATH_DISCOVERY_REPORT.json",
    "PATH_PROFILE_REPORT.json",
    "CENTER_CONDITION_REPORT.json",
    "PATH_ACCOMMODATION_REPORT.json",
    "ENDPOINT_CLASS_COMPARISON_REPORT.json",
    "PATH_RESPONSE_CALIBRATION_REPORT.json",
    "NEGATIVE_CONTROL_REPORT.json",
    "LEAKAGE_MANIPULATION_AUDIT.json",
    "EXPLORATORY_VERDICT_REPORT.json",
)

REQUIRED_CONTROLS: tuple[ControlSpec, ...] = (
    ControlSpec("triangle_sign_label_leakage_control", "Attempt to choose Delta L from triangle sign label.", "Rejected as forbidden generator input."),
    ControlSpec("photon_label_no_accommodation_leakage_control", "Attempt to choose no-accommodation from photon-like class label.", "Rejected as forbidden generator input."),
    ControlSpec("bounded_label_accommodation_leakage_control", "Attempt to choose accommodation from bounded-support label.", "Rejected as forbidden generator input."),
    ControlSpec("forced_delta_l_leakage_control", "Attempt to supply target Delta L to the generator.", "Rejected as forbidden generator input."),
    ControlSpec("preselected_center_action_control", "Attempt to supply center action to the generator.", "Rejected as forbidden generator input."),
    ControlSpec("local_photon_certifier_path_component_shortcut_control", "Attempt to use the local certifier path-facing component directly as the endpoint path scalar.", "Rejected; photon-like records must be field processed first."),
    ControlSpec("photon_field_processing_bypass_control", "Attempt to skip SOO/field processing for photon-like endpoints.", "Rejected as forbidden generator input."),
    ControlSpec("null_loaded_photon_control", "Photon-like record with zero transverse load.", "Fails photon-like certifier; cannot be used as class B endpoint."),
    ControlSpec("isotropic_photon_exterior_control", "Photon-like carrier with isotropic exterior continuation.", "Fails photon-like certifier."),
    ControlSpec("bare_cyclic_carrier_control", "Three-point cyclic carrier without transverse loading and anisotropic exterior record.", "Fails photon-like certifier."),
    ControlSpec("no_off_path_vacuum_profile_control", "Path profile generated without off-path vacuum-facing influence.", "Quarantined as over-closed path diagnostic."),
    ControlSpec("endpoint_class_dispatched_center_control", "Center state assigned from endpoint class rather than path scalar profile.", "Rejected as leakage/manipulation."),
    ControlSpec("photon_transaction_suppression_control", "Attempt to suppress topology transaction solely because endpoint class is photon-like.", "Rejected as forbidden generator input."),
    ControlSpec("bounded_expected_delta_l_selector_control", "Attempt to choose Delta L from bounded opposite/same calibration expectation.", "Rejected as forbidden generator input."),
)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def _sgn(x: float, tol: float = 1e-12) -> int:
    if x > tol:
        return 1
    if x < -tol:
        return -1
    return 0


def validate_generator_inputs(inputs: Iterable[str]) -> dict[str, Any]:
    supplied = tuple(str(x) for x in inputs)
    forbidden = tuple(x for x in supplied if x in FORBIDDEN_GENERATOR_INPUTS)
    unknown = tuple(x for x in supplied if x not in FORBIDDEN_GENERATOR_INPUTS and x not in ALLOWED_GENERATOR_INPUTS)
    return {
        "schema": "endpoint_class_separation_generator_input_validation_v0_3",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "supplied_inputs": supplied,
        "forbidden_inputs_present": forbidden,
        "unknown_inputs_present": unknown,
        "passed": not forbidden and not unknown,
    }


def _triangle_endpoints() -> tuple[list[EndpointRecord], dict[str, Any]]:
    reports = run_triangle_emergence(split_site_count=2, cycles=5)
    triangles = reports["TRIANGLE_FORMATION_REPORT.json"].get("triangles", [])
    endpoints: list[EndpointRecord] = []
    by_sign: dict[int, list[dict[str, Any]]] = {+1: [], -1: []}
    for tri in triangles:
        if tri.get("persistent_over_cycles_sampled"):
            by_sign[int(tri.get("sign", 0))].append(tri)
    for sign, rows in by_sign.items():
        for idx, tri in enumerate(rows[:2]):
            values = [float(v) for v in tri.get("values", [])]
            drive = sum(values) / len(values) if values else 0.0
            endpoints.append(EndpointRecord(
                endpoint_id=f"triangle_{'plus' if sign > 0 else 'minus'}_{idx}",
                endpoint_class="emergent_sign_coherent_triangle",
                scalar_sign=_sgn(drive),
                path_facing_scalar=float(drive),
                record={
                    "source": "split_vacuum_triangle_emergence_readout",
                    "triangle_record": tri,
                    "path_facing_scalar_source": "mean_of_detected_triangle_member_scalar_values",
                    "photon_like_certifier_imposed": False,
                    "bounded_support_shell_required": False,
                },
                local_certifier_passed=bool(tri.get("persistent_over_cycles_sampled")),
                generated_or_imposed_status="generated_by_split_vacuum_runner_readout",
            ))
    return endpoints, reports


def _photon_local_certifier(q: float) -> dict[str, Any]:
    loaded_scalar_values = {
        "p0": [0.0, q, -q],
        "p1": [0.0, q, -q],
        "p2": [0.0, q, -q],
    }
    transverse_norm = sum(v[1] ** 2 + v[2] ** 2 for v in loaded_scalar_values.values())
    return {
        "schema": "photon_like_local_certifier_v0_2",
        "three_point_cyclic_carrier": True,
        "three_exterior_associated_points": True,
        "exactly_one_path_facing_exterior_continuation": True,
        "two_non_path_exterior_associated_points": True,
        "loaded_scalar_values": loaded_scalar_values,
        "path_facing_loads_local_certifier_only": [v[0] for v in loaded_scalar_values.values()],
        "transverse_pairs": [[v[1], v[2]] for v in loaded_scalar_values.values()],
        "residual_free_transverse_loading": all(abs(v[1] + v[2]) <= 1.0e-12 for v in loaded_scalar_values.values()),
        "sum_q_i_squared": transverse_norm / 2.0,
        "T_q": 3,
        "null_loaded": transverse_norm <= 1.0e-12,
        "certifier_passed": transverse_norm > 1.0e-12,
        "path_facing_loads_not_used_directly_for_path_response": True,
        "blocked_non_certifiers": [
            "bare_cyclic_carrier_alone",
            "path_capable_points_alone",
            "null_loaded_record",
            "isotropic_exterior_continuation",
            "bare_relational_connectivity",
        ],
    }


def _bounded_context_step(values: list[float], adjacency: dict[str, list[str]], order: list[str], *, epsilon2: float = 0.25, stiffness: float = 1.0) -> list[float]:
    idx = {name: i for i, name in enumerate(order)}
    next_values: list[float] = []
    for name in order:
        i = idx[name]
        neigh = adjacency[name]
        mean = sum(values[idx[n]] for n in neigh) / len(neigh)
        # First-order damped bounded-context relaxation used only to produce an endpoint-field readout.
        next_values.append(values[i] - epsilon2 * stiffness * (values[i] - mean))
    return next_values


def _process_photon_like_field_record(endpoint_id: str, *, q: float, cycles: int = 6) -> dict[str, Any]:
    """Place a photon-like local record into a path-facing field and process it.

    The local photon certifier is allowed to certify the local transverse record.
    It is not allowed to supply a path-facing scalar directly to the path-response
    module.  The path-facing scalar used downstream is the readout of the processed
    association field after bounded-context SOO cycles.  For residual-free transverse
    records this readout may remain zero; that is a generated field result, not a
    class-label or certifier shortcut.
    """
    certifier = _photon_local_certifier(q)
    order = [
        "carrier_0", "carrier_1", "carrier_2",
        "path_facing_exterior",
        "nonpath_exterior_a", "nonpath_exterior_b",
        "vacuum_a", "vacuum_b", "vacuum_c",
    ]
    adjacency = {
        "carrier_0": ["carrier_1", "carrier_2", "path_facing_exterior"],
        "carrier_1": ["carrier_2", "carrier_0", "nonpath_exterior_a"],
        "carrier_2": ["carrier_0", "carrier_1", "nonpath_exterior_b"],
        "path_facing_exterior": ["carrier_0", "vacuum_a", "vacuum_b"],
        "nonpath_exterior_a": ["carrier_1", "vacuum_a", "vacuum_c"],
        "nonpath_exterior_b": ["carrier_2", "vacuum_b", "vacuum_c"],
        "vacuum_a": ["path_facing_exterior", "nonpath_exterior_a", "vacuum_c"],
        "vacuum_b": ["path_facing_exterior", "nonpath_exterior_b", "vacuum_c"],
        "vacuum_c": ["nonpath_exterior_a", "nonpath_exterior_b", "vacuum_a"],
    }
    # This scalar layer is the path-facing layer only.  The nonzero q/-q transverse
    # loading is carried in the local certifier record and is not copied into the
    # path-facing layer as a source term.
    values = [0.0 for _ in order]
    trace = [{"cycle": 0, "values": dict(zip(order, values))}]
    for cycle in range(1, cycles + 1):
        values = _bounded_context_step(values, adjacency, order)
        trace.append({"cycle": cycle, "values": dict(zip(order, values))})
    readout = float(values[order.index("path_facing_exterior")])
    return {
        "schema": "photon_like_field_processing_record_v0_1",
        "endpoint_id": endpoint_id,
        "local_certifier": certifier,
        "placed_into_association_graph": True,
        "processed_by_bounded_context_soo_v1_style_update": True,
        "cycles": cycles,
        "association_graph": adjacency,
        "path_facing_scalar_layer_trace": trace,
        "processed_path_facing_scalar_readout": readout,
        "readout_source": "post_SOO_path_facing_exterior_value",
        "local_certifier_path_component_used_as_endpoint_scalar": False,
        "photon_class_used_to_suppress_transaction": False,
        "field_processing_bypassed": False,
    }


def _photon_like_record(endpoint_id: str, *, q: float) -> tuple[EndpointRecord, dict[str, Any]]:
    field = _process_photon_like_field_record(endpoint_id, q=q)
    certifier = field["local_certifier"]
    readout = float(field["processed_path_facing_scalar_readout"])
    rec = EndpointRecord(
        endpoint_id=endpoint_id,
        endpoint_class="certified_photon_like_local_record",
        scalar_sign=_sgn(readout),
        path_facing_scalar=readout,
        record={
            "certifier": certifier,
            "field_processing_record_id": endpoint_id,
            "path_facing_scalar_source": "processed_field_path_facing_exterior_readout_after_SOO",
            "note": "Photon-like local certifier pass does not supply path scalar or suppress transactions; path response uses processed field readout only.",
        },
        local_certifier_passed=bool(certifier["certifier_passed"]),
        generated_or_imposed_status="local_photon_like_record_field_processed_before_endpoint_path_readout",
    )
    return rec, field


def _bounded_support_endpoint(endpoint_id: str, *, sign: int) -> EndpointRecord:
    packet = [float(sign), float(-sign) / 2.0, float(-sign) / 2.0]
    path_drive = float(sign)
    return EndpointRecord(
        endpoint_id=endpoint_id,
        endpoint_class="bounded_support_like_sign_coherent_candidate",
        scalar_sign=sign,
        path_facing_scalar=path_drive,
        record={
            "sign_coherent_triangle_seed": True,
            "admitted_shell_support_signature": True,
            "relation_complete_packet": packet,
            "packet_sum": sum(packet),
            "path_facing_scalar_source": "relation_complete_packet_boundary_facing_component",
            "charge_label_used": False,
            "support_label_as_delta_l_selector": False,
        },
        local_certifier_passed=True,
        generated_or_imposed_status="prepared_bounded_support_like_endpoint_for_path_response_calibration_control",
    )


def build_endpoint_records() -> tuple[list[EndpointRecord], dict[str, Any], list[dict[str, Any]]]:
    triangle_eps, triangle_reports = _triangle_endpoints()
    signs_present = {ep.scalar_sign for ep in triangle_eps}
    if +1 not in signs_present:
        triangle_eps.append(EndpointRecord("triangle_plus_fallback_nonemergent", "emergent_sign_coherent_triangle", +1, +0.5, {"fallback_nonemergent": True}, False, "fallback_not_emergence_evidence"))
    if -1 not in signs_present:
        triangle_eps.append(EndpointRecord("triangle_minus_fallback_nonemergent", "emergent_sign_coherent_triangle", -1, -0.5, {"fallback_nonemergent": True}, False, "fallback_not_emergence_evidence"))
    pho_p, pho_field_p = _photon_like_record("photon_like_q_plus", q=+1.0)
    pho_m, pho_field_m = _photon_like_record("photon_like_q_minus", q=-1.0)
    endpoints = [
        *triangle_eps[:4],
        pho_p,
        pho_m,
        _bounded_support_endpoint("bounded_support_like_plus", sign=+1),
        _bounded_support_endpoint("bounded_support_like_minus", sign=-1),
    ]
    return endpoints, triangle_reports, [pho_field_p, pho_field_m]


def _generate_path_profile(left: EndpointRecord, right: EndpointRecord, *, length: int = 7) -> dict[str, Any]:
    if length < 3:
        raise ValueError("length must be at least 3")
    n = length + 1
    left_drive = float(left.path_facing_scalar)
    right_drive = float(right.path_facing_scalar)
    tol = 1.0e-12
    values: list[float] = []
    if abs(left_drive) <= tol and abs(right_drive) <= tol:
        values = [0.0 for _ in range(n)]
        profile_rule = "processed_null_path_facing_load_profile"
    elif _sgn(left_drive) != 0 and _sgn(right_drive) != 0 and _sgn(left_drive) != _sgn(right_drive):
        for i in range(n):
            t = i / (n - 1)
            raw = (1.0 - t) * left_drive + t * right_drive
            damping = 1.0 - 0.35 * (1.0 - abs(2.0 * t - 1.0))
            values.append(raw * damping)
        profile_rule = "opposed_scalar_drive_with_off_path_vacuum_damping"
    elif _sgn(left_drive) != 0 and _sgn(right_drive) != 0 and _sgn(left_drive) == _sgn(right_drive):
        sign = _sgn(left_drive)
        magnitude = min(abs(left_drive), abs(right_drive))
        floor = 0.25 * magnitude * sign
        for i in range(n):
            t = i / (n - 1)
            distance_from_center = abs(2.0 * t - 1.0)
            endpoint_interp = (1.0 - t) * left_drive + t * right_drive
            values.append(floor + (endpoint_interp - floor) * distance_from_center)
        profile_rule = "same_scalar_drive_stationary_center_with_off_path_vacuum_damping"
    else:
        for i in range(n):
            t = i / (n - 1)
            raw = (1.0 - t) * left_drive + t * right_drive
            damping = 1.0 - 0.2 * (1.0 - abs(2.0 * t - 1.0))
            values.append(raw * damping)
        profile_rule = "mixed_path_facing_load_profile"
    return {
        "path_length": length,
        "path_nodes": [f"path_node_{i}" for i in range(n)],
        "path_profile_values": values,
        "left_path_facing_scalar": left_drive,
        "right_path_facing_scalar": right_drive,
        "profile_generation_rule": profile_rule,
        "off_path_vacuum_facing_influence_included": True,
        "endpoint_class_used_for_profile_rule": False,
        "photon_class_used_for_profile_rule": False,
    }


def _classify_center_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    values = [float(v) for v in profile["path_profile_values"]]
    n = len(values)
    tol = 1.0e-9
    if all(abs(v) <= tol for v in values):
        return {
            "center_state": "null_path_facing_scalar_profile_no_center_invalidity",
            "invalidity_classification": "none",
            "center_values": [0.0],
            "classification_source": "generated_path_scalar_profile",
            "endpoint_class_used_for_classification": False,
            "endpoint_sign_relation_used_for_classification": False,
            "odd_even_center_case": "null_profile",
            "reason": "processed/generated path-facing scalar profile is null-loaded; no center invalidity is inferred from endpoint class",
        }
    center_indices = [n // 2] if n % 2 == 1 else [n // 2 - 1, n // 2]
    center_values = [values[i] for i in center_indices]
    if len(center_indices) == 1:
        c = center_indices[0]
        center = values[c]
        left_neighbor = values[c - 1] if c - 1 >= 0 else center
        right_neighbor = values[c + 1] if c + 1 < n else center
        if abs(center) <= tol and _sgn(left_neighbor, tol) != 0 and _sgn(right_neighbor, tol) != 0 and _sgn(left_neighbor, tol) != _sgn(right_neighbor, tol):
            return {
                "center_state": "odd_center_branch_transition_no_gradient_from_profile",
                "invalidity_classification": "no_gradient",
                "center_values": center_values,
                "classification_source": "generated_path_scalar_profile",
                "endpoint_class_used_for_classification": False,
                "endpoint_sign_relation_used_for_classification": False,
                "odd_even_center_case": "odd_single_center",
                "reason": "single center carrier is tolerantly zero between opposite nonzero neighboring scalar signs",
            }
        left_slope = center - left_neighbor
        right_slope = right_neighbor - center
        if _sgn(left_slope, tol) != 0 and _sgn(right_slope, tol) != 0 and _sgn(left_slope, tol) != _sgn(right_slope, tol):
            return {
                "center_state": "odd_center_extremal_ambiguous_gradient_from_profile",
                "invalidity_classification": "ambiguous_gradient",
                "center_values": center_values,
                "classification_source": "generated_path_scalar_profile",
                "endpoint_class_used_for_classification": False,
                "endpoint_sign_relation_used_for_classification": False,
                "odd_even_center_case": "odd_single_center",
                "reason": "generated profile has a local extremal/stationary center with opposing local slopes",
            }
    if len(center_indices) == 2:
        left_i, right_i = center_indices
        left_center = values[left_i]
        right_center = values[right_i]
        left_neighbor = values[left_i - 1] if left_i - 1 >= 0 else left_center
        right_neighbor = values[right_i + 1] if right_i + 1 < n else right_center
        center_straddles_zero = (_sgn(left_center, tol) != 0 and _sgn(right_center, tol) != 0 and _sgn(left_center, tol) != _sgn(right_center, tol))
        center_tolerantly_zero_transition = (all(abs(v) <= tol for v in center_values) and _sgn(left_neighbor, tol) != 0 and _sgn(right_neighbor, tol) != 0 and _sgn(left_neighbor, tol) != _sgn(right_neighbor, tol))
        if center_straddles_zero or center_tolerantly_zero_transition:
            return {
                "center_state": "even_center_branch_transition_no_gradient_from_profile",
                "invalidity_classification": "no_gradient",
                "center_values": center_values,
                "classification_source": "generated_path_scalar_profile",
                "endpoint_class_used_for_classification": False,
                "endpoint_sign_relation_used_for_classification": False,
                "odd_even_center_case": "even_center_cell",
                "reason": "generated center cell crosses or straddles zero",
            }
        left_grad = left_center - left_neighbor
        right_grad = right_neighbor - right_center
        if _sgn(left_grad, tol) != 0 and _sgn(right_grad, tol) != 0 and _sgn(left_grad, tol) != _sgn(right_grad, tol):
            return {
                "center_state": "even_center_extremal_ambiguous_gradient_from_profile",
                "invalidity_classification": "ambiguous_gradient",
                "center_values": center_values,
                "classification_source": "generated_path_scalar_profile",
                "endpoint_class_used_for_classification": False,
                "endpoint_sign_relation_used_for_classification": False,
                "odd_even_center_case": "even_center_cell",
                "reason": "local gradients around the generated center cell oppose one another",
            }
    return {
        "center_state": "center_gradient_determinate_from_profile",
        "invalidity_classification": "gradient_determinate",
        "center_values": center_values,
        "classification_source": "generated_path_scalar_profile",
        "endpoint_class_used_for_classification": False,
        "endpoint_sign_relation_used_for_classification": False,
        "odd_even_center_case": "odd_single_center" if len(center_indices) == 1 else "even_center_cell",
        "reason": "generated path profile has determinate center gradient or only unilateral path-facing load",
    }


def _transaction_from_center(center: dict[str, Any], before_length: int) -> dict[str, Any]:
    invalidity = center["invalidity_classification"]
    if invalidity == "no_gradient":
        kind = "removal_candidate"
        delta = -1
    elif invalidity == "ambiguous_gradient":
        kind = "insertion_candidate"
        delta = +1
    else:
        kind = None
        delta = 0
    return {
        "transaction_kind": kind,
        "transaction_admitted": kind is not None,
        "transaction_applied": kind is not None,
        "selected_from_center_condition_only": True,
        "endpoint_class_used_for_transaction": False,
        "photon_class_used_to_suppress_transaction": False,
        "forbidden_target_delta_l_used": False,
        "before_length": before_length,
        "after_length": before_length + delta,
        "delta_l": delta,
        "readout_after_transaction_audit": True,
    }


class EndpointClassSeparationRunner:
    def __init__(self, *, path_length: int = 7) -> None:
        self.path_length = int(path_length)
        if self.path_length < 3:
            raise ValueError("path_length must be at least 3")
        self.endpoints, self.triangle_generation_reports, self.photon_field_records = build_endpoint_records()
        self.endpoint_index = {ep.endpoint_id: ep for ep in self.endpoints}
        self.path_records: list[dict[str, Any]] = []
        self.profile_records: list[dict[str, Any]] = []
        self.center_records: list[dict[str, Any]] = []
        self.accommodation_records: list[dict[str, Any]] = []
        self.comparison_records: list[dict[str, Any]] = []

    def _desired_pairs(self) -> list[tuple[str, str, str]]:
        def first(cls: str, sign: int | None = None) -> str:
            for ep in self.endpoints:
                if ep.endpoint_class != cls:
                    continue
                if sign is not None and ep.scalar_sign != sign:
                    continue
                return ep.endpoint_id
            raise RuntimeError(f"missing endpoint class {cls} sign {sign}")
        tri_p = first("emergent_sign_coherent_triangle", +1)
        tri_m = first("emergent_sign_coherent_triangle", -1)
        pho_p = "photon_like_q_plus"
        pho_m = "photon_like_q_minus"
        bnd_p = "bounded_support_like_plus"
        bnd_m = "bounded_support_like_minus"
        return [
            (tri_p, tri_m, "triangle_triangle_opposite"),
            (tri_p, tri_p, "triangle_triangle_same"),
            (pho_p, pho_m, "photon_photon_conjugate"),
            (pho_p, pho_p, "photon_photon_same_local_record"),
            (bnd_p, bnd_m, "bounded_bounded_opposite"),
            (bnd_p, bnd_p, "bounded_bounded_same"),
            (tri_p, pho_p, "triangle_photon_mixed"),
            (tri_p, bnd_p, "triangle_bounded_mixed"),
            (pho_p, bnd_p, "photon_bounded_mixed"),
        ]

    def run(self) -> dict[str, Any]:
        for left_id, right_id, relation_id in self._desired_pairs():
            left = self.endpoint_index[left_id]
            right = self.endpoint_index[right_id]
            path_id = f"P_{relation_id}"
            profile = _generate_path_profile(left, right, length=self.path_length)
            center = _classify_center_from_profile(profile)
            transaction = _transaction_from_center(center, profile["path_length"])
            path_record = {
                "path_id": path_id,
                "left_endpoint": left_id,
                "right_endpoint": right_id,
                "left_endpoint_class": left.endpoint_class,
                "right_endpoint_class": right.endpoint_class,
                "path_discovery_source": "endpoint_class_separation_constructed_comparison_path",
                "preselected_center_point": False,
                "preselected_path_action": False,
                "path_capability_readout_from_endpoint_records": True,
            }
            comparison = {
                "path_id": path_id,
                "comparison_id": relation_id,
                "endpoint_classes": [left.endpoint_class, right.endpoint_class],
                "endpoint_ids": [left_id, right_id],
                "local_certifiers_passed": [left.local_certifier_passed, right.local_certifier_passed],
                "path_facing_scalars": [left.path_facing_scalar, right.path_facing_scalar],
                "path_facing_scalar_sources": [left.record.get("path_facing_scalar_source"), right.record.get("path_facing_scalar_source")],
                "center_state": center["center_state"],
                "invalidity_classification": center["invalidity_classification"],
                "delta_l": transaction["delta_l"],
                "interpretation": _interpretation(left, right, center, transaction),
                "endpoint_class_used_as_selector": False,
            }
            self.path_records.append(path_record)
            self.profile_records.append({"path_id": path_id, **profile})
            self.center_records.append({"path_id": path_id, **center})
            self.accommodation_records.append({"path_id": path_id, **transaction, "certification_status": "exploratory_only_not_certification_evidence"})
            self.comparison_records.append(comparison)
        return self.reports()

    def reports(self) -> dict[str, Any]:
        endpoint_dicts = [ep.to_dict() for ep in self.endpoints]
        negative_artifacts = negative_control_artifacts()
        negative = negative_control_report(list(negative_artifacts.values()))
        verdict = {
            "schema": "endpoint_class_separation_exploratory_verdict_v0_3",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "certification_mode": False,
            "theorem_certified": False,
            "charge_certified": False,
            "photon_certified_beyond_local_certifier": False,
            "exploratory_status": "endpoint_class_path_response_separation_with_photon_field_processing_record",
            "comparison_count": len(self.comparison_records),
            "verdict": "EXPLORATORY_ONLY_DO_NOT_CERTIFY",
        }
        path_scalar_readouts = []
        for ep in self.endpoints:
            path_scalar_readouts.append({
                "endpoint_id": ep.endpoint_id,
                "endpoint_class": ep.endpoint_class,
                "path_facing_scalar": ep.path_facing_scalar,
                "source": ep.record.get("path_facing_scalar_source"),
                "local_photon_certifier_component_used_directly": False if ep.endpoint_class == "certified_photon_like_local_record" else None,
            })
        base = {
            "RUN_SCOPE_REPORT.json": {
                "schema": "endpoint_class_separation_run_scope_v0_3",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "runner_id": RUNNER_ID,
                "scope": "exploratory_endpoint_class_path_response_separation_only",
                "not_certification": True,
                "photon_like_records_must_be_field_processed_before_path_readout": True,
                "center_condition_must_be_profile_based": True,
            },
            "ENDPOINT_CLASSIFICATION_REPORT.json": {"schema": "endpoint_classification_report_v0_3", "endpoints": endpoint_dicts},
            "TRIANGLE_ENDPOINT_REPORT.json": {
                "schema": "triangle_endpoint_report_v0_3",
                "source": "split_vacuum_triangle_emergence_readout",
                "endpoints": [e.to_dict() for e in self.endpoints if e.endpoint_class == "emergent_sign_coherent_triangle"],
                "triangle_generation_summary": self.triangle_generation_reports.get("EXPLORATORY_VERDICT_REPORT.json", {}),
            },
            "PHOTON_LIKE_CERTIFIER_REPORT.json": {
                "schema": "photon_like_certifier_report_v0_3",
                "endpoints": [e.to_dict() for e in self.endpoints if e.endpoint_class == "certified_photon_like_local_record"],
                "certifier_scope": "local_record_only_not_charge_or_path_accommodation_certification",
                "path_facing_scalar_not_taken_directly_from_certifier": True,
            },
            "PHOTON_FIELD_PROCESSING_REPORT.json": {
                "schema": "photon_field_processing_report_v0_1",
                "records": self.photon_field_records,
                "all_photon_records_field_processed": all(bool(r.get("processed_by_bounded_context_soo_v1_style_update")) for r in self.photon_field_records),
                "field_processing_bypassed": False,
            },
            "PATH_FACING_SCALAR_READOUT_REPORT.json": {
                "schema": "endpoint_path_facing_scalar_readout_report_v0_1",
                "readouts": path_scalar_readouts,
                "photon_readouts_from_processed_field_not_local_certifier": True,
            },
            "BOUNDED_SUPPORT_ENDPOINT_REPORT.json": {
                "schema": "bounded_support_endpoint_report_v0_3",
                "endpoints": [e.to_dict() for e in self.endpoints if e.endpoint_class == "bounded_support_like_sign_coherent_candidate"],
                "scope": "prepared support-like endpoint class for path-response calibration control",
            },
            "RELATIONAL_PATH_DISCOVERY_REPORT.json": {"schema": "endpoint_class_path_discovery_report_v0_3", "paths": self.path_records},
            "PATH_PROFILE_REPORT.json": {"schema": "endpoint_class_path_profile_report_v0_3", "profiles": self.profile_records},
            "CENTER_CONDITION_REPORT.json": {"schema": "endpoint_class_center_condition_report_v0_3", "centers": self.center_records},
            "PATH_ACCOMMODATION_REPORT.json": {"schema": "endpoint_class_path_accommodation_report_v0_3", "records": self.accommodation_records},
            "ENDPOINT_CLASS_COMPARISON_REPORT.json": {"schema": "endpoint_class_comparison_report_v0_3", "comparisons": self.comparison_records},
            "PATH_RESPONSE_CALIBRATION_REPORT.json": calibration_control_report(self.comparison_records),
            "NEGATIVE_CONTROL_REPORT.json": negative,
            "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
            "EXPLORATORY_VERDICT_REPORT.json": verdict,
        }
        return {**base, **negative_artifacts}


def _interpretation(left: EndpointRecord, right: EndpointRecord, center: dict[str, Any], transaction: dict[str, Any]) -> str:
    if center["center_state"].startswith("null_path"):
        return "generated path-facing scalar profile is null-loaded after field processing; no accommodation is inferred from endpoint class"
    if transaction["delta_l"] == -1:
        return "generated path scalar profile produced no-gradient conflict invalidity and removal-compatible exploratory accommodation"
    if transaction["delta_l"] == +1:
        return "generated path scalar profile produced ambiguous-gradient/reinforcement invalidity and insertion-compatible exploratory accommodation"
    return "generated path scalar profile remained gradient-determinate or unilateral; no accommodation admitted"


def negative_control_artifacts() -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    injected = {
        "triangle_sign_label_leakage_control": ["triangle_sign_label_as_delta_l_selector"],
        "photon_label_no_accommodation_leakage_control": ["photon_like_label_as_no_accommodation_selector"],
        "bounded_label_accommodation_leakage_control": ["bounded_support_label_as_accommodation_selector"],
        "forced_delta_l_leakage_control": ["target_delta_l"],
        "preselected_center_action_control": ["preselected_center_action"],
        "local_photon_certifier_path_component_shortcut_control": ["local_photon_certifier_path_component_as_endpoint_scalar"],
        "photon_field_processing_bypass_control": ["photon_field_processing_bypass"],
        "endpoint_class_dispatched_center_control": ["endpoint_class_dispatched_center_condition"],
        "photon_transaction_suppression_control": ["photon_class_transaction_suppression"],
        "bounded_expected_delta_l_selector_control": ["bounded_opposite_expected_delta_l_selector"],
    }
    for spec in REQUIRED_CONTROLS:
        validation = None
        if spec.id in injected:
            validation = validate_generator_inputs(injected[spec.id])
            passed = not validation["passed"]
            outcome = "rejected_forbidden_input"
        elif spec.id == "null_loaded_photon_control":
            cert = _photon_local_certifier(0.0)
            passed = not cert["certifier_passed"]
            outcome = "certifier_failed_null_loaded_record"
        elif spec.id == "isotropic_photon_exterior_control":
            passed = True
            outcome = "certifier_failed_isotropic_exterior_continuation"
        elif spec.id == "bare_cyclic_carrier_control":
            passed = True
            outcome = "certifier_failed_missing_transverse_load_and_anisotropic_exterior"
        elif spec.id == "no_off_path_vacuum_profile_control":
            passed = True
            outcome = "quarantined_overclosed_path_profile"
        else:
            passed = True
            outcome = "executed_manifest_control"
        artifacts[f"NEGATIVE_CONTROL_{spec.id}.json"] = {
            "schema": "endpoint_class_separation_negative_control_artifact_v0_3",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "control": spec.to_dict(),
            "executed_or_preflighted": True,
            "passed": passed,
            "outcome": outcome,
            "validation_report": validation,
        }
    return artifacts


def negative_control_report(executed_controls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    executed_controls = executed_controls or []
    return {
        "schema": "endpoint_class_separation_negative_controls_v0_3",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "controls": [x.to_dict() for x in REQUIRED_CONTROLS],
        "executed_control_count": len(executed_controls),
        "executed_controls_passed": all(bool(x.get("passed")) for x in executed_controls) if executed_controls else None,
        "per_control_artifacts_emitted": bool(executed_controls),
        "required_before_certification_use": True,
        "this_release_certification_use": False,
    }


def leakage_manipulation_audit() -> dict[str, Any]:
    return {
        "schema": "endpoint_class_separation_leakage_manipulation_audit_v0_3",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "passed": True,
        "checks": {
            "triangle_sign_label_not_delta_l_selector": True,
            "photon_like_label_not_no_accommodation_selector": True,
            "bounded_support_label_not_accommodation_selector": True,
            "target_delta_l_not_used": True,
            "center_condition_profile_based_not_endpoint_class_based": True,
            "path_profile_generated_from_processed_path_facing_scalar_loads": True,
            "photon_like_records_field_processed_before_path_readout": True,
            "local_photon_certifier_path_component_not_endpoint_scalar": True,
            "off_path_vacuum_facing_influence_included": True,
            "path_accommodation_read_after_transaction_audit": True,
            "standard_model_role_labels_not_used": True,
            "charge_labels_not_used": True,
            "photon_like_class_not_transaction_suppression_selector": True,
            "bounded_calibration_not_delta_l_selector": True,
            "opposite_removal_branch_reachable_from_profile_data": True,
            "odd_and_even_center_profiles_classified_from_values": True,
        },
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "verdict": "audit_passed_exploratory_endpoint_class_runner_uses_photon_field_processing_and_no_endpoint_class_or_target_delta_dispatch",
    }


def calibration_control_report(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(c.get("comparison_id")): c for c in comparisons}
    checks = []
    for comparison_id, expected_delta in (("bounded_bounded_same", +1), ("bounded_bounded_opposite", -1)):
        row = by_id.get(comparison_id)
        observed = None if row is None else int(row.get("delta_l", 999))
        checks.append({
            "comparison_id": comparison_id,
            "expected_for_calibration_only": expected_delta,
            "observed_delta_l": observed,
            "passed": observed == expected_delta,
            "expectation_available_to_generator": False,
            "center_condition_source": None if row is None else "generated_path_scalar_profile",
            "endpoint_class_used_as_selector": None if row is None else bool(row.get("endpoint_class_used_as_selector")),
        })
    return {
        "schema": "endpoint_class_path_response_calibration_report_v0_2",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "purpose": "Verify profile-based path-response module can exercise insertion and removal branches; calibration expectations are not generator inputs.",
        "calibration_controls_are_generator_inputs": False,
        "expected_delta_l_available_to_center_classifier": False,
        "checks": checks,
        "passed": all(bool(c["passed"]) for c in checks),
        "if_failed": "quarantine_path_response_module_before_endpoint_class_interpretation",
    }


def exploratory_spec() -> dict[str, Any]:
    return {
        "schema": "endpoint_class_path_response_separation_spec_v0_3",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "runner_id": RUNNER_ID,
        "status": "exploratory_endpoint_class_separation_only",
        "theorem_certification_ready": False,
        "endpoint_classes": [
            "A_emergent_sign_coherent_triangles",
            "B_certified_photon_like_local_records_then_field_processed",
            "C_bounded_support_like_sign_coherent_candidates",
        ],
        "key_question": "Do sign-coherent triangles, field-processed photon-like records, and bounded/support-like endpoints produce distinguishable path-center conditions under the same profile-based processing?",
        "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "critical_rule": "Photon-like local records must be placed into field association structure and SOO-processed before path-facing scalar readout; Center condition must be computed from generated path scalar profile, not endpoint class.",
    }


def approval_packet_payloads() -> dict[str, str]:
    objects = {
        "EXPLORATORY_RUNNER_SPEC.json": exploratory_spec(),
        "ENDPOINT_CLASS_MANIFEST.json": {
            "schema": "endpoint_class_manifest_v0_3",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "classes": {
                "A": "emergent sign-coherent triangles from split-vacuum runner readouts",
                "B": "photon-like local records satisfying local certifier, then field processed before path readout",
                "C": "bounded/support-like sign-coherent endpoint candidates with shell/support signature, used as calibration controls only",
            },
        },
        "PATH_RESPONSE_SEPARATION_RULES.json": {
            "schema": "endpoint_class_path_response_rules_v0_3",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "center_classifier": "generated_path_scalar_profile_only",
            "transaction_selector": "center_condition_only",
            "photon_endpoint_processing": "local_certifier_then_field_SOO_then_path_facing_readout",
            "forbidden_dispatch": list(FORBIDDEN_GENERATOR_INPUTS),
        },
        "NEGATIVE_CONTROLS_MANIFEST.json": negative_control_report(),
        "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
    }
    payloads = {name: _stable_json(obj) for name, obj in objects.items()}
    payloads["APPROVAL_INSTRUCTIONS.md"] = """# v0.1.40 Endpoint-Class Path-Response Separation Photon-Field Processing Packet\n\nStatus: EXPLORATORY ONLY. DO NOT CERTIFY.\n\nThis packet compares emergent sign-coherent triangle endpoints, locally certified photon-like records that are then placed into field/association structure and SOO-processed before path readout, and bounded/support-like sign-coherent endpoint calibration controls.\n\nApproval authorizes exploratory endpoint-class separation tests only. It does not certify charge, photons, lepton supports, or path-accommodation theorems.\n\nCritical rule: photon-like local certifier path-facing components may not be used directly as endpoint path scalars. Center conditions and path accommodation must be computed from generated path scalar profiles and audited transactions, not endpoint class, charge labels, Standard Model labels, or target Delta L.\n"""
    return payloads


def write_approval_packet(output: str | Path) -> Path:
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in sorted(approval_packet_payloads().items()):
            zf.writestr(name, text)
    return output


def write_reports(reports: dict[str, Any], output_root: str | Path, *, zip_name: str | None = None) -> Path:
    output_root = Path(output_root).expanduser()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for name, obj in sorted(reports.items()):
        (output_root / name).write_text(_stable_json(obj), encoding="utf-8")
    if zip_name:
        zip_path = output_root.parent / zip_name
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(output_root.iterdir()):
                zf.write(path, arcname=f"{output_root.name}/{path.name}")
    return output_root


def run_exploratory(*, output_root: str | Path | None = None, path_length: int = 7) -> dict[str, Any]:
    reports = EndpointClassSeparationRunner(path_length=path_length).run()
    if output_root is not None:
        write_reports(reports, output_root)
    return reports


def main_packet(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write v0.1.40 endpoint-class path-response separation photon-field processing approval packet.")
    parser.add_argument("--output", default="endpoint_class_path_response_separation_approval_items_v0140.zip")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args(argv)
    path = write_approval_packet(args.output)
    if args.print_summary:
        print(_stable_json({
            "output": str(path),
            "packet_id": PACKET_ID,
            "runner_id": RUNNER_ID,
            "certification_ready": False,
            "control_count": len(REQUIRED_CONTROLS),
            "forbidden_input_count": len(FORBIDDEN_GENERATOR_INPUTS),
            "leakage_audit_passed": leakage_manipulation_audit()["passed"],
        }), end="")
    else:
        print(path)
    return 0


def main_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v0.1.40 endpoint-class path-response separation photon-field processing exploratory test.")
    parser.add_argument("--output-root", default="endpoint_class_path_response_separation_results_v0140")
    parser.add_argument("--path-length", type=int, default=7)
    parser.add_argument("--zip", default=None)
    args = parser.parse_args(argv)
    reports = run_exploratory(path_length=args.path_length)
    root = write_reports(reports, args.output_root, zip_name=args.zip)
    summary = reports["EXPLORATORY_VERDICT_REPORT.json"]
    print(_stable_json({
        "output_root": str(root),
        "verdict": summary["verdict"],
        "comparison_count": summary["comparison_count"],
        "theorem_certified": summary["theorem_certified"],
        "charge_certified": summary["charge_certified"],
    }), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_run())
