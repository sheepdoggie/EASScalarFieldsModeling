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



    if overlay.model_type == "charge_path_adjustment_admission_v0_1":
        if overlay.run_kind != "admission" or not overlay.requested_certification:
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires run_kind='admission' and requested_certification=true.")
        if overlay.path_construction.rule != "role_path_two_support_v0_1":
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires path_construction.rule='role_path_two_support_v0_1'.")
        if overlay.rules.scalar_update_rule != "bounded_context_soo_v1":
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires non-candidate scalar_update_rule='bounded_context_soo_v1'.")
        if overlay.rules.association_remap_rule != "admitted_identity_no_remap_v1":
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires non-candidate admitted_identity_no_remap_v1. Path add/remove, if any, must be external-monitor transaction evidence.")
        if len(overlay.supports) != 2:
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires exactly two supports.")
        if not overlay.constraints.non_overlap_required:
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires non_overlap_required=true.")
        if not overlay.constraints.require_three_phase_coherence:
            raise ManifestError("charge_path_adjustment_admission_v0_1 requires three-phase coherence.")
        if overlay.initialization.mode != "explicit_phi":
            raise ManifestError("charge_path_adjustment_admission_v0_1 currently requires explicit_phi plus declared settling witness policy.")
        required_controls = {
            "no_remap_control",
            "wrong_continuation_slot_control",
            "broken_path_control",
            "label_swap_control",
            "sign_randomized_control",
        }
        declared_controls = set(overlay.requested_controls)
        if not required_controls.issubset(declared_controls):
            missing = ", ".join(sorted(required_controls - declared_controls))
            raise ManifestError("charge_path_adjustment_admission_v0_1 missing required negative controls: " + missing)
        module_ids = {str(m.module_id) for m in overlay.optional_modules}
        # Path-edit attempts require the non-label monitor policy. No-remap controls may omit it.
        path_edit_requested = any(str(m.module_id) == "admitted_nonlabel_path_monitor_v1" for m in overlay.optional_modules)
        if "admitted_nonlabel_path_monitor_v1" in module_ids:
            for mod in overlay.optional_modules:
                if mod.module_id == "admitted_nonlabel_path_monitor_v1":
                    params = dict(mod.params)
                    forbidden_inputs = {"orientation", "same_label", "opposite_label", "target_delta_l"}
                    if params.get("reads_orientation_labels", False):
                        raise ManifestError("admitted_nonlabel_path_monitor_v1 may not read orientation/same/opposite/target labels.")
                    decision_inputs = {str(x) for x in params.get("decision_inputs", [])}
                    bad_inputs = sorted(forbidden_inputs & decision_inputs)
                    if bad_inputs:
                        raise ManifestError(
                            "admitted_nonlabel_path_monitor_v1 decision_inputs may not include forbidden inputs: "
                            + ", ".join(bad_inputs)
                        )
                    if params.get("path_edits_are_intrinsic_framework_rule", False):
                        raise ManifestError("path edits must remain external monitor transactions, not intrinsic rules.")
        return CompiledModelPlan(
            required_readouts=_dedupe(BASE_READOUTS + (
                "path_length_summary",
                "role_path_midpoint_arrival_readout",
            ) + EXPLICIT_PATH_READOUTS + CHARGE_PATH_READOUTS + overlay.requested_readouts),
            required_controls=_dedupe(BASE_CONTROLS + (
                "completed_path_scope",
                "active_phase_path_scope",
                "directed_graph_mode",
                "undirected_graph_mode",
                "no_remap_control",
                "wrong_continuation_slot_control",
                "broken_path_control",
                "label_swap_control",
                "sign_randomized_control",
            ) + overlay.requested_controls),
            required_path_scopes=("completed", "active_phase"),
            required_graph_modes=("directed", "undirected"),
            required_phases=(0, 1, 2),
            forbidden_interpretations=BASE_FORBIDDEN + (
                "candidate_rule_as_certification_mechanism",
                "support_selection_after_run",
                "path_construction_after_run",
                "role_path_midpoint_readout_as_path_mutation",
                "same_opposite_label_as_path_change_trigger",
                "orientation_label_as_monitor_input",
                "same_opposite_label_as_monitor_input",
                "target_delta_l_as_monitor_input",
                "center_locus_as_update_input",
                "external_monitor_result_as_theorem_without_admission_verdict",
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
