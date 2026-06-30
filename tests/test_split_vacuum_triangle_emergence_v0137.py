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


def test_v0137_version_and_capabilities():
    assert FRAMEWORK_VERSION == "0.1.44"
    assert FRAMEWORK_RELEASE_LABEL == "0.1.44-field0-locked-admissibility-simulation"
    assert "split_vacuum_triangle_emergence_exploratory_v0_1" in FRAMEWORK_CAPABILITIES
    assert "split_vacuum_triangle_emergence_runner_repair_v0_2" in FRAMEWORK_CAPABILITIES
    assert "dynamic_lifted_vacuum_splitting_v0_2" in FRAMEWORK_CAPABILITIES
    assert "pure_least_gradient_no_same_sign_priority_v0_2" in FRAMEWORK_CAPABILITIES
    assert "path_center_profile_classifier_v0_2" in FRAMEWORK_CAPABILITIES
    assert "exploratory_only_no_theorem_certification_v0_1" in FRAMEWORK_CAPABILITIES


def test_v0137_forbidden_inputs_rejected():
    for forbidden in FORBIDDEN_GENERATOR_INPUTS:
        report = validate_generator_inputs([forbidden])
        assert not report["passed"]
        assert forbidden in report["forbidden_inputs_present"]
    assert validate_generator_inputs(ALLOWED_GENERATOR_INPUTS)["passed"]


def test_v0137_runner_emits_required_artifacts_and_is_non_certifying():
    reports = run_exploratory(split_site_count=2, cycles=4)
    assert set(REQUIRED_ARTIFACTS).issubset(set(reports))
    verdict = reports["EXPLORATORY_VERDICT_REPORT.json"]
    assert verdict["verdict"] == "EXPLORATORY_ONLY_DO_NOT_CERTIFY"
    assert verdict["theorem_certified"] is False
    assert verdict["charge_certified"] is False
    assert reports["LEAKAGE_MANIPULATION_AUDIT.json"]["passed"] is True
    assert reports["DYNAMIC_SPLIT_BRANCH_LEDGER.json"]["events"]
    assert reports["TRIANGLE_FORMATION_REPORT.json"]["triangles"]
    assert all(not t["predeclared_membership"] for t in reports["TRIANGLE_FORMATION_REPORT.json"]["triangles"])
    # Path discovery is now graph-derived, so no-path is an allowed null exploratory outcome.
    assert "paths" in reports["RELATIONAL_PATH_DISCOVERY_REPORT.json"]
    assert all(not p["predeclared_path_endpoints"] for p in reports["RELATIONAL_PATH_DISCOVERY_REPORT.json"]["paths"])


def test_v0137_pure_least_gradient_has_no_sign_priority_or_branch_local_pool():
    reports = run_exploratory(split_site_count=2, cycles=4)
    events = reports["LEAST_GRADIENT_ASSOCIATION_REPORT.json"]["events"]
    assert events
    assert all(e["same_sign_priority_used"] is False for e in events)
    assert all(e["branch_local_pool_used"] is False for e in events)
    assert all(e["candidate_pool_scope"] == "global_generated_nonzero_points" for e in events)
    assert all(e["sort_key"] == ["burden", "members"] for e in events)


def test_v0137_center_condition_is_profile_based_when_paths_exist():
    reports = run_exploratory(split_site_count=2, cycles=5)
    centers = reports["CENTER_CONDITION_REPORT.json"]["centers"]
    for center in centers:
        assert center["classification_source"] == "generated_path_center_scalar_profile"
        assert center["endpoint_sign_relation_used_for_classification"] is False


def test_v0137_negative_controls_emit_per_control_artifacts():
    reports = run_exploratory(split_site_count=2, cycles=4)
    artifacts = [name for name in reports if name.startswith("NEGATIVE_CONTROL_") and name != "NEGATIVE_CONTROL_REPORT.json"]
    assert len(artifacts) >= 10
    assert reports["NEGATIVE_CONTROL_REPORT.json"]["per_control_artifacts_emitted"] is True
    assert reports["NEGATIVE_CONTROL_REPORT.json"]["executed_controls_passed"] is True


def test_v0137_all_vacuum_no_split_allowed_null_outcome():
    reports = run_exploratory(split_site_count=0, cycles=3)
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["triangle_count"] == 0
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["discovered_path_count"] == 0
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["theorem_certified"] is False


def test_v0137_approval_packet_contains_spec_and_controls(tmp_path: Path):
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
        assert "pure_least_scalar_gradient_burden_no_sign_priority" in spec["rules"]["association_selection"]


def test_v0137_packaged_payloads_non_imposing():
    payloads = approval_packet_payloads()
    audit = json.loads(payloads["LEAKAGE_MANIPULATION_AUDIT.json"])
    assert audit["passed"] is True
    assert audit["checks"]["same_sign_priority_not_used"] is True
    assert audit["checks"]["center_condition_not_endpoint_sign_dispatched"] is True
    text = payloads["EXPLORATORY_RUNNER_SPEC.json"]
    assert "predeclared_triangle_membership" in text
    assert "target_delta_l" in text
    assert "EXPLORATORY" in payloads["APPROVAL_INSTRUCTIONS.md"]
