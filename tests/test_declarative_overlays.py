import json
from pathlib import Path

import pytest
import numpy as np

import scalar_field_geometry as sfg
from rank3_enforced import (
    AdmissionVerdict,
    CertifiedIdentityRemapRule,
    DiagnosticManifest,
    ManifestError,
    ModelManifest,
    ModelPackage,
    RuleMetadata,
    RuleStatus,
    ZeroScalarUpdateRule,
    run_declarative_overlay,
    run_model_package,
)

ROOT = Path(__file__).resolve().parents[1]


def test_control_overlay_runs_with_compiled_overlay_hash():
    result = run_declarative_overlay(ROOT / "overlays" / "minimal_control_overlay.json")
    assert result.manifest.run_kind == "control"
    assert result.evidence.compiled_overlay_hash != "direct_model_package"
    assert result.controls.passed
    assert result.primary_result.verify()
    assert not result.certified


def test_candidate_overlay_runs_but_is_not_admitted():
    result = run_declarative_overlay(ROOT / "overlays" / "minimal_candidate_overlay.json")
    assert result.manifest.run_kind == "candidate"
    assert result.evidence.compiled_overlay_hash != "direct_model_package"
    assert result.controls.passed
    assert result.gate.external_admission_verdict == AdmissionVerdict.AMBIGUOUS
    assert not result.certified


def test_two_support_candidate_overlay_expands_mandatory_controls():
    result = run_declarative_overlay(ROOT / "overlays" / "two_support_candidate_overlay.json")
    control_names = {report.name for report in result.controls.reports}
    assert "completed_path_scope" in control_names
    assert "active_phase_path_scope" in control_names
    assert "directed_graph_mode" in control_names
    assert "undirected_graph_mode" in control_names
    assert "path_length_summary" in {report.name for report in result.readouts}


def test_python_overlay_path_is_rejected(tmp_path):
    path = tmp_path / "bad_overlay.py"
    path.write_text("print('not allowed')")
    with pytest.raises(ManifestError):
        run_declarative_overlay(path)


def test_executable_overlay_keys_are_rejected(tmp_path):
    payload = json.loads((ROOT / "overlays" / "minimal_control_overlay.json").read_text())
    payload["rules"]["python"] = "lambda x: x"
    path = tmp_path / "bad_overlay.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ManifestError):
        run_declarative_overlay(path)


def test_direct_candidate_modelpackage_is_blocked():
    initial_state = sfg.generate_initial_association_state(
        n_points=8,
        seed=999,
        generation_rule="random_distinct_no_self",
    )
    update = ZeroScalarUpdateRule()
    remap = CertifiedIdentityRemapRule()
    config = sfg.ScalarFieldGeometryConfig(
        initial_state=initial_state,
        initial_phi=np.zeros(initial_state.n_points),
        n_layers=3,
        graph_mode="undirected",
        path_scope="completed",
        phase_rule=sfg.cyclic_phase_rule,
        pair_weight_rule=sfg.inverse_length_pair_weight,
        triplet_lift_rule=sfg.product_triplet_lift,
        scalar_update_rule=update,
        association_remap_rule=remap,
    )
    fake_candidate_update = RuleMetadata(
        name="fake_candidate_zero_update",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="fake",
    )
    fake_candidate_remap = RuleMetadata(
        name="fake_candidate_identity_remap",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="fake",
    )
    manifest = ModelManifest(
        model_name="direct_candidate_should_block",
        model_version="0.1.0",
        purpose="prove candidate direct ModelPackage is blocked",
        run_kind="candidate",
        external_admission_verdict=AdmissionVerdict.AMBIGUOUS,
        diagnostics=DiagnosticManifest(),
    )
    package = ModelPackage(
        manifest=manifest,
        config=config,
        scalar_update_metadata=fake_candidate_update,
        association_remap_metadata=fake_candidate_remap,
    )
    with pytest.raises(ManifestError):
        run_model_package(package)
