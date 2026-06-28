from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ManifestError
from .overlay_schema import DeclarativeOverlay, SupportSpec


@dataclass(frozen=True)
class CompiledModelPlan:
    required_readouts: tuple[str, ...]
    required_controls: tuple[str, ...]
    required_path_scopes: tuple[str, ...]
    required_graph_modes: tuple[str, ...]
    required_phases: tuple[int, ...]
    forbidden_interpretations: tuple[str, ...]


BASE_READOUTS = (
    "result_shape",
    "state_verification",
    "phi_history_hash",
    "geometry_snapshot_count",
)

BASE_CONTROLS = (
    "identity_remap_zero_update",
    "identity_remap_candidate_update",
    "candidate_remap_zero_update",
)

BASE_FORBIDDEN = (
    "visualization_as_physical_space",
    "control_rule_as_admitted_dynamics",
    "candidate_rule_as_admitted_dynamics",
    "post_hoc_diagnostic_selection",
    "arbitrary_python_overlay",
)

EXPLICIT_PATH_READOUTS = (
    "center_locus_readout",
    "structural_silence_readout",
    "delta_l_classification",
)

CHARGE_PATH_READOUTS = (
    "relation_complete_packet_readout",
    "common_mode_zero_sum_report",
)

ASSOCIATION_INDEXED_CONTROLS = (
    "association_indexed_two_ledger_control",
    "association_indexed_identity_stiffness_control",
    "association_indexed_zero_stiffness_control",
    "residual_recipe_rejection_control",
)


