from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .fingerprints import stable_json_hash

FORBIDDEN_MONITOR_INPUTS = frozenset({
    "orientation",
    "same_label",
    "opposite_label",
    "target_delta_l",
})


def _to_dict(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _to_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_dict(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    return value


def _readout_payloads(readouts: Sequence[Any]) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for report in readouts:
        name = str(getattr(report, "name", ""))
        payload = getattr(report, "payload", {})
        if isinstance(payload, dict):
            payloads[name] = payload
    return payloads


def _optional_module_params(optional_module_report: Any) -> dict[str, dict[str, Any]]:
    report = _to_dict(optional_module_report) or {}
    details = report.get("details", {}) if isinstance(report, dict) else {}
    from_details = details.get("module_params_by_id", {}) if isinstance(details, dict) else {}
    if isinstance(from_details, dict) and from_details:
        return {str(k): dict(v) if isinstance(v, dict) else {} for k, v in from_details.items()}
    # Backward-compatible fallback for pre-v0.1.34 reports: params were not stored.
    modules = report.get("modules", ()) if isinstance(report, dict) else ()
    out: dict[str, dict[str, Any]] = {}
    for module in modules if isinstance(modules, list) else []:
        if isinstance(module, dict):
            out[str(module.get("module_id", ""))] = dict(module.get("params", {}) or {})
    return out


def _status_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"true", "yes", "passed", "enabled"}:
            return True
        if lower in {"false", "no", "failed", "disabled"}:
            return False
    return bool(value)


def _soo_candidate_flag(soo_execution_report: Any) -> bool | None:
    payload = _to_dict(soo_execution_report) or {}
    if not isinstance(payload, dict):
        return None
    details = payload.get("details", {})
    if isinstance(details, dict) and "candidate_not_admitted" in details:
        return bool(details.get("candidate_not_admitted"))
    return None


def _init_settling_status(initialization_settling_report: Any, contract: Any) -> dict[str, Any]:
    report = _to_dict(initialization_settling_report)
    contract_dict = _to_dict(contract) or {}
    required = tuple(str(x) for x in contract_dict.get("required_initialization", ()) if str(x).strip()) if isinstance(contract_dict, dict) else ()
    requires_settling = any(
        token in item.lower()
        for item in required
        for token in ("steady", "settling", "recurrent")
    )
    if not isinstance(report, dict):
        return {
            "contract_required_initialization": list(required),
            "contract_requires_settling_or_recurrence": bool(requires_settling),
            "initialization_settling_report_present": False,
            "initialization_settling_enabled": None,
            "initialization_settling_passed": False if requires_settling else None,
            "blocking_reason": "contract requires steady/recurrent initialization but INITIALIZATION_SETTLING_REPORT is absent" if requires_settling else None,
        }
    enabled = bool(report.get("enabled", False))
    reached = bool(report.get("steady_state_reached", False))
    passed = bool((not requires_settling) or (enabled and reached))
    reason = None
    if requires_settling and not enabled:
        reason = "contract requires steady/recurrent initialization but settling was disabled"
    elif requires_settling and enabled and not reached:
        reason = "contract requires steady/recurrent initialization but the settling report did not reach steady/recurrent status"
    return {
        "contract_required_initialization": list(required),
        "contract_requires_settling_or_recurrence": bool(requires_settling),
        "initialization_settling_report_present": True,
        "initialization_settling_enabled": enabled,
        "initialization_settling_passed": passed,
        "steady_state_reached": reached,
        "steady_state_type": report.get("steady_state_type"),
        "status": report.get("status"),
        "blocking_reason": reason,
    }


def _center_summary(center_payload: dict[str, Any]) -> dict[str, Any]:
    layers = center_payload.get("layers", [])
    zero_ells: list[int] = []
    first_nonzero: dict[str, Any] | None = None
    last_values: list[float] | None = None
    for row in layers if isinstance(layers, list) else []:
        if not isinstance(row, dict):
            continue
        ell = int(row.get("ell", 0))
        values = row.get("center_values", [])
        if row.get("tolerance_center_zero") or row.get("tolerance_center_balanced_edge"):
            zero_ells.append(ell)
        elif first_nonzero is None:
            first_nonzero = {"ell": ell, "center_values": values}
        last_values = values if isinstance(values, list) else None
    all_ells = [int(row.get("ell", 0)) for row in layers if isinstance(row, dict)] if isinstance(layers, list) else []
    final_zero = bool(zero_ells and all_ells and zero_ells[-1] == all_ells[-1])
    return {
        "center_condition_observed": bool(zero_ells),
        "zero_or_balanced_center_ells": zero_ells,
        "center_condition_persistent_through_final_layer": final_zero,
        "center_condition_transient": bool(zero_ells and not final_zero),
        "first_nonzero_center_after_initial_condition": first_nonzero,
        "final_center_values": last_values,
        "center_kind": center_payload.get("center_kind"),
        "center_points": center_payload.get("center_points"),
        "tolerance": center_payload.get("tolerance"),
    }


def _delta_summary(delta_payload: dict[str, Any]) -> dict[str, Any]:
    audits = delta_payload.get("edge_audits_by_state", [])
    first = audits[0] if isinstance(audits, list) and audits else {}
    last = audits[-1] if isinstance(audits, list) and audits else {}
    return {
        "declared_path_length": delta_payload.get("declared_path_length"),
        "delta_declared_path_length": delta_payload.get("delta_declared_path_length"),
        "classification": delta_payload.get("classification"),
        "declared_path_intact_initial": bool(first.get("declared_path_intact")) if isinstance(first, dict) else None,
        "declared_path_intact_final": bool(last.get("declared_path_intact")) if isinstance(last, dict) else None,
        "declared_path_intact_all_states": all(bool(row.get("declared_path_intact")) for row in audits) if isinstance(audits, list) else None,
        "initial_present_declared_edge_count": first.get("present_declared_edge_count") if isinstance(first, dict) else None,
        "final_present_declared_edge_count": last.get("present_declared_edge_count") if isinstance(last, dict) else None,
        "expected_declared_edges": delta_payload.get("expected_declared_edges"),
        "path_points": delta_payload.get("path_points"),
    }


def build_effective_orientation_record(*, readouts: Sequence[Any], path_report: Any | None) -> dict[str, Any]:
    payloads = _readout_payloads(readouts)
    relation = payloads.get("relation_complete_packet_readout", {})
    layers = relation.get("layers", [])
    first_layer = layers[0] if isinstance(layers, list) and layers else {}
    supports = first_layer.get("supports", []) if isinstance(first_layer, dict) else []
    support_records: list[dict[str, Any]] = []
    for support in supports if isinstance(supports, list) else []:
        if not isinstance(support, dict):
            continue
        phase_records = support.get("phase_records", [])
        chi = [float(r.get("chi_boundary_minus_dressing", 0.0)) for r in phase_records if isinstance(r, dict)]
        support_records.append({
            "support": support.get("support"),
            "handedness_label": support.get("handedness"),
            "chi_triple_ell0": chi,
            "chi_triple_hash": stable_json_hash(chi),
        })
    comparison: dict[str, Any] = {"available": len(support_records) >= 2}
    if len(support_records) >= 2:
        left = support_records[0]["chi_triple_ell0"]
        right = support_records[1]["chi_triple_ell0"]
        if len(left) == len(right) and left:
            tol = 1.0e-12
            identical = all(abs(a - b) <= tol for a, b in zip(left, right))
            reversed_ = all(abs(a + b) <= tol for a, b in zip(left, right))
            comparison.update({
                "support_B_packet_identical_to_support_A": bool(identical),
                "support_B_packet_reversed_relative_to_support_A": bool(reversed_),
                "max_abs_packet_difference": max(abs(a - b) for a, b in zip(left, right)),
                "max_abs_packet_sum_for_reversal_test": max(abs(a + b) for a, b in zip(left, right)),
                "effective_packet_relation": "identical" if identical else ("reversed" if reversed_ else "different"),
            })
    orientation_label = str(getattr(path_report, "orientation", "unspecified")) if path_report is not None else "unspecified"
    theorem_tested = True
    status = "effective_orientation_record_available"
    if orientation_label == "opposite" and comparison.get("support_B_packet_identical_to_support_A"):
        theorem_tested = False
        status = "theorem_not_tested_effective_orientation_missing"
    return {
        "report_schema": "rank3_effective_orientation_record_v1",
        "status": status,
        "diagnostic_only": True,
        "path_orientation_label_reported_but_not_used_for_update": orientation_label,
        "support_packet_records": support_records,
        "support_packet_comparison_ell0": comparison,
        "effective_orientation_present": bool(theorem_tested),
        "forbidden_interpretations": [
            "handedness/orientation labels do not by themselves constitute scalar packet reversal",
            "this report must not trigger a path edit or change scalar values",
        ],
        "record_hash": stable_json_hash({"supports": support_records, "comparison": comparison, "orientation_label": orientation_label}),
    }


def build_path_monitor_decision_report(*, readouts: Sequence[Any], optional_module_report: Any) -> dict[str, Any]:
    payloads = _readout_payloads(readouts)
    center = _center_summary(payloads.get("center_locus_readout", {}))
    params_by_id = _optional_module_params(optional_module_report)
    params = dict(params_by_id.get("admitted_nonlabel_path_monitor_v1", {}))
    monitor_declared = "admitted_nonlabel_path_monitor_v1" in params_by_id
    decision_inputs = tuple(str(x) for x in params.get("decision_inputs", ()) if str(x).strip())
    forbidden = sorted(FORBIDDEN_MONITOR_INPUTS & set(decision_inputs))
    monitor_ran = False
    edit_request_emitted = False
    if not monitor_declared:
        no_edit_reason = "no admitted_nonlabel_path_monitor_v1 policy declared"
    else:
        no_edit_reason = "admitted_nonlabel_path_monitor_v1 is a policy declaration only in this release; no executable monitor transaction emitted an edit request"
        if center["center_condition_observed"] and center["center_condition_transient"]:
            no_edit_reason += "; observed center condition was transient and was not converted into a removal transaction"
    return {
        "report_schema": "rank3_path_monitor_decision_report_v1",
        "diagnostic_only": True,
        "monitor_policy_declared": bool(monitor_declared),
        "monitor_ran": monitor_ran,
        "monitor_inputs_read": list(decision_inputs),
        "forbidden_inputs_read": forbidden,
        "forbidden_input_gate_passed": not forbidden,
        "center_condition_observed": center["center_condition_observed"],
        "center_condition_summary": center,
        "edit_request_emitted": edit_request_emitted,
        "no_edit_reason": no_edit_reason,
        "forbidden_interpretations": [
            "center zero is not treated as an intrinsic path-removal rule",
            "same/opposite labels are not monitor inputs",
            "this report records absence/presence of a transaction; it does not manufacture one",
        ],
    }


def build_path_edit_admission_report(*, monitor_report: dict[str, Any]) -> dict[str, Any]:
    requested = bool(monitor_report.get("edit_request_emitted"))
    return {
        "report_schema": "rank3_path_edit_admission_report_v1",
        "diagnostic_only": True,
        "path_edit_requested": requested,
        "path_edit_admitted": False,
        "path_edit_rejected": False,
        "admission_status": "not_requested" if not requested else "not_implemented_no_admission_record",
        "reason": "no external path-edit request was emitted" if not requested else "path-edit request admission engine is not present in this release",
    }


def build_geometry_transaction_report(*, readouts: Sequence[Any], path_edit_admission_report: dict[str, Any]) -> dict[str, Any]:
    payloads = _readout_payloads(readouts)
    delta = _delta_summary(payloads.get("delta_l_classification", {}))
    requested = bool(path_edit_admission_report.get("path_edit_requested"))
    admitted = bool(path_edit_admission_report.get("path_edit_admitted"))
    applied = False
    before_length = delta.get("declared_path_length")
    observed_delta = delta.get("delta_declared_path_length")
    after_length = before_length + observed_delta if isinstance(before_length, int) and isinstance(observed_delta, int) else before_length
    return {
        "report_schema": "rank3_geometry_transaction_report_v1",
        "diagnostic_only": True,
        "transaction_requested": requested,
        "transaction_admitted": admitted,
        "transaction_applied": applied,
        "before_path_length": before_length,
        "after_path_length": after_length,
        "observed_declared_path_length_delta": observed_delta,
        "declared_path_intact_all_states": delta.get("declared_path_intact_all_states"),
        "reason": "no admitted path-edit transaction was available/applied" if not applied else "transaction applied",
        "forbidden_interpretations": [
            "association remap changes associations only; scalar values are not edited here",
            "this transaction report does not add/remove path points unless an admitted external request exists",
        ],
    }


def build_active_path_record_report(*, readouts: Sequence[Any], path_report: Any | None) -> dict[str, Any]:
    payloads = _readout_payloads(readouts)
    delta = _delta_summary(payloads.get("delta_l_classification", {}))
    declared_points = tuple(int(x) for x in getattr(path_report, "path_points", ())) if path_report is not None else tuple(delta.get("path_points") or ())
    initial_edges = delta.get("expected_declared_edges")
    final_edges = delta.get("expected_declared_edges")
    observed_delta = delta.get("delta_declared_path_length")
    return {
        "report_schema": "rank3_active_path_record_report_v1",
        "diagnostic_only": True,
        "initial_active_path": {
            "path_points": list(declared_points),
            "declared_edges": initial_edges,
            "declared_path_length": delta.get("declared_path_length"),
            "declared_path_intact": delta.get("declared_path_intact_initial"),
        },
        "final_active_path": {
            "path_points": list(declared_points),
            "declared_edges": final_edges,
            "declared_path_length": delta.get("declared_path_length"),
            "declared_path_intact": delta.get("declared_path_intact_final"),
        },
        "active_path_record_mutation_supported": False,
        "active_path_length_delta": observed_delta,
        "declared_path_intact_all_states": delta.get("declared_path_intact_all_states"),
        "reason": "no active/declared path-record mutation primitive executed in this run",
    }


def build_theorem_failure_trace(
    *,
    readouts: Sequence[Any],
    path_report: Any | None,
    optional_module_report: Any,
    soo_execution_report: Any,
    initialization_settling_report: Any,
    modeling_intent_contract: Any,
    scalar_update_metadata: Any,
    association_remap_metadata: Any,
    effective_orientation_record: dict[str, Any],
    path_monitor_decision_report: dict[str, Any],
    path_edit_admission_report: dict[str, Any],
    geometry_transaction_report: dict[str, Any],
    active_path_record_report: dict[str, Any],
) -> dict[str, Any]:
    payloads = _readout_payloads(readouts)
    center = _center_summary(payloads.get("center_locus_readout", {}))
    delta = _delta_summary(payloads.get("delta_l_classification", {}))
    role = payloads.get("role_path_midpoint_arrival_readout", {})
    init_status = _init_settling_status(initialization_settling_report, modeling_intent_contract)
    candidate_flag = _soo_candidate_flag(soo_execution_report)
    scalar_status = str(getattr(getattr(scalar_update_metadata, "status", None), "value", getattr(scalar_update_metadata, "status", "unknown")))
    remap_status = str(getattr(getattr(association_remap_metadata, "status", None), "value", getattr(association_remap_metadata, "status", "unknown")))
    mechanisms_non_candidate = bool(scalar_status == "admitted" and remap_status == "admitted" and candidate_flag is not True)
    no_edit_reasons: list[str] = []
    if not effective_orientation_record.get("effective_orientation_present", True):
        no_edit_reasons.append("same/opposite label did not correspond to the required effective scalar-packet distinction")
    if not path_monitor_decision_report.get("monitor_ran"):
        no_edit_reasons.append(str(path_monitor_decision_report.get("no_edit_reason")))
    if not geometry_transaction_report.get("transaction_applied"):
        no_edit_reasons.append(str(geometry_transaction_report.get("reason")))
    if init_status.get("blocking_reason"):
        no_edit_reasons.append(str(init_status.get("blocking_reason")))
    if candidate_flag is True:
        no_edit_reasons.append("SOO execution report marked candidate_not_admitted=true")
    verdict = "theorem_not_certified"
    return {
        "report_schema": "rank3_theorem_failure_trace_v1",
        "diagnostic_only": True,
        "verdict": verdict,
        "failure_chain": {
            "support_packet_formation": {
                "relation_complete_packet_readout_present": "relation_complete_packet_readout" in payloads,
                "effective_orientation_record_status": effective_orientation_record.get("status"),
                "effective_orientation_present": effective_orientation_record.get("effective_orientation_present"),
                "support_packet_comparison_ell0": effective_orientation_record.get("support_packet_comparison_ell0"),
            },
            "center_scalar_condition": center,
            "midpoint_arrival_summary": {
                "late_abs_sum_mean": role.get("late_abs_sum_mean"),
                "late_abs_contrast_mean": role.get("late_abs_contrast_mean"),
                "late_center_vacuum_equivalent_fraction": role.get("late_center_vacuum_equivalent_fraction"),
            },
            "nonlabel_monitor_decision": path_monitor_decision_report,
            "path_edit_admission": path_edit_admission_report,
            "geometry_transaction": geometry_transaction_report,
            "active_path_record": active_path_record_report,
            "declared_path_length_readout": delta,
            "mechanism_status": {
                "scalar_update_rule_status": scalar_status,
                "association_remap_rule_status": remap_status,
                "soo_candidate_not_admitted_flag": candidate_flag,
                "all_mechanisms_non_candidate": mechanisms_non_candidate,
            },
            "initialization_settling": init_status,
            "control_separation": {
                "evaluated_in_case_report": False,
                "note": "control separation requires suite-level comparison across theorem and control cases",
            },
        },
        "primary_failure_reasons": [x for x in no_edit_reasons if x and x != "None"],
        "forbidden_interpretations": [
            "this trace is not an update rule",
            "this trace must not use same/opposite labels to set Delta L",
            "this trace reports missing causal links rather than filling them in",
        ],
    }


def build_all_path_failure_diagnostics(
    *,
    readouts: Sequence[Any],
    path_report: Any | None,
    optional_module_report: Any,
    soo_execution_report: Any,
    initialization_settling_report: Any,
    modeling_intent_contract: Any,
    scalar_update_metadata: Any,
    association_remap_metadata: Any,
) -> dict[str, dict[str, Any]]:
    effective = build_effective_orientation_record(readouts=readouts, path_report=path_report)
    monitor = build_path_monitor_decision_report(readouts=readouts, optional_module_report=optional_module_report)
    admission = build_path_edit_admission_report(monitor_report=monitor)
    transaction = build_geometry_transaction_report(readouts=readouts, path_edit_admission_report=admission)
    active = build_active_path_record_report(readouts=readouts, path_report=path_report)
    trace = build_theorem_failure_trace(
        readouts=readouts,
        path_report=path_report,
        optional_module_report=optional_module_report,
        soo_execution_report=soo_execution_report,
        initialization_settling_report=initialization_settling_report,
        modeling_intent_contract=modeling_intent_contract,
        scalar_update_metadata=scalar_update_metadata,
        association_remap_metadata=association_remap_metadata,
        effective_orientation_record=effective,
        path_monitor_decision_report=monitor,
        path_edit_admission_report=admission,
        geometry_transaction_report=transaction,
        active_path_record_report=active,
    )
    return {
        "EFFECTIVE_ORIENTATION_RECORD": effective,
        "PATH_MONITOR_DECISION_REPORT": monitor,
        "PATH_EDIT_ADMISSION_REPORT": admission,
        "GEOMETRY_TRANSACTION_REPORT": transaction,
        "ACTIVE_PATH_RECORD_REPORT": active,
        "THEOREM_FAILURE_TRACE": trace,
    }
