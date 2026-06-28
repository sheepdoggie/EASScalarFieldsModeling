from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

import scalar_field_geometry as sfg
from .controls import CertifiedIdentityRemapRule, ZeroScalarUpdateRule
from .exceptions import ManifestError
from .readouts import (
    DEFAULT_READOUTS,
    CenterLocusReadout,
    DeltaLClassificationReadout,
    GeometrySnapshotCountReadout,
    PathLengthSummaryReadout,
    PhiHistoryHashReadout,
    ReadoutRule,
    ResultShapeReadout,
    StateVerificationReadout,
    StructuralSilenceReadout,
    RelationCompletePacketReadout,
    CommonModeZeroSumReadout,
)
from .rule_metadata import RuleMetadata, RuleStatus
from .soo_compiler import build_declarative_soo_update_rule
from .association_indexed_soo import AssociationIndexedSOOUpdateRule
from .bounded_context_soo import BoundedContextSOOUpdateRule, build_bounded_context_soo_update_rule
from .path_facing_remap import PathTargetDerivedExternalRemapRule, build_path_target_derived_external_remap_rule
from .role_path_remap import PathContinuationRoleRemapRule, build_path_continuation_role_remap_rule
from .dynamic_paths import DressingRoleMap, RelationalPathRecord
from .soo_schema import parse_soo_recipe


@dataclass(frozen=True)
class RegistryContrastTensorUpdateRule:
    """Locked candidate scalar-update rule for enforced overlay tests.

    This is candidate/demo-style behavior, not final SOO. It is included so
    candidate overlays can exercise the enforcement path without arbitrary
    Python plugins.
    """

    stiffness: float = 0.1
    name: str = "candidate_contrast_tensor_update_v0_1"
    metadata: RuleMetadata = RuleMetadata(
        name="candidate_contrast_tensor_update_v0_1",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="locked_registry_candidate_contrast_tensor_update_v0_1",
        allowed_for_certified_runs=False,
        notes="Locked candidate scalar update; not final SOO and not admitted.",
    )

    def __call__(self, context: sfg.ScalarUpdateContext) -> sfg.FloatArray:
        return sfg.ContrastTensorUpdateRule(stiffness=float(self.stiffness))(context)


@dataclass(frozen=True)
class RegistryCandidateIdentityRemapRule:
    """Locked candidate no-change remap used to test candidate overlay flow.

    This is not admitted EAS remapping. It is intentionally conservative and
    exists only as a locked registry item so candidate runs do not need custom
    Python overlays.
    """

    name: str = "candidate_identity_remap_v0_1"
    metadata: RuleMetadata = RuleMetadata(
        name="candidate_identity_remap_v0_1",
        version="0.1.0",
        status=RuleStatus.CANDIDATE,
        source_hash="locked_registry_candidate_identity_remap_v0_1",
        allowed_for_certified_runs=False,
        notes="Locked candidate no-change remap; not final EAS remapping.",
    )

    def __call__(self, context: sfg.RemapContext) -> sfg.IntArray:
        return context.state_current.assoc.copy()


@dataclass(frozen=True)
class RegistryItem:
    name: str
    factory: Callable[..., Any]
    metadata: RuleMetadata | None = None


def _zero_scalar_update_factory(**params: Any) -> ZeroScalarUpdateRule:
    if params:
        raise ManifestError(f"zero_scalar_update accepts no params, got {sorted(params)}")
    return ZeroScalarUpdateRule()


def _identity_remap_factory(**params: Any) -> CertifiedIdentityRemapRule:
    if params:
        raise ManifestError(f"identity_no_remap accepts no params, got {sorted(params)}")
    return CertifiedIdentityRemapRule()


def _association_indexed_factory(**params: Any):
    raise ManifestError(
        "association_indexed_soo_v1 requires overlay compiler context (n_points, diagnostic_points); "
        "use compile_overlay_to_model_package rather than registry factory directly."
    )


def _soo_declarative_factory(**params: Any):
    allowed = {"recipe"}
    unknown = set(params) - allowed
    if unknown:
        raise ManifestError(f"soo_declarative_v0_1 unknown params: {sorted(unknown)}")
    raw_recipe = params.get("recipe")
    if not isinstance(raw_recipe, dict):
        raise ManifestError("soo_declarative_v0_1 requires scalar_update_params.recipe object.")
    recipe = parse_soo_recipe(raw_recipe)
    return build_declarative_soo_update_rule(recipe)


