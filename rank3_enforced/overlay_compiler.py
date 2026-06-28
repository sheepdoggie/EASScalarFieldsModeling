from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .certified_runner import ModelPackage
from .exceptions import ManifestError
from .fingerprints import stable_json_hash
from .initialization_runner import (
    recipe_uses_support_initialization_source,
    run_initialization_epoch,
    strip_support_initialization_terms,
)
from .locked_registries import (
    build_association_remap_rule,
    build_scalar_update_rule,
    get_pair_weight_rule,
    get_phase_rule,
    get_readout_rules,
    get_triplet_lift_rule,
)
from .manifest import DiagnosticManifest, ModelManifest
from .model_type_registry import compile_model_type
from .overlay_schema import DeclarativeOverlay
from .path_construction import build_explicit_path_association_state
from .optional_modules import validate_optional_modules
from .path_debugging import spec_from_optional_modules
from .rule_metadata import AdmissionVerdict, get_rule_metadata
from .soo_compiler import build_declarative_soo_update_rule
from .soo_schema import parse_soo_recipe, SOORecipe
from .association_indexed_soo import build_association_indexed_soo_update_rule


def _external_verdict(value: str) -> AdmissionVerdict:
    try:
        return AdmissionVerdict(value)
    except ValueError as exc:
        raise ManifestError(f"Invalid external_admission_verdict: {value}") from exc


def _initial_seed(overlay: DeclarativeOverlay) -> int:
    if overlay.initial_geometry.seed is not None:
        return int(overlay.initial_geometry.seed)
    if overlay.initial_geometry.seed_set:
        # The current scalar_field_geometry runner accepts one initial state.
        # Full seed sweeps are compiled as required diagnostics/controls later;
        # this first seed is the primary run seed.
        return int(overlay.initial_geometry.seed_set[0])
    raise ManifestError("No initial seed available.")


def _build_initial_phi(overlay: DeclarativeOverlay, *, n_points: int) -> np.ndarray:
    if overlay.initial_phi.kind == "zeros":
        return np.zeros(n_points, dtype=np.float64)
    if overlay.initial_phi.kind == "explicit":
        return np.asarray(overlay.initial_phi.values, dtype=np.float64)
    raise ManifestError(f"Unsupported initial_phi.kind: {overlay.initial_phi.kind}")


def _parse_soo_recipe_if_present(overlay: DeclarativeOverlay) -> SOORecipe | None:
    if overlay.rules.scalar_update_rule != "soo_declarative_v0_1":
        return None
    params = overlay.rules.scalar_update_params
    raw_recipe = params.get("recipe")
    if not isinstance(raw_recipe, dict):
        raise ManifestError("soo_declarative_v0_1 requires scalar_update_params.recipe object.")
    return parse_soo_recipe(raw_recipe)



