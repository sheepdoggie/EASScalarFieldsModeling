from __future__ import annotations

import numpy as np

import scalar_field_geometry as sfg
from rank3_enforced import (
    AdmissionVerdict,
    CertifiedIdentityRemapRule,
    DiagnosticManifest,
    ModelManifest,
    ModelPackage,
    RuleMetadata,
    RuleStatus,
    ZeroScalarUpdateRule,
    run_model_package,
)


def main() -> None:
    initial_state = sfg.generate_initial_association_state(
        n_points=8,
        seed=20260626,
        generation_rule="random_distinct_no_self",
        allow_self_association=False,
    )

    initial_phi = np.zeros(initial_state.n_points, dtype=np.float64)

    scalar_update_rule = ZeroScalarUpdateRule()
    remap_rule = CertifiedIdentityRemapRule()

    config = sfg.ScalarFieldGeometryConfig(
        initial_state=initial_state,
        initial_phi=initial_phi,
        n_layers=4,
        graph_mode="undirected",
        path_scope="completed",
        phase_rule=sfg.cyclic_phase_rule,
        pair_weight_rule=sfg.inverse_length_pair_weight,
        triplet_lift_rule=sfg.product_triplet_lift,
        scalar_update_rule=scalar_update_rule,
        association_remap_rule=remap_rule,
        allow_self_association=False,
    )

    manifest = ModelManifest(
        model_name="minimal_enforced_control",
        model_version="0.1.0",
        purpose="Verify enforceable runner, mandatory controls, freezing, readouts, evidence hashes, and BASE gate plumbing.",
        run_kind="control",
        external_admission_verdict=AdmissionVerdict.CONTROL,
        diagnostics=DiagnosticManifest(),
        requested_certification=False,
    )

    package = ModelPackage(
        manifest=manifest,
        config=config,
        scalar_update_metadata=scalar_update_rule.metadata,
        association_remap_metadata=remap_rule.metadata,
    )

    result = run_model_package(package)

    print("Enforced run completed.")
    print("Certified/admitted:", result.certified)
    print("External verdict:", result.gate.external_admission_verdict.value)
    print("BASE gate passed:", result.gate.passed)
    print("Controls passed:", result.controls.passed)
    print("Primary result verified immutable:", result.primary_result.verify())
    print("Evidence package hash:", result.evidence.package_hash)
    print("Core hash:", result.core_hash)
    print("Readouts:", [report.name for report in result.readouts])
    print("Gate details:", result.gate.details)


if __name__ == "__main__":
    main()
