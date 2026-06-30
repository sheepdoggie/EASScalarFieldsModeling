import json
import zipfile
from pathlib import Path

from rank3_enforced.capabilities import FRAMEWORK_CAPABILITIES, FRAMEWORK_RELEASE_LABEL, FRAMEWORK_VERSION
from rank3_enforced.split_vacuum_triangle_emergence import (
    ALLOWED_GENERATOR_INPUTS,
    FORBIDDEN_GENERATOR_INPUTS,
    REQUIRED_ARTIFACTS,
    approval_packet_payloads,
    leakage_manipulation_audit,
    run_exploratory,
    validate_generator_inputs,
    write_approval_packet,
)


def test_v0136_version_and_capabilities():
    assert FRAMEWORK_VERSION == "0.1.36"
    assert FRAMEWORK_RELEASE_LABEL == "0.1.36-split-vacuum-triangle-emergence-exploratory"
    assert "split_vacuum_triangle_emergence_exploratory_v0_1" in FRAMEWORK_CAPABILITIES
    assert "triangle_membership_readout_not_input_v0_1" in FRAMEWORK_CAPABILITIES
    assert "path_endpoints_detected_not_preselected_v0_1" in FRAMEWORK_CAPABILITIES
    assert "exploratory_only_no_theorem_certification_v0_1" in FRAMEWORK_CAPABILITIES


def test_v0136_forbidden_inputs_rejected():
    for forbidden in FORBIDDEN_GENERATOR_INPUTS:
        report = validate_generator_inputs([forbidden])
        assert not report["passed"]
        assert forbidden in report["forbidden_inputs_present"]
    assert validate_generator_inputs(ALLOWED_GENERATOR_INPUTS)["passed"]


def test_v0136_runner_emits_required_artifacts_and_is_non_certifying():
    reports = run_exploratory(split_site_count=2, cycles=4)
    assert set(REQUIRED_ARTIFACTS).issubset(set(reports))
    verdict = reports["EXPLORATORY_VERDICT_REPORT.json"]
    assert verdict["verdict"] == "EXPLORATORY_ONLY_DO_NOT_CERTIFY"
    assert verdict["theorem_certified"] is False
    assert verdict["charge_certified"] is False
    assert reports["LEAKAGE_MANIPULATION_AUDIT.json"]["passed"] is True
    assert reports["TRIANGLE_FORMATION_REPORT.json"]["triangles"]
    assert all(not t["predeclared_membership"] for t in reports["TRIANGLE_FORMATION_REPORT.json"]["triangles"])
    paths = reports["RELATIONAL_PATH_DISCOVERY_REPORT.json"]["paths"]
    assert paths
    assert all(not p["predeclared_path_endpoints"] for p in paths)


def test_v0136_all_vacuum_no_split_allowed_null_outcome():
    reports = run_exploratory(split_site_count=0, cycles=3)
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["triangle_count"] == 0
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["discovered_path_count"] == 0
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["theorem_certified"] is False


def test_v0136_approval_packet_contains_spec_and_controls(tmp_path: Path):
    output = tmp_path / "packet.zip"
    write_approval_packet(output)
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        assert "EXPLORATORY_RUNNER_SPEC.json" in names
        assert "ADMISSIBLE_INITIAL_CONDITIONS.json" in names
        assert "SOO_AND_ASSOCIATION_RULES.json" in names
        assert "NEGATIVE_CONTROLS_MANIFEST.json" in names
        assert "LEAKAGE_MANIPULATION_AUDIT.json" in names
        spec = json.loads(zf.read("EXPLORATORY_RUNNER_SPEC.json"))
        assert spec["theorem_certification_ready"] is False
        assert spec["rules"]["triangle_membership"] == "readout_not_generator_input"


def test_v0136_packaged_payloads_non_imposing():
    payloads = approval_packet_payloads()
    audit = json.loads(payloads["LEAKAGE_MANIPULATION_AUDIT.json"])
    assert audit["passed"] is True
    text = payloads["EXPLORATORY_RUNNER_SPEC.json"]
    assert "predeclared_triangle_membership" in text
    assert "target_delta_l" in text
    assert "EXPLORATORY" in payloads["APPROVAL_INSTRUCTIONS.md"]
