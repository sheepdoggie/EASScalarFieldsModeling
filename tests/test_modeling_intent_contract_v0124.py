from pathlib import Path
import json

import pytest

from rank3_enforced.modeling_intent import (
    charge_path_adjustment_certification_template,
    contract_from_dict,
    validate_contract_for_overlay,
)
from rank3_enforced.overlay_loader import load_declarative_overlay
from rank3_enforced.overlay_compiler import compile_overlay_to_model_package
from rank3_enforced.certificates import write_enforced_run_package
from rank3_enforced.certified_runner import run_declarative_overlay


def test_absent_contract_defaults_to_exploratory() -> None:
    overlay, overlay_hash = load_declarative_overlay("overlays/minimal_control_overlay.json")
    package = compile_overlay_to_model_package(overlay, overlay_hash=overlay_hash)
    assert package.modeling_intent_contract is not None
    assert package.modeling_intent_contract.mode == "exploratory"
    assert package.modeling_intent_compliance_report is not None
    assert package.modeling_intent_compliance_report.exploratory_default is True
    assert package.modeling_intent_compliance_report.certification_eligible is False


def test_certification_contract_rejects_non_admission_overlay() -> None:
    payload = json.loads(Path("overlays/minimal_control_overlay.json").read_text())
    contract = charge_path_adjustment_certification_template()
    report = validate_contract_for_overlay(contract=contract, overlay_payload=payload, overlay_hash="test")
    assert not report.passed
    assert any("run_kind='admission'" in v for v in report.violations)


def test_exploratory_overlay_emits_contract_and_compliance_artifacts(tmp_path: Path) -> None:
    result = run_declarative_overlay("overlays/minimal_control_overlay.json")
    assert result.modeling_intent_contract is not None
    assert result.modeling_intent_compliance_report is not None
    write_enforced_run_package(result=result, output_dir=tmp_path, overlay_path="overlays/minimal_control_overlay.json")
    assert (tmp_path / "MODELING_INTENT_CONTRACT.json").is_file()
    assert (tmp_path / "MODELING_INTENT_COMPLIANCE_REPORT.json").is_file()


def test_contract_parser_records_forbidden_shortcuts() -> None:
    contract = contract_from_dict({
        "modeling_intent": "charge_path_adjustment_theorem",
        "mode": "certification",
        "claim": {"same_orientation": "Delta L = +1"},
        "forbidden_shortcuts": ["orientation_label_triggers_path_edit"],
    })
    assert contract.mode == "certification"
    assert "orientation_label_triggers_path_edit" in contract.forbidden_shortcuts
