import pytest
import numpy as np

import scalar_field_geometry as sfg
from rank3_enforced import (
    AdmissionVerdict,
    CertifiedIdentityRemapRule,
    CertificationBlocked,
    DiagnosticManifest,
    ModelManifest,
    ModelPackage,
    RuleMetadata,
    RuleStatus,
    ZeroScalarUpdateRule,
    run_model_package,
)


def test_requested_certification_blocks_control_rules():
    initial_state = sfg.generate_initial_association_state(
        n_points=8,
        seed=456,
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
    # Deliberately lie by marking control logic admitted but not allowed for certification.
    fake_admitted_update = RuleMetadata(
        name="fake_admitted_zero_update",
        version="0.1.0",
        status=RuleStatus.ADMITTED,
        source_hash="fake",
        allowed_for_certified_runs=False,
    )
    fake_admitted_remap = RuleMetadata(
        name="fake_admitted_identity_remap",
        version="0.1.0",
        status=RuleStatus.ADMITTED,
        source_hash="fake",
        allowed_for_certified_runs=False,
    )
    manifest = ModelManifest(
        model_name="bad_certification",
        model_version="0.1.0",
        purpose="should block",
        run_kind="admission",
        external_admission_verdict=AdmissionVerdict.ADMITTED,
        diagnostics=DiagnosticManifest(),
        requested_certification=True,
    )
    package = ModelPackage(
        manifest=manifest,
        config=config,
        scalar_update_metadata=fake_admitted_update,
        association_remap_metadata=fake_admitted_remap,
    )
    with pytest.raises(Exception):
        run_model_package(package)
