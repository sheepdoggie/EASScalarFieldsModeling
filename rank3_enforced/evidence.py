from __future__ import annotations

from dataclasses import dataclass

from .fingerprints import array_hash, stable_json_hash
from .immutable_result import ImmutableScalarFieldGeometryResult
from .manifest import ModelManifest
from .readouts import ReadoutReport
from .rule_metadata import RuleMetadata


@dataclass(frozen=True)
class EvidencePackage:
    manifest_hash: str
    initial_state_hash: str
    initial_phi_hash: str
    scalar_update_rule_hash: str
    association_remap_rule_hash: str
    result_hash: str
    readout_hash: str
    control_hash: str
    compiled_overlay_hash: str
    soo_trace_hash: str
    soo_functional_hash: str
    initialization_hash: str
    package_hash: str


def build_evidence_package(
    *,
    manifest: ModelManifest,
    scalar_update_metadata: RuleMetadata,
    association_remap_metadata: RuleMetadata,
    result: ImmutableScalarFieldGeometryResult,
    readouts: tuple[ReadoutReport, ...],
    controls_hash: str,
    compiled_overlay_hash: str | None = None,
    soo_trace_hash: str = "not_applicable",
    soo_functional_hash: str = "not_applicable",
    initialization_hash: str = "not_applicable",
) -> EvidencePackage:
    manifest_hash = stable_json_hash(manifest)
    initial_state_hash = result.states[0].fingerprint if result.states else "missing"
    initial_phi_hash = array_hash(result.phi[0]) if result.phi.shape[0] else "missing"
    result_hash = result.fingerprint()
    readout_hash = stable_json_hash([report.fingerprint for report in readouts])
    overlay_hash = compiled_overlay_hash or "direct_model_package"
    package_hash = stable_json_hash(
        {
            "manifest_hash": manifest_hash,
            "initial_state_hash": initial_state_hash,
            "initial_phi_hash": initial_phi_hash,
            "scalar_update_rule_hash": scalar_update_metadata.source_hash,
            "association_remap_rule_hash": association_remap_metadata.source_hash,
            "result_hash": result_hash,
            "readout_hash": readout_hash,
            "control_hash": controls_hash,
            "compiled_overlay_hash": overlay_hash,
            "soo_trace_hash": soo_trace_hash,
            "soo_functional_hash": soo_functional_hash,
            "initialization_hash": initialization_hash,
        }
    )
    return EvidencePackage(
        manifest_hash=manifest_hash,
        initial_state_hash=initial_state_hash,
        initial_phi_hash=initial_phi_hash,
        scalar_update_rule_hash=scalar_update_metadata.source_hash,
        association_remap_rule_hash=association_remap_metadata.source_hash,
        result_hash=result_hash,
        readout_hash=readout_hash,
        control_hash=controls_hash,
        compiled_overlay_hash=overlay_hash,
        soo_trace_hash=soo_trace_hash,
        soo_functional_hash=soo_functional_hash,
        initialization_hash=initialization_hash,
        package_hash=package_hash,
    )
