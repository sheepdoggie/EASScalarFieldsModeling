import numpy as np

import scalar_field_geometry as sfg
from rank3_enforced import (
    AdmissionVerdict,
    CertifiedIdentityRemapRule,
    DiagnosticManifest,
    ModelManifest,
    ModelPackage,
    ZeroScalarUpdateRule,
    run_model_package,
)


def build_package():
    initial_state = sfg.generate_initial_association_state(
        n_points=8,
        seed=123,
        generation_rule="random_distinct_no_self",
        allow_self_association=False,
    )
    initial_phi = np.zeros(initial_state.n_points, dtype=np.float64)
    update = ZeroScalarUpdateRule()
    remap = CertifiedIdentityRemapRule()
    config = sfg.ScalarFieldGeometryConfig(
        initial_state=initial_state,
        initial_phi=initial_phi,
        n_layers=4,
        graph_mode="undirected",
        path_scope="completed",
        phase_rule=sfg.cyclic_phase_rule,
        pair_weight_rule=sfg.inverse_length_pair_weight,
        triplet_lift_rule=sfg.product_triplet_lift,
        scalar_update_rule=update,
        association_remap_rule=remap,
        allow_self_association=False,
    )
    manifest = ModelManifest(
        model_name="test_minimal_control",
        model_version="0.1.0",
        purpose="test",
        run_kind="control",
        external_admission_verdict=AdmissionVerdict.CONTROL,
        diagnostics=DiagnosticManifest(),
        requested_certification=False,
    )
    return ModelPackage(
        manifest=manifest,
        config=config,
        scalar_update_metadata=update.metadata,
        association_remap_metadata=remap.metadata,
    )


def test_minimal_enforced_control_runs_and_freezes():
    result = run_model_package(build_package())
    assert result.controls.passed
    assert result.primary_result.verify()
    assert not result.primary_result.phi.flags.writeable
    assert result.gate.external_admission_verdict == AdmissionVerdict.CONTROL
    assert not result.gate.passed
    assert not result.certified
    assert result.evidence.package_hash


def test_control_phi_unchanged():
    result = run_model_package(build_package())
    assert np.allclose(result.primary_result.phi, 0.0)
