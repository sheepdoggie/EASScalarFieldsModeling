import json
import zipfile
from pathlib import Path

from rank3_enforced.capabilities import FRAMEWORK_CAPABILITIES, FRAMEWORK_RELEASE_LABEL, FRAMEWORK_VERSION
from rank3_enforced.endpoint_class_path_response_separation import (
    ALLOWED_GENERATOR_INPUTS,
    FORBIDDEN_GENERATOR_INPUTS,
    REQUIRED_ARTIFACTS,
    approval_packet_payloads,
    leakage_manipulation_audit,
    run_exploratory,
    validate_generator_inputs,
    write_approval_packet,
)


def test_v0138_version_and_capabilities():
    assert FRAMEWORK_VERSION == "0.1.39"
    assert FRAMEWORK_RELEASE_LABEL == "0.1.39-endpoint-class-center-classifier-repair"
    assert "endpoint_class_path_response_separation_runner_v0_2" in FRAMEWORK_CAPABILITIES
    assert "photon_like_local_certifier_report_v0_1" in FRAMEWORK_CAPABILITIES
    assert "endpoint_class_not_delta_l_selector_v0_1" in FRAMEWORK_CAPABILITIES
    assert "path_profile_based_center_classification_v0_1" in FRAMEWORK_CAPABILITIES


def test_v0138_forbidden_inputs_rejected_and_allowed_inputs_pass():
    for forbidden in FORBIDDEN_GENERATOR_INPUTS:
        report = validate_generator_inputs([forbidden])
        assert not report["passed"]
        assert forbidden in report["forbidden_inputs_present"]
    assert validate_generator_inputs(ALLOWED_GENERATOR_INPUTS)["passed"]


def test_v0138_runner_emits_required_artifacts_and_is_non_certifying():
    reports = run_exploratory(path_length=7)
    assert set(REQUIRED_ARTIFACTS).issubset(set(reports))
    verdict = reports["EXPLORATORY_VERDICT_REPORT.json"]
    assert verdict["verdict"] == "EXPLORATORY_ONLY_DO_NOT_CERTIFY"
    assert verdict["theorem_certified"] is False
    assert verdict["charge_certified"] is False
    assert reports["LEAKAGE_MANIPULATION_AUDIT.json"]["passed"] is True
    assert reports["ENDPOINT_CLASS_COMPARISON_REPORT.json"]["comparisons"]


def test_v0138_center_conditions_are_profile_based_not_class_based():
    reports = run_exploratory(path_length=7)
    for center in reports["CENTER_CONDITION_REPORT.json"]["centers"]:
        assert center["classification_source"] == "generated_path_scalar_profile"
        assert center["endpoint_class_used_for_classification"] is False
        assert center["endpoint_sign_relation_used_for_classification"] is False
    for rec in reports["PATH_ACCOMMODATION_REPORT.json"]["records"]:
        assert rec["endpoint_class_used_for_transaction"] is False
        assert rec["forbidden_target_delta_l_used"] is False
        assert rec["readout_after_transaction_audit"] is True


def test_v0138_photon_like_records_are_locally_certified_but_not_selector():
    reports = run_exploratory(path_length=7)
    photons = reports["PHOTON_LIKE_CERTIFIER_REPORT.json"]["endpoints"]
    assert photons
    assert all(p["local_certifier_passed"] for p in photons)
    comparisons = reports["ENDPOINT_CLASS_COMPARISON_REPORT.json"]["comparisons"]
    photon_pairs = [c for c in comparisons if all(cls == "certified_photon_like_local_record" for cls in c["endpoint_classes"])]
    assert photon_pairs
    assert all(c["center_state"] == "null_path_facing_scalar_profile_no_center_invalidity" for c in photon_pairs)
    assert all(c["delta_l"] == 0 for c in photon_pairs)
    assert all(c["endpoint_class_used_as_selector"] is False for c in comparisons)


def test_v0138_endpoint_classes_are_compared_without_certification_claim():
    reports = run_exploratory(path_length=7)
    comparisons = reports["ENDPOINT_CLASS_COMPARISON_REPORT.json"]["comparisons"]
    ids = {c["comparison_id"] for c in comparisons}
    assert "triangle_triangle_opposite" in ids
    assert "photon_photon_conjugate" in ids
    assert "bounded_bounded_opposite" in ids
    assert "triangle_photon_mixed" in ids
    assert reports["EXPLORATORY_VERDICT_REPORT.json"]["photon_certified_beyond_local_certifier"] is False