def _diagnostic_points_for_path(path_report: object | None, supports: tuple[object, ...]) -> tuple[tuple[int, str], ...]:
    points: list[tuple[int, str]] = []
    if path_report is not None:
        path_points = tuple(int(x) for x in getattr(path_report, "path_points"))
        L = len(path_points)
        if L:
            if L % 2 == 1:
                points.append((path_points[L // 2], "declared_center"))
            else:
                points.append((path_points[L // 2 - 1], "declared_center_left"))
                points.append((path_points[L // 2], "declared_center_right"))
        points.append((int(getattr(path_report, "left_anchor")), "left_support_anchor"))
        points.append((int(getattr(path_report, "right_anchor")), "right_support_anchor"))
    for support in supports:
        name = str(getattr(support, "name", "support"))
        for phase, point in sorted(dict(getattr(support, "active_phase_map", {})).items()):
            points.append((int(point), f"{name}_active_dressing_phase_{int(phase)}"))
        for index, point in enumerate(tuple(getattr(support, "boundary_points", ()))):
            points.append((int(point), f"{name}_boundary_{index}"))
        for index, point in enumerate(tuple(getattr(support, "dressing_points", ()))):
            points.append((int(point), f"{name}_dressing_{index}"))
    seen: set[int] = set()
    deduped: list[tuple[int, str]] = []
    for point, role in points:
        if point in seen:
            continue
        seen.add(point)
        deduped.append((point, role))
    return tuple(deduped)

def _build_measurement_scalar_update_rule(
    overlay: DeclarativeOverlay,
    recipe: SOORecipe | None,
    *,
    path_construction_report: object | None = None,
):
    if overlay.rules.scalar_update_rule == "association_indexed_soo_v1":
        return build_association_indexed_soo_update_rule(
            overlay.rules.scalar_update_params,
            n_points=overlay.initial_geometry.n_points,
            diagnostic_points=_diagnostic_points_for_path(path_construction_report, overlay.supports),
        )
    if overlay.rules.scalar_update_rule != "soo_declarative_v0_1":
        return build_scalar_update_rule(
            overlay.rules.scalar_update_rule,
            overlay.rules.scalar_update_params,
        )
    assert recipe is not None
    measurement_recipe = recipe
    if recipe_uses_support_initialization_source(recipe):
        measurement_recipe = strip_support_initialization_terms(recipe)
    return build_declarative_soo_update_rule(
        measurement_recipe,
        epoch_label="measurement",
        supports=overlay.supports,
        path_construction_report=path_construction_report,
        diagnostic_points=_diagnostic_points_for_path(path_construction_report, overlay.supports),
    )


def compile_overlay_to_model_package(
    overlay: DeclarativeOverlay,
    *,
    overlay_hash: str,
) -> ModelPackage:
    """Compile a data-only overlay into a locked ModelPackage.

    No executable overlay logic is accepted. Rule names and readout names are
    resolved only through locked registries. Support-origin initialization is
    executed here as a sealed pre-measurement epoch when declared.
    """

    plan = compile_model_type(overlay)
    optional_module_report = validate_optional_modules(overlay.optional_modules)
    run_debugging_spec = spec_from_optional_modules(overlay.optional_modules)
    soo_recipe = _parse_soo_recipe_if_present(overlay)

    if overlay.initialization.mode == "support_seeded" and overlay.rules.scalar_update_rule not in ("soo_declarative_v0_1",):
        raise ManifestError("legacy support_seeded initialization currently requires scalar_update_rule='soo_declarative_v0_1'. Use support_seeded_two_ledger with association_indexed_soo_v1.")
    if overlay.initialization.mode == "support_seeded_two_ledger" and overlay.rules.scalar_update_rule != "association_indexed_soo_v1":
        raise ManifestError("support_seeded_two_ledger initialization requires scalar_update_rule='association_indexed_soo_v1'.")

    if overlay.initialization.mode not in ("support_seeded", "support_seeded_two_ledger") and soo_recipe is not None and recipe_uses_support_initialization_source(soo_recipe):
        raise ManifestError("support_initialization_source may only be used with initialization.mode='support_seeded'.")

    association_remap_rule = build_association_remap_rule(
        overlay.rules.association_remap_rule,
        overlay.rules.association_remap_params,
    )

    path_construction_report = None
    if overlay.path_construction.rule in ("linear_support_path_v0_1", "linear_support_path_v0_2"):
        initial_state, path_construction_report = build_explicit_path_association_state(
            n_points=overlay.initial_geometry.n_points,
            path_spec=overlay.path_construction,
            supports=overlay.supports,
            allow_self_association=overlay.initial_geometry.allow_self_association,
        )
    else:
        initial_state = sfg.generate_initial_association_state(
            n_points=overlay.initial_geometry.n_points,
            seed=_initial_seed(overlay),
            generation_rule=overlay.initial_geometry.generation_rule,  # type: ignore[arg-type]
            allow_self_association=overlay.initial_geometry.allow_self_association,
        )
    declared_initial_phi = _build_initial_phi(overlay, n_points=initial_state.n_points)

    phase_rule = get_phase_rule(overlay.execution.phase_rule)
    pair_weight_rule = get_pair_weight_rule(overlay.execution.pair_weight_rule)
    triplet_lift_rule = get_triplet_lift_rule(overlay.execution.triplet_lift_rule)

    initialization_result = run_initialization_epoch(
        initialization=overlay.initialization,
        initial_state=initial_state,
        initial_phi=declared_initial_phi,
        supports=overlay.supports,
        graph_mode=overlay.execution.graph_mode,
        path_scope=overlay.execution.path_scope,
        phase_rule=phase_rule,
        pair_weight_rule=pair_weight_rule,
        triplet_lift_rule=triplet_lift_rule,
        soo_recipe=soo_recipe,
        path_construction_report=path_construction_report,
        scalar_update_rule_name=overlay.rules.scalar_update_rule,
        scalar_update_params=overlay.rules.scalar_update_params,
    )

    scalar_update_rule = _build_measurement_scalar_update_rule(
        overlay,
        soo_recipe,
        path_construction_report=path_construction_report,
    )

    config = sfg.ScalarFieldGeometryConfig(
        initial_state=initial_state,
        initial_phi=np.asarray(initialization_result.phi_after_initialization, dtype=np.float64),
        n_layers=overlay.execution.n_layers,
        graph_mode=overlay.execution.graph_mode,
        path_scope=overlay.execution.path_scope,
        phase_rule=phase_rule,
        pair_weight_rule=pair_weight_rule,
        triplet_lift_rule=triplet_lift_rule,
        scalar_update_rule=scalar_update_rule,
        association_remap_rule=association_remap_rule,
        allow_self_association=overlay.initial_geometry.allow_self_association,
        initial_phi_previous=(None if initialization_result.phi_previous_for_measurement is None else np.asarray(initialization_result.phi_previous_for_measurement, dtype=np.float64)),
    )

    diagnostics = DiagnosticManifest(
        required_readouts=plan.required_readouts,
        required_controls=plan.required_controls,
        required_path_scopes=plan.required_path_scopes,
        required_graph_modes=plan.required_graph_modes,
        required_phases=plan.required_phases,
        seed_set=overlay.initial_geometry.seed_set
        or ((overlay.initial_geometry.seed,) if overlay.initial_geometry.seed is not None else ()),
        tensor_slices=(),
    )

    manifest = ModelManifest(
        model_name=overlay.model_name,
        model_version=overlay.model_version,
        purpose=overlay.purpose,
        run_kind=overlay.run_kind,
        external_admission_verdict=_external_verdict(overlay.external_admission_verdict),
        diagnostics=diagnostics,
        requested_certification=overlay.requested_certification,
        expected_core_hash=overlay.expected_core_hash,
        forbidden_interpretations=plan.forbidden_interpretations,
        notes=(
            overlay.notes
            + "\nCompiled from data-only declarative overlay. "
            + f"overlay_hash={overlay_hash}. supports_hash="
            + stable_json_hash([asdict(support) for support in overlay.supports])
            + f". optional_module_hash={optional_module_report.fingerprint()}"
            + f". initialization_hash={initialization_result.report.fingerprint()}"
            + (f". path_construction_hash={path_construction_report.fingerprint()}" if path_construction_report is not None else "")
        ).strip(),
    )

    readout_rules = get_readout_rules(
        plan.required_readouts,
        path_construction_report=path_construction_report,
        supports=overlay.supports,
    )

    return ModelPackage(
        manifest=manifest,
        config=config,
        scalar_update_metadata=get_rule_metadata(scalar_update_rule),
        association_remap_metadata=get_rule_metadata(association_remap_rule),
        readout_rules=readout_rules,
        compiled_overlay_hash=overlay_hash,
        initialization_report=initialization_result.report,
        initialization_soo_traces=initialization_result.soo_traces,
        initial_two_ledger_report=initialization_result.initial_two_ledger_report,
        optional_module_report=optional_module_report,
        path_construction_report=path_construction_report,
        run_debugging_spec=run_debugging_spec,
        initialization_settling_report=initialization_result.settling_report,
    )
