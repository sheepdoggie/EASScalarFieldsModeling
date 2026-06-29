from __future__ import annotations

import json
from pathlib import Path

import pytest

from rank3_enforced.modeling_intent import charge_path_adjustment_certification_template
from rank3_enforced.operator_review_packet import generate_operator_review_packet
from rank3_enforced.run_manager import run_overlay_suite


def _write_contract(tmp_path: Path) -> Path:
    contract = charge_path_adjustment_certification_template()
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract.to_dict(), indent=2, sort_keys=True) + "\n")
    return path


def test_generate_operator_review_packet_writes_customizable_templates(tmp_path: Path) -> None:
    contract_path = _write_contract(tmp_path)
    req_path = tmp_path / "OPERATOR_REQUIRED_ITEMS.json"
    req_path.write_text(json.dumps({
        "schema": "rank3_operator_required_items_report_v2",
        "items": [{
            "item_id": "admission_overlay_specification",
            "category": "overlay_status",
            "severity": "blocking",
            "prompt": "Provide admission overlays.",
            "reason": "Candidate overlays cannot certify.",
        }],
    }, indent=2) + "\n")
    out = tmp_path / "packet"
    manifest = generate_operator_review_packet(
        contract_path=contract_path,
        operator_required_items_path=req_path,
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
        output_dir=out,
    )
    assert manifest.requires_user_approval_before_modeling is True
    required = {
        "CHAT_MODELING_INSTRUCTIONS.md",
        "ADMISSION_OVERLAY_TEMPLATE.json",
        "MECHANISM_STATUS_DECLARATION_TEMPLATE.json",
        "INITIALIZATION_SETTLING_REQUIREMENTS_TEMPLATE.json",
        "NEGATIVE_CONTROL_SUITE_TEMPLATE/negative_control_overlay_template.json",
        "PATH_MONITOR_POLICY_TEMPLATE.json",
        "MODELING_PLAN_APPROVAL_REQUEST_TEMPLATE.json",
        "RELEASE_SIGNING_CHECKLIST.md",
        "USER_APPROVAL_CHECKLIST.md",
        "OPERATOR_REVIEW_PACKET_MANIFEST.json",
        "OPERATOR_REVIEW_PACKET_MANIFEST.sha256",
    }
    for rel in required:
        assert (out / rel).is_file(), rel
    overlay_template = json.loads((out / "ADMISSION_OVERLAY_TEMPLATE.json").read_text())
    assert overlay_template["run_kind"] == "admission"
    assert overlay_template["requested_certification"] is True
    assert overlay_template["path_edit_policy"]["intrinsic_path_length_rule_allowed"] is False
    instructions = (out / "CHAT_MODELING_INSTRUCTIONS.md").read_text()
    assert "Do not run SOO/model execution yet" in instructions
    assert "Do not promote candidate overlays" in instructions


def test_certification_preflight_points_to_operator_review_packet_generator(tmp_path: Path) -> None:
    contract_path = _write_contract(tmp_path)
    out = tmp_path / "run"
    with pytest.raises(ValueError, match="requires --approved-plan"):
        run_overlay_suite(
            suite_id="charge_role_path_remap_dynamic_path_v0_1",
            output_root=out,
            modeling_mode="certification",
            modeling_intent_contract_path=contract_path,
            case_ids=("L7_same_no_remap",),
            progress=False,
        )
    req = json.loads((out / "OPERATOR_REQUIRED_ITEMS.json").read_text())
    assert req["schema"] == "rank3_operator_required_items_report_v2"
    assert req["recommended_generator_command"].startswith("rank3-generate-operator-review-packet")
    assert "OPERATOR_REVIEW_PACKET" in req["recommended_generator_command"]
    assert "CHAT_MODELING_INSTRUCTIONS.md" in req["recommended_generator_outputs"]
    assert all(item.get("generator") == "rank3-generate-operator-review-packet" for item in req["items"])
    script = out / "GENERATE_OPERATOR_REVIEW_PACKET.sh"
    assert script.is_file()
    assert "rank3-generate-operator-review-packet" in script.read_text()