def test_v0138_negative_controls_emit_per_control_artifacts():
    reports = run_exploratory(path_length=7)
    artifacts = [name for name in reports if name.startswith("NEGATIVE_CONTROL_") and name != "NEGATIVE_CONTROL_REPORT.json"]
    assert len(artifacts) >= 10
    assert reports["NEGATIVE_CONTROL_REPORT.json"]["per_control_artifacts_emitted"] is True
    assert reports["NEGATIVE_CONTROL_REPORT.json"]["executed_controls_passed"] is True


def test_v0138_approval_packet_contains_required_materials(tmp_path: Path):
    output = tmp_path / "packet.zip"
    write_approval_packet(output)
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        assert "EXPLORATORY_RUNNER_SPEC.json" in names
        assert "ENDPOINT_CLASS_MANIFEST.json" in names
        assert "PATH_RESPONSE_SEPARATION_RULES.json" in names
        assert "NEGATIVE_CONTROLS_MANIFEST.json" in names
        assert "LEAKAGE_MANIPULATION_AUDIT.json" in names
        spec = json.loads(zf.read("EXPLORATORY_RUNNER_SPEC.json"))
        assert spec["theorem_certification_ready"] is False
        assert "Center condition" in spec["critical_rule"]


def test_v0138_packaged_payloads_non_imposing():
    payloads = approval_packet_payloads()
    audit = json.loads(payloads["LEAKAGE_MANIPULATION_AUDIT.json"])
    assert audit["passed"] is True
    assert audit["checks"]["endpoint_class_not_delta_l_selector"] if "endpoint_class_not_delta_l_selector" in audit["checks"] else True
    assert "target_delta_l" in payloads["EXPLORATORY_RUNNER_SPEC.json"]
    assert "EXPLORATORY" in payloads["APPROVAL_INSTRUCTIONS.md"]


def test_v0139_bounded_calibration_exercises_insert_and_remove_branches():
    reports = run_exploratory(path_length=7)
    cal = reports["PATH_RESPONSE_CALIBRATION_REPORT.json"]
    assert cal["passed"] is True
    checks = {c["comparison_id"]: c for c in cal["checks"]}
    assert checks["bounded_bounded_same"]["observed_delta_l"] == 1
    assert checks["bounded_bounded_opposite"]["observed_delta_l"] == -1
    assert all(c["expectation_available_to_generator"] is False for c in checks.values())


def test_v0139_opposite_removal_branch_reachable_from_profile_not_endpoint_label():
    reports = run_exploratory(path_length=7)
    comparisons = {c["comparison_id"]: c for c in reports["ENDPOINT_CLASS_COMPARISON_REPORT.json"]["comparisons"]}
    bounded_opp = comparisons["bounded_bounded_opposite"]
    assert bounded_opp["delta_l"] == -1
    assert bounded_opp["center_state"] == "even_center_branch_transition_no_gradient_from_profile"
    assert bounded_opp["endpoint_class_used_as_selector"] is False
    centers = {c["path_id"]: c for c in reports["CENTER_CONDITION_REPORT.json"]["centers"]}
    center = centers[bounded_opp["path_id"]]
    assert center["endpoint_sign_relation_used_for_classification"] is False
    assert center["classification_source"] == "generated_path_scalar_profile"


def test_v0139_photon_records_are_not_transaction_suppressed_by_class():
    reports = run_exploratory(path_length=7)
    comparisons = reports["ENDPOINT_CLASS_COMPARISON_REPORT.json"]["comparisons"]
    photon_pairs = [c for c in comparisons if all(cls == "certified_photon_like_local_record" for cls in c["endpoint_classes"])]
    assert photon_pairs
    for row in photon_pairs:
        assert row["endpoint_class_used_as_selector"] is False
        assert row["center_state"] == "null_path_facing_scalar_profile_no_center_invalidity"
        assert row["delta_l"] == 0
    audit = reports["LEAKAGE_MANIPULATION_AUDIT.json"]
    assert audit["checks"]["photon_like_class_not_transaction_suppression_selector"] is True
