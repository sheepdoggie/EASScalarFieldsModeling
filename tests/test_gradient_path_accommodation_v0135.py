import json
import zipfile
from pathlib import Path

from rank3_enforced.capabilities import FRAMEWORK_CAPABILITIES, FRAMEWORK_VERSION, FRAMEWORK_RELEASE_LABEL
from rank3_enforced.gradient_path_accommodation import (
    ALLOWED_GENERATOR_INPUTS,
    FORBIDDEN_GENERATOR_INPUTS,
    FROZEN_ADMISSIBILITIES,
    THEOREM_FACING_HYPOTHESES,
    anti_imposition_audit,
    approval_packet_payloads,
    validate_generator_inputs,
    write_approval_packet,
)


def test_v0135_version_and_capabilities():
    assert FRAMEWORK_VERSION == "0.1.41"
    assert FRAMEWORK_RELEASE_LABEL == "0.1.41-endpoint-class-loaded-photon-field-processing"
    assert "gradient_governed_vacuum_split_plan_v0_1" in FRAMEWORK_CAPABILITIES
    assert "theorem_hypotheses_not_primitive_rules_v0_1" in FRAMEWORK_CAPABILITIES
    assert "forced_delta_l_leakage_control_v0_1" in FRAMEWORK_CAPABILITIES
    assert "ready_for_certification_plan_not_theorem_certification_v0_1" in FRAMEWORK_CAPABILITIES


def test_v0135_admissibilities_stop_before_theorem_result():
    assert [x.id for x in FROZEN_ADMISSIBILITIES] == ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
    primitive_text = "\n".join(x.statement for x in FROZEN_ADMISSIBILITIES).lower()
    assert "delta l" not in primitive_text
    assert "same sign" not in primitive_text
    assert "opposite sign" not in primitive_text
    assert all(x.id.startswith("H") for x in THEOREM_FACING_HYPOTHESES)
    assert all(x.status == "proof_obligation_not_admissibility" for x in THEOREM_FACING_HYPOTHESES)
    assert all(x.blocked_if_primitive for x in THEOREM_FACING_HYPOTHESES)


def test_v0135_forbidden_generator_inputs_blocked():
    for forbidden in FORBIDDEN_GENERATOR_INPUTS:
        report = validate_generator_inputs([forbidden])
        assert not report["passed"]
        assert forbidden in report["forbidden_inputs_present"]
    assert validate_generator_inputs(ALLOWED_GENERATOR_INPUTS)["passed"]


def test_v0135_approval_packet_contains_required_files(tmp_path: Path):
    output = tmp_path / "approval.zip"
    write_approval_packet(output)
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        assert "THEOREM_STATEMENT.json" in names
        assert "ADMISSIBILITY_MANIFEST.json" in names
        assert "HYPOTHESIS_MANIFEST.json" in names
        assert "GENERATOR_READOUT_SEPARATION_CONTRACT.json" in names
        assert "NEGATIVE_CONTROLS_MANIFEST.json" in names
        assert "AUDIT_GATES_MANIFEST.json" in names
        assert "ANTI_IMPOSITION_AUDIT.json" in names
        audit = json.loads(zf.read("ANTI_IMPOSITION_AUDIT.json"))
        assert audit["passed"] is True
        theorem = json.loads(zf.read("THEOREM_STATEMENT.json"))
        assert theorem["ready_for_certification_plan"] is True
        assert theorem["ready_for_theorem_certification"] is False


def test_v0135_packaged_payloads_are_non_imposing():
    payloads = approval_packet_payloads()
    audit = json.loads(payloads["ANTI_IMPOSITION_AUDIT.json"])
    assert audit["passed"] is True
    admissibility_manifest = json.loads(payloads["ADMISSIBILITY_MANIFEST.json"])
    assert len(admissibility_manifest["admissibilities"]) == 7
    hypothesis_manifest = json.loads(payloads["HYPOTHESIS_MANIFEST.json"])
    assert len(hypothesis_manifest["hypotheses"]) == 5
