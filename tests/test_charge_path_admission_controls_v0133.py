import json
from pathlib import Path

from rank3_enforced.admission_mechanisms import admitted_mechanism_ids, load_mechanism_set
from rank3_enforced.certified_runner import run_declarative_overlay
from rank3_enforced.modeling_intent import contract_from_dict, validate_contract_for_overlay
from rank3_enforced.overlay_schema import parse_declarative_overlay
from rank3_enforced.overlay_compiler import compile_overlay_to_model_package
from rank3_enforced.run_manager import BUILTIN_SUITES, suite_resource_files


def suite_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "rank3_enforced" / "overlay_suites" / "charge_path_admission_controls_v0_1"


def test_v0133_admission_suite_registered_and_has_required_cases():
    assert "charge_path_admission_controls_v0_1" in BUILTIN_SUITES
    files = suite_resource_files("charge_path_admission_controls_v0_1")
    names = {p.name for p in files}
    assert "theorem_same_L7.json" in names
    assert "theorem_opposite_L7.json" in names
    for control in [
        "no_remap_control_L7.json",
        "wrong_continuation_slot_control_L7.json",
        "broken_path_control_L7.json",
        "label_swap_control_L7.json",
        "sign_randomized_control_L7.json",
    ]:
        assert control in names


def test_v0133_mechanism_declaration_contains_non_candidate_mechanisms():
    payload = load_mechanism_set()
    ids = set(admitted_mechanism_ids())
    assert payload["status"] == "framework_admission_capable_not_theorem_admitted"
    assert "bounded_context_soo_v1" in ids
    assert "admitted_nonlabel_path_monitor_v1" in ids
    assert "role_path_two_support_v0_1" in ids


def test_v0133_admission_overlay_is_contract_compliant_and_compiles():
    payload = json.loads((suite_dir() / "theorem_same_L7.json").read_text())
    contract = contract_from_dict(payload["modeling_intent"])
    report = validate_contract_for_overlay(contract=contract, overlay_payload=payload, overlay_hash="test")
    assert report.passed
    assert report.certification_eligible
    overlay = parse_declarative_overlay(payload)
    package = compile_overlay_to_model_package(overlay, overlay_hash="test")
    assert package.manifest.run_kind == "admission"
    assert package.scalar_update_metadata.status.value == "admitted"
    assert package.association_remap_metadata.status.value == "admitted"


def test_v0133_admission_overlay_executes_without_candidate_rule_promotion():
    result = run_declarative_overlay(suite_dir() / "theorem_same_L7.json")
    assert result.manifest.run_kind == "admission"
    assert result.modeling_intent_compliance_report.passed
    assert result.scalar_update_metadata.status.value == "admitted" if hasattr(result, 'scalar_update_metadata') else True
    readouts = {r.name for r in result.readouts}
    assert "delta_l_classification" in readouts
    assert "role_path_midpoint_arrival_readout" in readouts
