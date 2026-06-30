import zipfile

from rank3_enforced.capabilities import FRAMEWORK_CAPABILITIES, FRAMEWORK_RELEASE_LABEL, FRAMEWORK_VERSION
from rank3_enforced.whole_field_conjugate_vacuum import (
    FORBIDDEN_GENERATOR_INPUTS,
    REQUIRED_ARTIFACTS,
    VARIANTS,
    approval_packet_payloads,
    run_exploratory,
    validate_generator_inputs,
    write_approval_packet,
)


def test_v0143_version_and_capabilities():
    assert FRAMEWORK_VERSION == "0.1.43"
    assert FRAMEWORK_RELEASE_LABEL == "0.1.43-whole-field-conjugate-vacuum-derived-longitudinal"
    assert "whole_field_conjugate_vacuum_derived_longitudinal_runner_v0_1" in FRAMEWORK_CAPABILITIES
    assert "vacuum_first_association_conjugate_split_v0_1" in FRAMEWORK_CAPABILITIES
    assert "derived_longitudinal_residual_lambda_v0_1" in FRAMEWORK_CAPABILITIES
    assert "postrun_transverse_record_candidate_audit_v0_1" in FRAMEWORK_CAPABILITIES
    assert "path_accommodation_from_derived_lambda_v0_1" in FRAMEWORK_CAPABILITIES
    assert "stored_path_facing_zero_value_forbidden_v0_1" in FRAMEWORK_CAPABILITIES


def test_v0143_forbids_stored_zero_and_constructed_photon_inputs():
    for forbidden in FORBIDDEN_GENERATOR_INPUTS:
        report = validate_generator_inputs([forbidden])
        assert not report["passed"]
        assert forbidden in report["forbidden_inputs_present"]
    assert validate_generator_inputs(["whole_field_shape", "vacuum_first_association_conjugate_split_rule"]) ["passed"]


def test_v0143_runner_emits_required_artifacts_and_is_exploratory_only():
    reports = run_exploratory(width=3, height=3, cycles=4)
    assert set(REQUIRED_ARTIFACTS).issubset(reports)
    verdict = reports["EXPLORATORY_VERDICT_REPORT.json"]
    assert verdict["verdict"] == "EXPLORATORY_ONLY_DO_NOT_CERTIFY"
    assert verdict["photon_certified"] is False
    assert verdict["charge_certified"] is False
    assert verdict["theorem_certified"] is False
    assert reports["LEAKAGE_MANIPULATION_AUDIT.json"]["passed"] is True


def test_v0143_first_association_split_and_conjugate_link_are_ledged():
    reports = run_exploratory(width=3, height=3, cycles=4)
    ledger = reports["VACUUM_FIRST_ASSOCIATION_CONJUGATE_SPLIT_LEDGER.json"]
    assert ledger["not_memory_variable"] is True
    assert ledger["not_photon_template"] is True
    records = [r for r in ledger["records"] if r.get("event_type") == "vacuum_first_association_split_into_two_conjugate_points"]
    assert records
    linked = [r for r in records if r["one_association_of_each_branch_to_conjugate"]]
    assert linked
    assert all(r["generated_from_vacuum_first_association"] for r in records)


def test_v0143_derived_longitudinal_zero_not_stored_path_facing_zero():
    reports = run_exploratory(width=3, height=3, cycles=4)
    long_report = reports["DERIVED_LONGITUDINAL_RESIDUAL_REPORT.json"]
    assert long_report["definition"] == "lambda(P)=Phi(P)-Phi(a_path(P))"
    assert long_report["zero_is_derived_not_stored"] is True
    zero_records = [r for r in long_report["records"] if r["lambda_zero_derived"]]
    assert zero_records
    assert all(r["derived_not_stored"] for r in zero_records)
    assert all(r["stored_path_facing_scalar_value_used"] is False for r in zero_records)
    assert all(r["component_zero_layer_used"] is False for r in zero_records)


def test_v0143_transverse_slot_generates_clean_candidates_but_path_slot_control_fails():
    reports = run_exploratory(width=3, height=3, cycles=4)
    candidates = reports["POSTRUN_TRANSVERSE_RECORD_CANDIDATE_REPORT.json"]["records"]
    clean_by_variant = {r["variant_id"] for r in candidates if r["clean_photon_like_candidate"]}
    assert "C_CONJUGATE_LINK_TRANSVERSE_SLOT" in clean_by_variant
    assert "D_SUCCESSOR_COVARIANT_CONJUGATE_SLOT" in clean_by_variant
    assert "B_CONJUGATE_LINK_PATH_SLOT_CONTROL" not in clean_by_variant
    path_slot_failures = [r for r in candidates if r["variant_id"] == "B_CONJUGATE_LINK_PATH_SLOT_CONTROL"]
    assert path_slot_failures
    assert all("nonzero_derived_longitudinal_residual" in r["fails_clean_photon_like_status_reason"] for r in path_slot_failures)


def test_v0143_path_accommodation_uses_derived_lambda_not_raw_component():
    reports = run_exploratory(width=3, height=3, cycles=4)
    paths = reports["PATH_ACCOMMODATION_FROM_DERIVED_RESIDUAL_REPORT.json"]["records"]
    clean_paths = [p for p in paths if p["classification_source"] == "derived_longitudinal_residual_clean_candidate_pair"]
    assert clean_paths
    assert all(p["delta_l"] == 0 for p in clean_paths)
    assert all(p["endpoint_drive_source"] == "derived_longitudinal_residual_lambda_not_raw_path_facing_scalar_value" for p in paths)
    controls = [p for p in paths if p["classification_source"].startswith("nonzero_derived_longitudinal")]
    assert {p["delta_l"] for p in controls} == {-1, 1}


def test_v0143_nonzero_path_facing_control_preserved_as_noncertifying_control():
    reports = run_exploratory(width=3, height=3, cycles=4)
    control = reports["PHOTON_NONZERO_PATH_FACING_CONTROL_REPORT.json"]
    assert control["classification"] == "longitudinally_loaded_path_capable_excitation_control"
    assert control["noncertifying_photon_perturbation_control"] is True
    assert control["zero_control"]["delta_l"] == 0
    assert control["same_sign_nonzero_control"]["delta_l"] == 1
    assert control["opposite_sign_nonzero_control"]["delta_l"] == -1


def test_v0143_approval_packet_contains_required_materials(tmp_path):
    payloads = approval_packet_payloads()
    assert "EXPLORATORY_RUNNER_SPEC.json" in payloads
    assert "WHOLE_FIELD_VARIANTS.json" in payloads
    assert "POSTRUN_DERIVED_LONGITUDINAL_CERTIFIER_RULES.json" in payloads
    path = write_approval_packet(tmp_path / "packet.zip")
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    assert set(payloads).issubset(names)
