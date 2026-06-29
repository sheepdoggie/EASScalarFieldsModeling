import json
from pathlib import Path

from rank3_enforced.operator_agent_workflow import (
    APPROVAL_DECISION_SCHEMA,
    generate_customized_review_packet,
    validate_customized_review_packet,
)
from rank3_enforced.operator_review_packet import generate_operator_review_packet
from rank3_enforced.contract_overlay_synthesis import write_operator_required_items_report, OperatorRequiredItem
from rank3_enforced.modeling_intent import ModelingIntentContract, contract_from_file


def _contract(tmp_path: Path) -> Path:
    c = ModelingIntentContract(
        mode="certification",
        modeling_intent="charge_path_adjustment_theorem",
        claim={"same_orientation": "Delta L(P)=+1", "opposite_orientation": "Delta L(P)=-1"},
        required_mechanisms=("whole_field_soo", "dynamic_path_record"),
        forbidden_shortcuts=("label_triggered_path_edit",),
        admissible_inputs=("signed_scalar_records",),
        required_initialization=("steady_state_gate",),
        required_soo_properties=("signed_values_preserved",),
        required_monitors=("path_monitor_policy",),
        negative_controls=("orientation_label_shuffle",),
        leakage_checks=("no_candidate_promotion",),
        admission_verdict_rules=("same_plus_one_opposite_minus_one",),
        abort_conditions=("release_guard_failed",),
        allow_candidate_rules=False,
        allow_external_monitors=False,
        notes="test contract",
    )
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(c.to_dict(), indent=2, sort_keys=True) + "\n")
    return p


def test_customized_packet_requires_approval_loop(tmp_path):
    contract = _contract(tmp_path)
    req = tmp_path / "OPERATOR_REQUIRED_ITEMS.json"
    write_operator_required_items_report(
        path=req,
        context="test",
        contract=contract_from_file(contract),
        requested_mode="certification",
        items=(OperatorRequiredItem(
            item_id="admission_overlay_specification",
            severity="blocking",
            category="overlay_status",
            required_from_operator=True,
            prompt="Provide admission overlays.",
            reason="candidate overlays cannot certify",
        ),),
    )
    packet = tmp_path / "packet"
    generate_operator_review_packet(contract_path=contract, operator_required_items_path=req, output_dir=packet, suite_id="charge_role_path_remap_dynamic_path_v0_1")
    assert (packet / "CHAT_APPROVAL_LOOP_PROTOCOL.md").exists()
    assert (packet / "CHAT_TASKS.json").exists()
    assert (packet / "GENERATE_CUSTOMIZED_REVIEW_PACKET.sh").exists()
    customized = tmp_path / "customized"
    manifest = generate_customized_review_packet(review_packet_dir=packet, output_dir=customized, contract_path=contract)
    assert manifest.requires_explicit_user_approval_before_modeling is True
    assert manifest.executable_for_certification is False
    report = validate_customized_review_packet(packet_dir=customized)
    assert report.valid_for_user_review is True
    assert report.approved_for_modeling is False
    assert report.required_next_action == "return_customized_packet_to_user_and_wait_for_explicit_approval"
    assert (customized / "USER_APPROVAL_DECISION_TEMPLATE.json").exists()


def test_approval_decision_must_bind_packet_and_plan_hash(tmp_path):
    contract = _contract(tmp_path)
    packet = tmp_path / "packet"
    generate_operator_review_packet(contract_path=contract, output_dir=packet)
    customized = tmp_path / "customized"
    generate_customized_review_packet(review_packet_dir=packet, output_dir=customized)
    packet_hash = (customized / "CUSTOMIZED_REVIEW_PACKET.sha256").read_text().strip()
    bad = tmp_path / "bad_approval.json"
    bad.write_text(json.dumps({
        "schema": APPROVAL_DECISION_SCHEMA,
        "decision": "approve",
        "approved_packet_sha256": "wrong",
        "approved_plan_sha256": "planhash",
    }))
    bad_report = validate_customized_review_packet(packet_dir=customized, approval_decision_path=bad)
    assert bad_report.approved_for_modeling is False
    assert any("packet hash" in e for e in bad_report.errors)
    good = tmp_path / "good_approval.json"
    good.write_text(json.dumps({
        "schema": APPROVAL_DECISION_SCHEMA,
        "decision": "approve",
        "approved_packet_sha256": packet_hash,
        "approved_plan_sha256": "abc123",
    }))
    good_report = validate_customized_review_packet(packet_dir=customized, approval_decision_path=good)
    assert good_report.approved_for_modeling is True
    assert good_report.executable_for_certification is True
