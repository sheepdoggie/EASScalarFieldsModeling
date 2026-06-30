import zipfile

from rank3_enforced.capabilities import FRAMEWORK_CAPABILITIES, FRAMEWORK_RELEASE_LABEL, FRAMEWORK_VERSION
from rank3_enforced.vacuum_admissibility_variation import (
    ADMISSIBILITY_VARIANTS,
    ALLOWED_GENERATOR_INPUTS,
    FORBIDDEN_GENERATOR_INPUTS,
    REQUIRED_ARTIFACTS,
    approval_packet_payloads,
    leakage_manipulation_audit,
    run_exploratory,
    validate_generator_inputs,
    write_approval_packet,
)


def test_v0142_version_and_capabilities():
    assert FRAMEWORK_VERSION == "0.1.42"
    assert FRAMEWORK_RELEASE_LABEL == "0.1.42-vacuum-admissibility-variation"
    assert "vacuum_admissibility_variation_runner_v0_1" in FRAMEWORK_CAPABILITIES
    assert "constructed_photon_endpoint_quarantine_v0_1" in FRAMEWORK_CAPABILITIES
    assert "photon_path_facing_zero_layer_control_v0_1" in FRAMEWORK_CAPABILITIES
    assert "postrun_photon_like_certifier_v0_1" in FRAMEWORK_CAPABILITIES
    assert "bounded_support_closure_admissibility_v0_1" in FRAMEWORK_CAPABILITIES
    assert "standard_model_interface_quarantine_v0_1" in FRAMEWORK_CAPABILITIES


def test_v0142_forbidden_inputs_rejected_and_allowed_inputs_pass():
    for forbidden in FORBIDDEN_GENERATOR_INPUTS:
        report = validate_generator_inputs([forbidden])
        assert not report["passed"]
        assert forbidden in report["forbidden_inputs_present"]
    assert validate_generator_inputs(ALLOWED_GENERATOR_INPUTS)["passed"]


def test_v0142_runner_emits_required_artifacts_and_is_non_certifying():
    reports = run_exploratory(cycles=3, split_site_count=2)
    assert set(REQUIRED_ARTIFACTS).issubset(reports)
    verdict = reports["EXPLORATORY_VERDICT_REPORT.json"]
    assert verdict["verdict"] == "EXPLORATORY_ONLY_DO_NOT_CERTIFY"
    assert verdict["theorem_certified"] is False
    assert verdict["charge_certified"] is False
    assert verdict["photon_certified"] is False
    assert reports["LEAKAGE_MANIPULATION_AUDIT.json"]["passed"] is True


def test_v0142_single_vacuum_origin_and_no_constructed_photon_records():
    reports = run_exploratory(cycles=3, split_site_count=2)
    scope = reports["RUN_SCOPE_REPORT.json"]
    assert scope["not_endpoint_class_comparison"] is True
    assert scope["single_origin_chain_for_all_candidates"] == [
        "undefined_vacuum", "split/lift", "SOO", "association_selection", "motif_discovery", "postrun_classification"
    ]
    photon = reports["POSTRUN_PHOTON_LIKE_CERTIFIER_REPORT.json"]
    assert photon["candidate_source"] == "postrun_generated_scalar_field_phase_readouts_only"
    for record in photon["records"]:
        assert record["loaded_transverse_form_supplied"] is False
        assert record["component_zero_layer_sealed_at_initialization"] is False


def test_v0142_variants_A_to_E_present_and_burden_decomposed():
    reports = run_exploratory(cycles=3, split_site_count=2)
    variants = reports["VACUUM_ADMISSIBILITY_VARIANT_LEDGER.json"]["variants"]
    assert [v["id"] for v in variants] == [v.id for v in ADMISSIBILITY_VARIANTS]
    burden = reports["ASSOCIATION_BURDEN_DECOMPOSITION_REPORT.json"]
    assert burden["burden_terms"] == ["scalar_gradient", "split_conjugacy", "relation_complete", "cyclic_covariance", "bounded_closure"]
    assert burden["photon_form_predeclared"] is False
    assert burden["selected_burden_decompositions"]


def test_v0142_quarantines_standard_model_interpretation():
    reports = run_exploratory(cycles=3, split_site_count=2)
    quarantine = reports["STANDARD_MODEL_INTERFACE_QUARANTINE_REPORT.json"]
    assert quarantine["standard_model_interpretation_enabled"] is False
    assert quarantine["triangle_path_accommodation_not_charge_particle_accommodation"] is True
    assert quarantine["v0141_endpoint_classes_have_provenance_mismatch"] is True
    for rec in reports["PATH_ACCOMMODATION_BY_PROVENANCE_REPORT.json"]["records"]:
        assert rec["standard_model_interpretation_quarantined"] is True
        assert rec["target_delta_l_used"] is False
        assert rec["endpoint_class_used_as_selector"] is False


def test_v0142_approval_packet_contains_required_materials(tmp_path):
    payloads = approval_packet_payloads()
    assert "EXPLORATORY_RUNNER_SPEC.json" in payloads
    assert "VACUUM_ADMISSIBILITY_VARIANTS.json" in payloads
    assert "POSTRUN_CERTIFIER_RULES.json" in payloads
    path = write_approval_packet(tmp_path / "packet.zip")
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    assert set(payloads).issubset(names)


def test_v0142_required_negative_controls_present():
    reports = run_exploratory(cycles=3, split_site_count=2)
    controls = reports["NEGATIVE_CONTROL_REPORT.json"]
    assert controls["per_control_artifacts_emitted"] is True
    assert controls["executed_controls_passed"] is True
    assert "NEGATIVE_CONTROL_PHOTON_PATH_FACING_ZERO_LAYER_CONTROL.json" in reports
    assert "NEGATIVE_CONTROL_CONSTRUCTED_PHOTON_ENDPOINT_CONTROL.json" in reports
    audit = leakage_manipulation_audit()
    assert audit["checks"]["photon_path_facing_zero_layer_quarantined"] is True
    assert audit["checks"]["constructed_photon_endpoint_quarantined"] is True
