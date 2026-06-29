from __future__ import annotations

import json
from pathlib import Path

import pytest

from rank3_enforced.modeling_intent import charge_path_adjustment_certification_template
from rank3_enforced.modeling_plan import (
    approve_modeling_plan,
    build_modeling_plan,
    validate_modeling_plan,
    write_modeling_plan,
)
from rank3_enforced.run_manager import run_overlay_suite


def test_zero_eligible_certification_plan_is_structural_but_not_executable(tmp_path: Path) -> None:
    contract = charge_path_adjustment_certification_template()
    source_overlay = Path("rank3_enforced/overlay_suites/charge_role_path_remap_dynamic_path_v0_1/L7_same_no_remap.json")
    draft = build_modeling_plan(
        contract=contract,
        overlay_files=[source_overlay],
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
        output_overlays_dir=tmp_path / "planned_overlays",
        modeling_mode="certification",
    )
    assert draft.plan_certification_executable is False
    assert "zero certification-eligible cases" in "; ".join(draft.execution_blocking_reasons)
    draft_path = tmp_path / "draft.json"
    approved_path = tmp_path / "approved.json"
    write_modeling_plan(draft_path, draft)
    approved = approve_modeling_plan(plan_path=draft_path, output_path=approved_path, approved_by="tester")
    report = validate_modeling_plan(
        contract=contract,
        plan=approved,
        overlay_files=[source_overlay],
        require_approved=True,
    )
    assert report.structurally_valid is True
    assert report.plan_certification_executable is False
    assert report.passed is False
    assert "certification plan has zero certification-eligible cases" in report.execution_blocking_violations


def test_certification_run_blocks_before_release_guard_when_plan_not_executable(tmp_path: Path, monkeypatch) -> None:
    # Use required guard mode to prove the plan gate fires before release-guard/network behavior.
    monkeypatch.setenv("RANK3_RELEASE_GUARD", "required")
    contract = charge_path_adjustment_certification_template()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source_overlay = Path("rank3_enforced/overlay_suites/charge_role_path_remap_dynamic_path_v0_1/L7_same_no_remap.json")
    draft = build_modeling_plan(
        contract=contract,
        overlay_files=[source_overlay],
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
        output_overlays_dir=tmp_path / "planned_overlays",
        modeling_mode="certification",
    )
    draft_path = tmp_path / "draft.json"
    approved_path = tmp_path / "approved.json"
    write_modeling_plan(draft_path, draft)
    approve_modeling_plan(plan_path=draft_path, output_path=approved_path, approved_by="tester")
    with pytest.raises(ValueError, match="zero certification-eligible cases"):
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
    validation = json.loads((tmp_path / "suite" / "MODELING_PLAN_VALIDATION_REPORT.json").read_text(encoding="utf-8"))
    assert validation["structurally_valid"] is True
    assert validation["plan_certification_executable"] is False
    assert validation["passed"] is False
    assert not (tmp_path / "suite" / "release_guard.json").exists()
