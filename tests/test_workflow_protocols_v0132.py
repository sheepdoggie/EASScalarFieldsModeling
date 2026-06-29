from pathlib import Path

from rank3_enforced.workflow_protocols import (
    DEFAULT_APPROVAL_LOOP_PROTOCOL_ID,
    compute_workflow_protocols_sha256,
    load_workflow_protocol,
    protocol_sequence_markdown,
    validate_workflow_protocol,
)
from rank3_enforced.operator_review_packet import generate_operator_review_packet
from rank3_enforced.operator_agent_workflow import generate_customized_review_packet, validate_customized_review_packet


def test_data_driven_approval_protocol_valid():
    report = validate_workflow_protocol(DEFAULT_APPROVAL_LOOP_PROTOCOL_ID)
    assert report.valid, report.errors
    assert "return_to_user_for_approval" in report.mandatory_sequence_ids
    assert "wait_for_explicit_decision" in report.mandatory_sequence_ids
    assert "run_before_explicit_approval" in report.forbidden_behaviors
    assert compute_workflow_protocols_sha256()


def test_protocol_markdown_contains_revision_loop_and_no_silent_approval():
    payload = load_workflow_protocol(DEFAULT_APPROVAL_LOOP_PROTOCOL_ID)
    md = protocol_sequence_markdown(payload)
    assert "wait_for_explicit_decision" in md
    assert "handle_revision_request" in md
    assert "treat_silence_as_approval" in md


def test_review_packet_embeds_protocol_metadata(tmp_path: Path):
    contract = tmp_path / "contract.json"
    contract.write_text(
        '{"schema":"rank3_modeling_intent_contract_v1","modeling_intent":"charge_path_adjustment_theorem","mode":"certification","claim":{"same_orientation":"Delta L = +1"},"required_mechanisms":["whole_field_soo"],"forbidden_shortcuts":["candidate_rule_certification"],"admissible_inputs":[],"required_initialization":["settled"],"required_soo_properties":[],"required_monitors":[],"negative_controls":["orientation_label_shuffle"],"leakage_checks":[],"admission_verdict_rules":[],"abort_conditions":["release_guard_failed"],"allow_candidate_rules":false,"allow_external_monitors":false}',
        encoding="utf-8",
    )
    out = tmp_path / "packet"
    manifest = generate_operator_review_packet(contract_path=contract, output_dir=out, suite_id="charge_role_path_remap_dynamic_path_v0_1")
    assert manifest.workflow_protocol_id == DEFAULT_APPROVAL_LOOP_PROTOCOL_ID
    assert manifest.workflow_protocol_sha256
    assert (out / "WORKFLOW_PROTOCOL.json").exists()
    assert (out / "WORKFLOW_PROTOCOL_VALIDATION_REPORT.json").exists()
    assert "Workflow protocol SHA-256" in (out / "CHAT_MODELING_INSTRUCTIONS.md").read_text(encoding="utf-8")

    custom_dir = tmp_path / "customized"
    cmanifest = generate_customized_review_packet(review_packet_dir=out, output_dir=custom_dir)
    assert cmanifest.workflow_protocol_id == DEFAULT_APPROVAL_LOOP_PROTOCOL_ID
    report = validate_customized_review_packet(packet_dir=custom_dir)
    assert report.valid_for_user_review
    assert not report.approved_for_modeling
    assert report.required_next_action == "return_customized_packet_to_user_and_wait_for_explicit_approval"