def _bounded_context_soo_factory(**params: Any) -> BoundedContextSOOUpdateRule:
    return build_bounded_context_soo_update_rule(dict(params))


def _candidate_contrast_factory(**params: Any) -> RegistryContrastTensorUpdateRule:
    allowed = {"stiffness"}
    unknown = set(params) - allowed
    if unknown:
        raise ManifestError(f"candidate_contrast_tensor_update_v0_1 unknown params: {sorted(unknown)}")
    return RegistryContrastTensorUpdateRule(stiffness=float(params.get("stiffness", 0.1)))


def _candidate_identity_remap_factory(**params: Any) -> RegistryCandidateIdentityRemapRule:
    if params:
        raise ManifestError(f"candidate_identity_remap_v0_1 accepts no params, got {sorted(params)}")
    return RegistryCandidateIdentityRemapRule()


def _path_target_derived_external_remap_factory(**params: Any) -> PathTargetDerivedExternalRemapRule:
    return build_path_target_derived_external_remap_rule(dict(params))


def _path_continuation_role_remap_factory(**params: Any) -> PathContinuationRoleRemapRule:
    return build_path_continuation_role_remap_rule(dict(params))


SCALAR_UPDATE_RULES: dict[str, RegistryItem] = {
    "zero_scalar_update": RegistryItem("zero_scalar_update", _zero_scalar_update_factory, ZeroScalarUpdateRule().metadata),
    "soo_declarative_v0_1": RegistryItem(
        "soo_declarative_v0_1",
        _soo_declarative_factory,
        build_declarative_soo_update_rule(parse_soo_recipe({
            "recipe_id": "registry_metadata_recipe",
            "residual_terms": [{"id": "active", "operator_id": "active_association_contrast", "weight": 1.0}],
            "closure": {"id": "linear_response", "response_scale": 0.0},
        })).metadata,
    ),
    "association_indexed_soo_v1": RegistryItem(
        "association_indexed_soo_v1",
        _association_indexed_factory,
        AssociationIndexedSOOUpdateRule.metadata,
    ),
    "bounded_context_soo_v1": RegistryItem(
        "bounded_context_soo_v1",
        _bounded_context_soo_factory,
        BoundedContextSOOUpdateRule.metadata,
    ),
    "candidate_contrast_tensor_update_v0_1": RegistryItem(
        "candidate_contrast_tensor_update_v0_1",
        _candidate_contrast_factory,
        RegistryContrastTensorUpdateRule().metadata,
    ),
}

ASSOCIATION_REMAP_RULES: dict[str, RegistryItem] = {
    "identity_no_remap": RegistryItem("identity_no_remap", _identity_remap_factory, CertifiedIdentityRemapRule().metadata),
    "candidate_identity_remap_v0_1": RegistryItem(
        "candidate_identity_remap_v0_1",
        _candidate_identity_remap_factory,
        RegistryCandidateIdentityRemapRule().metadata,
    ),
    "path_target_derived_external_remap_v1": RegistryItem(
        "path_target_derived_external_remap_v1",
        _path_target_derived_external_remap_factory,
        PathTargetDerivedExternalRemapRule(eligible_points=(0,)).metadata,
    ),
    "path_continuation_role_remap_v1": RegistryItem(
        "path_continuation_role_remap_v1",
        _path_continuation_role_remap_factory,
        PathContinuationRoleRemapRule(
            paths=(RelationalPathRecord(
                path_id="metadata_path", left_endpoint=0, right_endpoint=2, ordered_nodes=(1,)
            ),),
            dressing_roles=(DressingRoleMap(
                point=0, boundary_slot=0, path_slot=1, vacuum_slot=2, path_id="metadata_path", endpoint_side="left"
            ),),
        ).metadata,
    ),
}

PHASE_RULES: dict[str, Callable[[int], int]] = {
    "cyclic_phase": sfg.cyclic_phase_rule,
}

PAIR_WEIGHT_RULES: dict[str, Callable[[sfg.FloatArray], sfg.FloatArray]] = {
    "inverse_path_length": sfg.inverse_length_pair_weight,
    "bounded_inverse_path_length": sfg.bounded_inverse_length_pair_weight,
}

