from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


FRAMEWORK_VERSION = "0.1.35"
FRAMEWORK_RELEASE_LABEL = "0.1.35-gradient-vacuum-split-planning"

FRAMEWORK_CAPABILITIES: frozenset[str] = frozenset(
    {
        "declarative_overlay_only",
        "signed_evidence_envelope",
        "explicit_path_construction",
        "center_locus_readout",
        "structural_silence_readout",
        "delta_l_classification",
        "SOO_FUNCTIONAL_REPORT",
        "soo_functional_hash",
        "diagnostic_point_residual_samples",
        "relation_complete_packet_contrast",
        "dual_plaintext_encrypted_output",
        "support_seeded_initialization",
        "signed_release_manifest_guard",
        "version_guard_environment_cache",
        "configuration_only_job_bundles",
        "association_indexed_soo_v1",
        "two_ledger_soo_state",
        "phase_indexed_stiffness_reports",
        "cyclic_return_map_report",
        "stiffness_feedback_closure_diagnostic",
        "induced_stiffness_report",
        "stiffness_closure_report",
        "residual_recipe_candidate_rejection",
        "support_seeded_two_ledger_initialization",
        "optional_experimental_modules",
        "charge_attraction_repulsion_module",
        "gravitation_path_module",
        "linear_support_path_v0_2_permutation",
        "relation_complete_packet_readout",
        "common_mode_zero_sum_report",
        "charge_path_support_burden_rules",
        "association_indexed_controls",
        "installed_console_run_manager",
        "builtin_overlay_suites_package_data",
        "code_free_run_workspaces",
        "run_debugging_optional_module",
        "path_neighborhood_soo_change_retention",
        "debugging_default_off",
        "suite_progress_reporting",
        "cli_debug_opt_in",
        "debug_overlay_staging",
        "path_facing_association_report",
        "debug_instrumentation_does_not_alter_soo",

        "targeted_soo_debug_pair_runner",
        "suite_case_filtering",
        "soo_path_transition_analysis",
        "initialization_measurement_epoch_report",
        "debug_pair_analysis_cli",

        "soo_settled_initialization_gate",
        "initialization_settling_report",
        "support_influenced_exterior_witness_settling",
        "relational_path_witness_steady_state",
        "single_support_dressing_witness_steady_state",
        "initialization_measurement_cycle_separation",
        "initialization_settling_early_stop",
        "initialization_settling_progress",
        "initialization_settling_cli_overrides",
        "targeted_initialization_debug_pair_runner",

        "soo_validation_controls",
        "identity_recurrence_validation",
        "analytic_oscillator_amplitude_validation",
        "cyclic_return_spectrum_validation",
        "recurrent_two_ledger_solve_validation",

        "direct_recurrent_initialization_solver",
        "bounded_context_soo_v1",
        "boundedness_derived_stiffness_profile",
        "rank3_complete_context_soo_kernel",
        "interpolated_initialization_profile_constraints",
        "finite_cycle_recurrent_profile_solve",
        "phase_consistent_two_ledger_diagnostic",

        "path_target_derived_external_remap_v1",

        "path_continuation_role_remap_v1",
        "role_based_dressing_association_map",
        "orientation_aware_path_continuation",
        "geometry_transaction_reports",
        "relational_path_record_registry",
        "path_length_change_external_monitor_only",
        "external_path_monitor_api_v0_1",
        "path_edit_transaction_validator_v0_1",
        "path_edit_not_intrinsic_framework_rule",
        "active_path_record_external_edit_support",
        "separate_install_and_run_subtrees",
        "publication_certified_run_mode",
        "github_installable_source_tree",
        "versioned_release_archive",
        "release_manifest_capability_check",
        "charge_role_path_remap_dynamic_path_suite_v0_1",
        "role_path_two_support_path_construction_v0_1",
        "role_path_midpoint_arrival_readout",
        "role_path_remap_report_artifact",
        "legacy_charge_identity_remap_suite_marked_not_theorem_capable",
        "path_change_admission_gate_policy_v0_1",
        "path_change_external_monitor_policy_v0_1",
        "latest_framework_code_sha256_manifest_field",
        "accepted_framework_code_sha256_manifest_field",
        "initialization_steady_state_gate_policy_v0_1",

        "modeling_intent_contract_layer_v0_1",
        "exploratory_modeling_mode",
        "certification_admission_modeling_mode",
        "modeling_intent_compliance_report",
        "modeling_intent_contract_cli",
        "certification_requires_predeclared_contract",
        "exploratory_default_without_contract",
        "contract_bound_run_manager_staging",
        "modeling_plan_generation_v0_1",
        "modeling_plan_user_approval_gate_v0_1",
        "certification_requires_approved_plan_v0_1",
        "approved_plan_hash_binding_v0_1",
        "pre_run_plan_validation_report_v0_1",
        "certification_plan_executability_gate_v0_1",
        "plan_structural_vs_executable_status_v0_1",
        "zero_eligible_certification_plan_block_v0_1",

        "contract_propagation_enforced_v0_1",
        "suite_contract_hash_consistency_v0_1",
        "certification_fail_closed_pre_run_v0_1",
        "warning_mode_non_certifying_artifacts_v0_1",
        "offline_local_release_guard_sources_v0_1",
        "release_identity_self_consistency_gate_v0_1",
        "release_manifest_exact_code_hash_gate_v0_1",
        "contract_driven_overlay_synthesis_v0_1",
        "operator_required_items_report_v0_1",
        "certification_operator_item_preflight_v0_1",
        "no_candidate_promotion_by_synthesis_v0_1",

        "operator_review_packet_generator_v0_1",
        "operator_required_items_generator_directives_v0_1",
        "chat_customizable_certification_material_templates_v0_1",
        "certification_run_requires_operator_agent_approval_loop_v0_1",
        "data_driven_workflow_protocols_v0_1",
        "workflow_protocol_hash_manifest_field_v0_1",
        "operator_agent_protocol_loader_v0_1",
        "workflow_protocol_validation_cli_v0_1",

        "charge_path_admission_controls_suite_v0_1",
        "admission_capable_bounded_context_soo_v1_declaration",
        "admitted_nonlabel_path_monitor_policy_v0_1",
        "negative_control_overlay_suite_v0_1",
        "package_embedded_release_signature_materials_v0_1",
        "executable_certification_plan_case_materials_v0_1",
        "effective_orientation_record_v0_1",
        "path_monitor_decision_report_v0_1",
        "path_edit_admission_report_v0_1",
        "geometry_transaction_report_v0_2",
        "active_path_record_report_v0_1",
        "theorem_failure_trace_v0_1",
        "nonlabel_monitor_forbidden_input_full_gate_v0_1",
        "candidate_not_admitted_blocks_certification_v0_1",
        "contract_required_initialization_settling_gate_v0_1",
        "packageable_failed_certification_attempts_v0_1",
        "gradient_governed_vacuum_split_plan_v0_1",
        "undefined_vacuum_admissibility_manifest_v0_1",
        "vacuum_split_six_slot_manifest_v0_1",
        "association_gradient_minimization_manifest_v0_1",
        "association_latency_manifest_v0_1",
        "relational_gradient_center_invalidity_manifest_v0_1",
        "theorem_hypotheses_not_primitive_rules_v0_1",
        "gradient_path_approval_items_zip_v0_1",
        "generator_readout_separation_contract_v0_2",
        "forced_delta_l_leakage_control_v0_1",
        "topology_transaction_audit_plan_v0_1",
        "scalar_sign_only_theorem_scope_v0_1",
        "ready_for_certification_plan_not_theorem_certification_v0_1",
    }
)


@dataclass(frozen=True)
class CapabilityReport:
    framework_version: str
    framework_release_label: str
    capabilities: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def capability_report(required: Iterable[str] = ()) -> CapabilityReport:
    required_tuple = tuple(sorted(set(str(x) for x in required)))
    missing = tuple(x for x in required_tuple if x not in FRAMEWORK_CAPABILITIES)
    return CapabilityReport(
        framework_version=FRAMEWORK_VERSION,
        framework_release_label=FRAMEWORK_RELEASE_LABEL,
        capabilities=tuple(sorted(FRAMEWORK_CAPABILITIES)),
        required_capabilities=required_tuple,
        missing_capabilities=missing,
        passed=not missing,
    )


def require_capabilities(required: Iterable[str]) -> CapabilityReport:
    report = capability_report(required)
    if not report.passed:
        raise RuntimeError(
            "Framework is missing required capabilities: " + ", ".join(report.missing_capabilities)
        )
    return report
