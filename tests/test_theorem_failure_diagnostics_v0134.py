import copy
import json
from pathlib import Path

import pytest

from rank3_enforced.certified_runner import run_declarative_overlay
from rank3_enforced.exceptions import ManifestError
from rank3_enforced.overlay_schema import parse_declarative_overlay
from rank3_enforced.overlay_compiler import compile_overlay_to_model_package


SUITE = Path(__file__).resolve().parents[1] / "rank3_enforced" / "overlay_suites" / "charge_path_admission_controls_v0_1"


def _payload(name="theorem_same_L7.json"):
    return json.loads((SUITE / name).read_text())


@pytest.mark.parametrize("bad_input", ["orientation", "same_label", "opposite_label", "target_delta_l"])
def test_v0134_nonlabel_monitor_rejects_all_forbidden_inputs(bad_input):
    payload = _payload()
    for module in payload["optional_modules"]:
        if module["module_id"] == "admitted_nonlabel_path_monitor_v1":
            module.setdefault("params", {})["decision_inputs"] = [bad_input]
    overlay = parse_declarative_overlay(payload)
    with pytest.raises(ManifestError, match="forbidden inputs"):
        compile_overlay_to_model_package(overlay, overlay_hash="test")


def test_v0134_theorem_failure_diagnostics_explain_no_path_edit_chain():
    result = run_declarative_overlay(SUITE / "theorem_opposite_L7.json")
    assert result.gate.passed is False
    assert result.gate.details["soo_execution_candidate_not_admitted"] is False
    assert result.gate.details["initialization_contract_gate_passed"] is False
    assert "INITIALIZATION_SETTLING_REPORT is absent" in result.gate.details["initialization_contract_blocking_reason"]

    effective = result.effective_orientation_record
    assert effective["status"] == "theorem_not_tested_effective_orientation_missing"
    assert effective["support_packet_comparison_ell0"]["support_B_packet_identical_to_support_A"] is True

    monitor = result.path_monitor_decision_report
    assert monitor["monitor_policy_declared"] is True
    assert monitor["monitor_ran"] is False
    assert monitor["edit_request_emitted"] is False
    assert monitor["forbidden_inputs_read"] == []
    assert monitor["center_condition_summary"]["zero_or_balanced_center_ells"] == [0, 1, 2]
    assert monitor["center_condition_summary"]["center_condition_transient"] is True

    transaction = result.geometry_transaction_report
    assert transaction["transaction_requested"] is False
    assert transaction["transaction_applied"] is False
    assert transaction["observed_declared_path_length_delta"] == 0

    active = result.active_path_record_report
    assert active["active_path_record_mutation_supported"] is False
    assert active["active_path_length_delta"] == 0

    trace = result.theorem_failure_trace
    assert trace["verdict"] == "theorem_not_certified"
    reasons = "\n".join(trace["primary_failure_reasons"])
    assert "no executable monitor transaction" in reasons
    assert "effective scalar-packet distinction" in reasons