TRIPLET_LIFT_RULES: dict[str, Callable[[sfg.FloatArray], sfg.FloatArray]] = {
    "product_triplet_lift": sfg.product_triplet_lift,
    "minimum_triplet_lift": sfg.minimum_triplet_lift,
}

READOUT_RULES: dict[str, ReadoutRule] = {
    "result_shape": ResultShapeReadout(),
    "state_verification": StateVerificationReadout(),
    "phi_history_hash": PhiHistoryHashReadout(),
    "geometry_snapshot_count": GeometrySnapshotCountReadout(),
    "path_length_summary": PathLengthSummaryReadout(),
}

PATH_READOUT_NAMES = {
    "center_locus_readout",
    "structural_silence_readout",
    "delta_l_classification",
}

SUPPORT_READOUT_NAMES = {
    "relation_complete_packet_readout",
    "common_mode_zero_sum_report",
}

def _build_path_readout(name: str, *, path_construction_report: object | None) -> ReadoutRule:
    if path_construction_report is None:
        raise ManifestError(f"Readout {name!r} requires explicit path_construction.")
    if name == "center_locus_readout":
        return CenterLocusReadout(path_construction_report)
    if name == "structural_silence_readout":
        return StructuralSilenceReadout(path_construction_report)
    if name == "delta_l_classification":
        return DeltaLClassificationReadout(path_construction_report)
    raise ManifestError(f"Unknown locked path readout rule: {name}")


def build_scalar_update_rule(name: str, params: dict[str, Any]) -> Any:
    try:
        item = SCALAR_UPDATE_RULES[name]
    except KeyError as exc:
        raise ManifestError(f"Unknown locked scalar_update_rule: {name}") from exc
    return item.factory(**params)


def build_association_remap_rule(name: str, params: dict[str, Any]) -> Any:
    try:
        item = ASSOCIATION_REMAP_RULES[name]
    except KeyError as exc:
        raise ManifestError(f"Unknown locked association_remap_rule: {name}") from exc
    return item.factory(**params)


def get_phase_rule(name: str) -> Callable[[int], int]:
    try:
        return PHASE_RULES[name]
    except KeyError as exc:
        raise ManifestError(f"Unknown locked phase_rule: {name}") from exc


def get_pair_weight_rule(name: str) -> Callable[[sfg.FloatArray], sfg.FloatArray]:
    try:
        return PAIR_WEIGHT_RULES[name]
    except KeyError as exc:
        raise ManifestError(f"Unknown locked pair_weight_rule: {name}") from exc


def get_triplet_lift_rule(name: str) -> Callable[[sfg.FloatArray], sfg.FloatArray]:
    try:
        return TRIPLET_LIFT_RULES[name]
    except KeyError as exc:
        raise ManifestError(f"Unknown locked triplet_lift_rule: {name}") from exc


def get_readout_rules(
    names: tuple[str, ...],
    *,
    path_construction_report: object | None = None,
    supports: tuple[object, ...] = (),
) -> tuple[ReadoutRule, ...]:
    readouts: list[ReadoutRule] = []
    for name in names:
        if name in PATH_READOUT_NAMES:
            readouts.append(_build_path_readout(name, path_construction_report=path_construction_report))
            continue
        if name in SUPPORT_READOUT_NAMES:
            if name == "relation_complete_packet_readout":
                readouts.append(RelationCompletePacketReadout(tuple(supports)))
            elif name == "common_mode_zero_sum_report":
                readouts.append(CommonModeZeroSumReadout(tuple(supports)))
            else:
                raise ManifestError(f"Unknown support readout: {name}")
            continue
        try:
            readouts.append(READOUT_RULES[name])
        except KeyError as exc:
            raise ManifestError(f"Unknown locked readout rule: {name}") from exc
    return tuple(readouts)


def registry_names() -> dict[str, tuple[str, ...]]:
    return {
        "scalar_update_rules": tuple(sorted(SCALAR_UPDATE_RULES)),
        "association_remap_rules": tuple(sorted(ASSOCIATION_REMAP_RULES)),
        "phase_rules": tuple(sorted(PHASE_RULES)),
        "pair_weight_rules": tuple(sorted(PAIR_WEIGHT_RULES)),
        "triplet_lift_rules": tuple(sorted(TRIPLET_LIFT_RULES)),
        "readout_rules": tuple(sorted(set(READOUT_RULES) | PATH_READOUT_NAMES | SUPPORT_READOUT_NAMES)),
    }
