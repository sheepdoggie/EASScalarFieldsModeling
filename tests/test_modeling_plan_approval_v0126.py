from __future__ import annotations

import json
from pathlib import Path

import pytest

from rank3_enforced.modeling_intent import charge_path_adjustment_certification_template
from rank3_enforced.modeling_plan import (
    approve_modeling_plan,
    build_modeling_plan,
    load_modeling_plan,
    validate_modeling_plan,
    write_modeling_plan,
)
from rank3_enforced.run_manager import run_overlay_suite


def test_modeling_plan_requires_user_approval_for_certification(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RANK3_RELEASE_GUARD", "off")
    contract = charge_path_adjustment_certification_template()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="approved-plan"):
        run_overlay_suite(
            suite_id="charge_role_path_remap_dynamic_path_v0_1",
            output_root=tmp_path / "suite_no_plan",
            fail_fast=True,
            progress=False,
            case_ids=("L7_same_no_remap",),
            modeling_mode="certification",
            modeling_intent_contract_path=contract_path,
        )


def test_draft_approve_validate_plan_and_block_candidate_case(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RANK3_RELEASE_GUARD", "off")
    contract = charge_path_adjustment_certification_template()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    source_overlay = Path("rank3_enforced/overlay_suites/charge_role_path_remap_dynamic_path_v0_1/L7_same_no_remap.json")
    staged_dir = tmp_path / "planned_overlays"
    draft = build_modeling_plan(
        contract=contract,
        overlay_files=[source_overlay],
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
        output_overlays_dir=staged_dir,
        modeling_mode="certification",
    )
    draft_path = tmp_path / "draft_plan.json"
    write_modeling_plan(draft_path, draft)
    assert draft.plan_status == "draft_pending_user_approval"
    assert draft.blocked_case_count == 1
    approved_path = tmp_path / "approved_plan.json"
    approved = approve_modeling_plan(plan_path=draft_path, output_path=approved_path, approved_by="test-user")
    assert approved.plan_status == "approved_for_execution"
    validation = validate_modeling_plan(
        contract=contract,
        plan=approved,
        overlay_files=[source_overlay],
        require_approved=True,
    )
    assert validation.structurally_valid
    assert not validation.plan_certification_executable
    assert not validation.passed
    assert "zero certification-eligible cases" in "; ".join(validation.execution_blocking_violations)
    with pytest.raises(ValueError, match="executable approved modeling plan"):
        run_overlay_suite(
            suite_id="charge_role_path_remap_dynamic_path_v0_1",
            output_root=tmp_path / "suite",
            fail_fast=True,
            progress=False,
            case_ids=("L7_same_no_remap",),
            modeling_mode="certification",
            modeling_intent_contract_path=contract_path,
            approved_plan_path=approved_path,
        )
    report_path = tmp_path / "suite" / "MODELING_PLAN_VALIDATION_REPORT.json"
    assert report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["structurally_valid"] is True
    assert payload["plan_certification_executable"] is False
    assert payload["passed"] is False
    assert not (tmp_path / "suite" / "runs" / "L7_same_no_remap" / "CERTIFICATE.json").exists()


def test_plan_validation_rejects_stale_hash(tmp_path: Path) -> None:
    contract = charge_path_adjustment_certification_template()
    source_overlay = Path("rank3_enforced/overlay_suites/charge_role_path_remap_dynamic_path_v0_1/L7_same_no_remap.json")
    staged_dir = tmp_path / "planned_overlays"
    draft = build_modeling_plan(
        contract=contract,
        overlay_files=[source_overlay],
        output_overlays_dir=staged_dir,
        modeling_mode="certification",
    )
    draft_path = tmp_path / "draft_plan.json"
    write_modeling_plan(draft_path, draft)
    approved_path = tmp_path / "approved_plan.json"
    approved = approve_modeling_plan(plan_path=draft_path, output_path=approved_path)
    staged = staged_dir / source_overlay.name
    payload = json.loads(staged.read_text(encoding="utf-8"))
    payload["notes"] = str(payload.get("notes", "")) + "\nUnauthorized post-approval edit."
    staged.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = validate_modeling_plan(
        contract=contract,
        plan=load_modeling_plan(approved_path),
        overlay_files=[source_overlay],
        require_approved=True,
    )
    assert not validation.passed
    assert any("planned overlay file hash mismatch" in v for v in validation.violations)
