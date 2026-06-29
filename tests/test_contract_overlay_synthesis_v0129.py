from __future__ import annotations

import json
from pathlib import Path

import pytest

from rank3_enforced.contract_overlay_synthesis import synthesize_overlays_from_contract
from rank3_enforced.modeling_intent import charge_path_adjustment_certification_template
from rank3_enforced.run_manager import overlay_files_from_source, run_overlay_suite


def test_contract_synthesis_refuses_candidate_promotion_and_requests_operator_items(tmp_path: Path) -> None:
    contract = charge_path_adjustment_certification_template()
    overlays = [p for p in overlay_files_from_source(suite_id="charge_role_path_remap_dynamic_path_v0_1") if p.stem == "L7_same_no_remap"]
    assert len(overlays) == 1
    out = tmp_path / "synth"
    report = synthesize_overlays_from_contract(
        contract=contract,
        overlay_files=overlays,
        output_overlays_dir=out,
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
    )
    assert report.source_overlay_count == 1
    assert report.synthesized_overlay_count == 0
    assert report.certification_eligible_case_count == 0
    assert report.can_build_certification_plan is False
    assert report.operator_action_required is True
    assert (out / "OVERLAY_SYNTHESIS_REPORT.json").is_file()
    req = json.loads((out / "OPERATOR_REQUIRED_ITEMS.json").read_text())
    prompts = "\n".join(item["prompt"] for item in req["items"])
    assert "run_kind='admission'" in prompts
    assert "will not turn candidate overlays into admission overlays automatically" in prompts


def test_contract_synthesis_can_stage_exploratory_without_operator_block(tmp_path: Path) -> None:
    from rank3_enforced.modeling_intent import default_exploratory_contract

    contract = default_exploratory_contract()
    overlays = [p for p in overlay_files_from_source(suite_id="charge_role_path_remap_dynamic_path_v0_1") if p.stem == "L7_same_no_remap"]
    out = tmp_path / "synth_exploratory"
    report = synthesize_overlays_from_contract(
        contract=contract,
        overlay_files=overlays,
        output_overlays_dir=out,
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
    )
    assert report.synthesized_overlay_count == 1
    staged = Path(report.cases[0].synthesized_overlay_path)
    payload = json.loads(staged.read_text())
    assert payload["modeling_intent"]["mode"] == "exploratory"


def test_certification_run_missing_approved_plan_writes_operator_required_items(tmp_path: Path) -> None:
    contract = charge_path_adjustment_certification_template()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract.to_dict(), indent=2, sort_keys=True) + "\n")
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
    req_path = out / "OPERATOR_REQUIRED_ITEMS.json"
    assert req_path.is_file()
    req = json.loads(req_path.read_text())
    ids = {item["item_id"] for item in req["items"]}
    assert "approved_modeling_plan_required" in ids
    assert req["blocks_certification_execution"] is True