def _dedupe(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _validate_support_indices(support: SupportSpec, *, n_points: int) -> None:
    all_indices = tuple(support.support_points) + tuple(support.boundary_points) + tuple(support.dressing_points)
    for index in all_indices:
        if index < 0 or index >= n_points:
            raise ManifestError(f"Support {support.name!r} contains out-of-range point {index}.")
    if len(set(support.support_points)) != len(support.support_points):
        raise ManifestError(f"Support {support.name!r} has duplicate support_points.")
    for phase, point in support.active_phase_map.items():
        if phase not in (0, 1, 2):
            raise ManifestError(f"Support {support.name!r} has invalid active phase {phase}.")
        if point < 0 or point >= n_points:
            raise ManifestError(f"Support {support.name!r} active point {point} is out of range.")


def _validate_non_overlap(supports: tuple[SupportSpec, ...]) -> None:
    seen: dict[int, str] = {}
    for support in supports:
        for point in support.support_points:
            if point in seen:
                raise ManifestError(
                    f"Non-overlap failed: point {point} appears in both {seen[point]!r} and {support.name!r}."
                )
            seen[point] = support.name


def compile_model_type(overlay: DeclarativeOverlay) -> CompiledModelPlan:
    for support in overlay.supports:
        _validate_support_indices(support, n_points=overlay.initial_geometry.n_points)

    if overlay.constraints.non_overlap_required:
        _validate_non_overlap(overlay.supports)

    if overlay.model_type == "minimal_control":
        if overlay.supports:
            raise ManifestError("minimal_control does not accept supports.")
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(BASE_CONTROLS + overlay.requested_controls),
            required_path_scopes=(overlay.execution.path_scope,),
            required_graph_modes=(overlay.execution.graph_mode,),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN,
        )

    if overlay.model_type == "two_support_path_adjustment":
        if len(overlay.supports) != 2:
            raise ManifestError("two_support_path_adjustment requires exactly two supports.")
        if overlay.initialization.mode != "support_seeded":
            raise ManifestError(
                "two_support_path_adjustment requires initialization.mode='support_seeded' so SOO "
                "starts from declared support-owned boundary/dressing records, not all-zero vacuum."
            )
        if overlay.constraints.require_three_phase_coherence:
            for support in overlay.supports:
                if set(support.active_phase_map.keys()) != {0, 1, 2}:
                    raise ManifestError(
                        f"Support {support.name!r} lacks complete active_phase_map for phases 0,1,2."
                    )
        if not overlay.constraints.non_overlap_required:
            raise ManifestError("two_support_path_adjustment requires non_overlap_required=true.")
        extra_readouts = EXPLICIT_PATH_READOUTS if overlay.path_construction.rule != "none" else ()
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + ("path_length_summary",) + extra_readouts + overlay.requested_readouts),
            required_controls=_dedupe(
                BASE_CONTROLS
                + (
                    "completed_path_scope",
                    "active_phase_path_scope",
                    "directed_graph_mode",
                    "undirected_graph_mode",
                )
                + overlay.requested_controls
            ),
            required_path_scopes=("completed", "active_phase"),
            required_graph_modes=("directed", "undirected"),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + ("support_selection_after_run",),
        )

    if overlay.model_type == "association_indexed_soo_feedback_candidate":
        if overlay.rules.scalar_update_rule != "association_indexed_soo_v1":
            raise ManifestError("association_indexed_soo_feedback_candidate requires scalar_update_rule='association_indexed_soo_v1'.")
        if overlay.initialization.mode == "support_seeded":
            raise ManifestError("association_indexed_soo_feedback_candidate uses support_seeded_two_ledger, vacuum_zero, or explicit_phi; legacy support_seeded is residual-recipe-only.")
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(BASE_CONTROLS + ASSOCIATION_INDEXED_CONTROLS + overlay.requested_controls),
            required_path_scopes=(overlay.execution.path_scope,),
            required_graph_modes=(overlay.execution.graph_mode,),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + (
                "point_to_self_as_general_soo",
                "residual_recipe_as_candidate_soo",
                "post_readout_stiffness_selection",
                "stiffness_feedback_as_solved_without_closure_verdict",
            ),
        )

    if overlay.model_type == "charge_attraction_repulsion_candidate":
        if overlay.rules.scalar_update_rule != "association_indexed_soo_v1":
            raise ManifestError("charge_attraction_repulsion_candidate requires scalar_update_rule='association_indexed_soo_v1'.")
        if overlay.path_construction.rule != "linear_support_path_v0_2":
            raise ManifestError("charge_attraction_repulsion_candidate requires path_construction.rule='linear_support_path_v0_2'.")
        if overlay.initialization.mode != "support_seeded_two_ledger":
            raise ManifestError("charge_attraction_repulsion_candidate requires initialization.mode='support_seeded_two_ledger'.")
        if len(overlay.supports) != 2:
            raise ManifestError("charge_attraction_repulsion_candidate requires exactly two supports.")
        if not overlay.constraints.non_overlap_required:
            raise ManifestError("charge_attraction_repulsion_candidate requires non_overlap_required=true.")
        for support in overlay.supports:
            if set(support.active_phase_map.keys()) != {0, 1, 2}:
                raise ManifestError(f"Support {support.name!r} lacks complete active_phase_map for phases 0,1,2.")
            if support.handedness not in ("right", "left"):
                raise ManifestError(f"Charge support {support.name!r} must declare handedness 'right' or 'left'.")
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + ("path_length_summary",) + EXPLICIT_PATH_READOUTS + CHARGE_PATH_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(BASE_CONTROLS + ASSOCIATION_INDEXED_CONTROLS + (
                "completed_path_scope",
                "active_phase_path_scope",
                "directed_graph_mode",
                "undirected_graph_mode",
            ) + overlay.requested_controls),
            required_path_scopes=("completed", "active_phase"),
            required_graph_modes=("directed", "undirected"),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + (
                "support_selection_after_run",
                "path_construction_after_run",
                "residual_recipe_as_candidate_soo",
                "charge_result_as_stiffness_certification",
                "center_locus_as_update_input",
            ),
        )



    if overlay.model_type == "charge_role_path_remap_dynamic_path_candidate":
        if overlay.path_construction.rule != "role_path_two_support_v0_1":
            raise ManifestError("charge_role_path_remap_dynamic_path_candidate requires path_construction.rule='role_path_two_support_v0_1'.")
        if overlay.rules.scalar_update_rule not in ("bounded_context_soo_v1", "association_indexed_soo_v1"):
            raise ManifestError("charge_role_path_remap_dynamic_path_candidate requires bounded_context_soo_v1 or association_indexed_soo_v1.")
        if overlay.rules.association_remap_rule not in (
            "candidate_identity_remap_v0_1",
            "identity_no_remap",
            "path_continuation_role_remap_v1",
        ):
            raise ManifestError("charge_role_path_remap_dynamic_path_candidate requires identity or path_continuation_role_remap_v1 remap.")
        if len(overlay.supports) != 2:
            raise ManifestError("charge_role_path_remap_dynamic_path_candidate requires exactly two supports.")
        if not overlay.constraints.non_overlap_required:
            raise ManifestError("charge_role_path_remap_dynamic_path_candidate requires non_overlap_required=true.")
        for support in overlay.supports:
            if set(support.active_phase_map.keys()) != {0, 1, 2}:
                raise ManifestError(f"Support {support.name!r} lacks complete active_phase_map for phases 0,1,2.")
            if support.handedness not in ("right", "left"):
                raise ManifestError(f"Charge role/path support {support.name!r} must declare handedness 'right' or 'left'.")
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + ("path_length_summary",) + EXPLICIT_PATH_READOUTS + ("role_path_midpoint_arrival_readout",) + CHARGE_PATH_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(BASE_CONTROLS + (
                "completed_path_scope",
                "active_phase_path_scope",
                "directed_graph_mode",
                "undirected_graph_mode",
            ) + overlay.requested_controls),
            required_path_scopes=("completed", "active_phase"),
            required_graph_modes=("directed", "undirected"),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + (
                "legacy_identity_remap_suite_as_theorem_capable",
                "support_selection_after_run",
                "path_construction_after_run",
                "role_path_midpoint_readout_as_path_mutation",
                "same_opposite_label_as_path_change_trigger",
                "center_locus_as_update_input",
            ),
        )

    if overlay.model_type == "gravitation_path_candidate":
        if overlay.rules.scalar_update_rule != "association_indexed_soo_v1":
            raise ManifestError("gravitation_path_candidate requires scalar_update_rule='association_indexed_soo_v1'.")
        if overlay.path_construction.rule != "linear_support_path_v0_2":
            raise ManifestError("gravitation_path_candidate requires path_construction.rule='linear_support_path_v0_2'.")
        if overlay.initialization.mode != "support_seeded_two_ledger":
            raise ManifestError("gravitation_path_candidate requires initialization.mode='support_seeded_two_ledger'.")
        if len(overlay.supports) != 2:
            raise ManifestError("gravitation_path_candidate requires exactly two neutral supports.")
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + ("path_length_summary",) + EXPLICIT_PATH_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(BASE_CONTROLS + ASSOCIATION_INDEXED_CONTROLS + overlay.requested_controls),
            required_path_scopes=(overlay.execution.path_scope,),
            required_graph_modes=(overlay.execution.graph_mode,),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + ("mass_or_gravity_claim_without_interface_calibration",),
        )

    if overlay.model_type == "two_support_explicit_path_adjustment":
        if overlay.path_construction.rule != "linear_support_path_v0_1":
            raise ManifestError("two_support_explicit_path_adjustment requires path_construction.rule='linear_support_path_v0_1'.")
        if len(overlay.supports) != 2:
            raise ManifestError("two_support_explicit_path_adjustment requires exactly two supports.")
        if overlay.initialization.mode != "support_seeded":
            raise ManifestError("two_support_explicit_path_adjustment requires support_seeded initialization.")
        if not overlay.constraints.non_overlap_required:
            raise ManifestError("two_support_explicit_path_adjustment requires non_overlap_required=true.")
        for support in overlay.supports:
            if set(support.active_phase_map.keys()) != {0, 1, 2}:
                raise ManifestError(
                    f"Support {support.name!r} lacks complete active_phase_map for phases 0,1,2."
                )
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + ("path_length_summary",) + EXPLICIT_PATH_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(
                BASE_CONTROLS
                + (
                    "completed_path_scope",
                    "active_phase_path_scope",
                    "directed_graph_mode",
                    "undirected_graph_mode",
                )
                + overlay.requested_controls
            ),
            required_path_scopes=("completed", "active_phase"),
            required_graph_modes=("directed", "undirected"),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + ("support_selection_after_run", "path_construction_after_run"),
        )

    raise ManifestError(f"Unknown locked model_type: {overlay.model_type}")
