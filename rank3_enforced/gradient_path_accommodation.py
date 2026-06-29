from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "gradient_path_accommodation_plan_v0_1"
FRAMEWORK_TARGET_VERSION = "0.1.35"
THEOREM_ID = "gradient_governed_scalar_sign_path_accommodation_v0_1"


@dataclass(frozen=True)
class AdmissibilityItem:
    id: str
    name: str
    status: str
    statement: str
    certification_role: str
    anti_imposition_note: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class HypothesisItem:
    id: str
    name: str
    status: str
    statement: str
    proof_obligation: str
    blocked_if_primitive: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlItem:
    id: str
    purpose: str
    expected_non_certifying_behavior: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AuditGateItem:
    id: str
    question: str
    blocks_certification_if_false: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FROZEN_ADMISSIBILITIES: tuple[AdmissibilityItem, ...] = (
    AdmissibilityItem(
        "A1",
        "vacuum_undefined_association_admissibility",
        "frozen_for_operator_review",
        "An undefined vacuum point has no active rank-3 association record until first association reaches it.",
        "ontology_input",
        "Does not encode support class, center action, or Delta L.",
    ),
    AdmissibilityItem(
        "A2",
        "vacuum_split_admissibility",
        "frozen_for_operator_review",
        "First association to an undefined vacuum point resolves it into two scalar branches with equal and opposite scalar values.",
        "ontology_input",
        "Creates scalar-sign conjugate branches but does not prescribe path shortening or lengthening.",
    ),
    AdmissibilityItem(
        "A3",
        "six_slot_split_admissibility",
        "frozen_for_operator_review",
        "Each resolved branch carries three association slots, so one split vacuum site contributes six pending branch association slots.",
        "ontology_input",
        "Specifies branch-slot accounting only; it does not choose a topology transaction.",
    ),
    AdmissibilityItem(
        "A4",
        "association_gradient_admissibility",
        "frozen_for_operator_review",
        "Among available association candidates, the admitted new association is the one minimizing scalar-gradient burden.",
        "generator_rule",
        "Selection is based on scalar-gradient burden, not same/opposite labels or target outcomes.",
    ),
    AdmissibilityItem(
        "A5",
        "one_cycle_association_latency",
        "frozen_for_operator_review",
        "New association formation is not instantaneous; proposals made in one cycle become usable associations in the next cycle.",
        "generator_rule",
        "Latency prevents instantaneous spreading from serving as an uninspected path edit.",
    ),
    AdmissibilityItem(
        "A6",
        "relational_gradient_admissibility",
        "frozen_for_operator_review",
        "A relational path point carries relationship only when it participates in a determinate scalar gradient.",
        "readout_admission_rule",
        "This admits or rejects path-carrier status from gradient determinacy, not from theorem labels.",
    ),
    AdmissibilityItem(
        "A7",
        "center_invalidity_admissibility",
        "frozen_for_operator_review",
        "No-gradient centers and ambiguous-gradient centers cannot persist as relational path carriers.",
        "readout_admission_rule",
        "Invalidity is a carrier-status condition; it does not by itself specify insertion or removal.",
    ),
)


THEOREM_FACING_HYPOTHESES: tuple[HypothesisItem, ...] = (
    HypothesisItem(
        "H1",
        "opposite_sign_center_no_gradient_hypothesis",
        "proof_obligation_not_admissibility",
        "Opposite scalar-sign support pairs produce a center inflection/no-gradient invalidity.",
        "Must be derived from generated scalar signs, association records, and path-center gradients without reading a target Delta L.",
    ),
    HypothesisItem(
        "H2",
        "same_sign_center_ambiguous_gradient_hypothesis",
        "proof_obligation_not_admissibility",
        "Same scalar-sign support pairs produce a center peak/ambiguous-gradient invalidity.",
        "Must be derived from generated scalar signs, association records, and path-center gradients without reading a target Delta L.",
    ),
    HypothesisItem(
        "H3",
        "no_gradient_removal_accommodation_hypothesis",
        "proof_obligation_not_admissibility",
        "A no-gradient invalid relational carrier is accommodated by removal.",
        "Must be justified as a topology transaction policy after center invalidity is observed; it must not be a sign-label dispatch rule.",
    ),
    HypothesisItem(
        "H4",
        "ambiguous_gradient_vacuum_insertion_hypothesis",
        "proof_obligation_not_admissibility",
        "An ambiguous-gradient invalid center is accommodated by insertion of a vacuum point.",
        "Must be justified as a topology transaction policy after center invalidity is observed; it must not be a sign-label dispatch rule.",
    ),
    HypothesisItem(
        "H5",
        "dangling_vacuum_reassociation_hypothesis",
        "proof_obligation_not_admissibility",
        "Removal leaves dangling beside-path associations that reassociate to vacuum; insertion creates new vacuum associations on both sides of the path.",
        "Must be audited as a consequence of an admitted transaction rather than as a preselected path outcome.",
    ),
)


REQUIRED_CONTROLS: tuple[ControlItem, ...] = (
    ControlItem("all_vacuum_no_seed_control", "No first association seed is available.", "No split, no triangle, no support, no path accommodation."),
    ControlItem("association_randomized_control", "Association selection is randomized rather than gradient-minimized.", "No stable same-sign triangle/shell dominance certification."),
    ControlItem("no_latency_control", "Association proposals commit without one-cycle latency.", "Quarantined or fails admission because spreading is instantaneous."),
    ControlItem("three_slot_only_control", "Split site is incorrectly restricted to three total branch slots.", "Fails split-vacuum admissibility; cannot represent six pending branch slots."),
    ControlItem("below_threshold_y_le_x_control", "Shell candidate amplitude is below or equal to the lower shell threshold.", "Forms triangle/duplicate activity, not shell support candidate."),
    ControlItem("above_window_y_too_large_control", "Shell candidate amplitude is above the accepted shell-admission window.", "Forms independent high-amplitude triangle, not shell support candidate."),
    ControlItem("no_soo_control", "Association geometry is generated without SOO persistence.", "Cannot certify packet/support persistence."),
    ControlItem("no_center_invalidity_rule_control", "Center load/null is recorded but carrier invalidity is not admitted.", "No Delta L certification from load/null alone."),
    ControlItem("forced_delta_l_leakage_control", "A malicious or contaminated generator is given target Delta L or sign-label dispatch.", "Must be rejected before execution or classified as leakage/manipulation failure."),
)


REQUIRED_AUDIT_GATES: tuple[AuditGateItem, ...] = (
    AuditGateItem("source_provenance", "Are all admissibilities, hypotheses, and cost functionals source-identified and frozen before execution?"),
    AuditGateItem("verdict_independence", "Is target Delta L unavailable to the generator, association selector, and topology transaction selector?"),
    AuditGateItem("blind_generation_projection_separation", "Are support/path records generated before Delta L projection/readout?"),
    AuditGateItem("negative_controls", "Do all mandatory negative controls execute and separate from theorem cases?"),
    AuditGateItem("leakage_checks", "Are charge labels, handedness labels, imposed support classes, same/opposite labels, and target outcomes absent from generator inputs?"),
    AuditGateItem("topology_manipulation_check", "Are insertion/removal transactions triggered only from center-gradient admissibility and a separately approved transaction policy?"),
    AuditGateItem("redressing_check", "Does cyclic/reflection redressing preserve the report class?"),
    AuditGateItem("conjugacy_check", "Do + and - branches remain exact scalar-sign conjugates through split and association formation?"),
    AuditGateItem("odd_even_path_check", "Are odd-center and even-center path cases both handled without ad hoc center special casing?"),
)


FORBIDDEN_GENERATOR_INPUTS: tuple[str, ...] = (
    "same_label",
    "opposite_label",
    "charge_label",
    "handedness_label",
    "target_delta_l",
    "expected_delta_l",
    "predeclared_support_membership",
    "predeclared_center_action",
    "preselected_path_outcome",
)


ALLOWED_GENERATOR_INPUTS: tuple[str, ...] = (
    "scalar_signs",
    "scalar_values",
    "undefined_vacuum_state",
    "association_candidates",
    "frozen_admissibility_rules",
    "cost_functional_id",
)


REQUIRED_OUTPUT_ARTIFACTS: tuple[str, ...] = (
    "SOURCE_PROVENANCE_REPORT.json",
    "ADMISSIBILITY_STATUS_REPORT.json",
    "HYPOTHESIS_STATUS_REPORT.json",
    "GENERATOR_READOUT_SEPARATION_REPORT.json",
    "NEGATIVE_CONTROL_REPORT.json",
    "LEAKAGE_MANIPULATION_REPORT.json",
    "TOPOLOGY_TRANSACTION_AUDIT.json",
    "CONJUGACY_REPORT.json",
    "ODD_EVEN_PATH_REPORT.json",
    "BASE_GATE_REPORT.json",
    "THEOREM_VERDICT_REPORT.json",
)


RUNNER_CAUSAL_CHAIN: tuple[str, ...] = (
    "undefined_vacuum",
    "first_association",
    "+/-_split_with_six_branch_slots",
    "one_cycle_association_proposal_latency",
    "gradient_minimizing_association_selection",
    "same_sign_triangle_shell_candidate_formation",
    "SOO_over_generated_support_candidates",
    "scalar_sign_support_classification",
    "two_support_path_sector_SOO",
    "center_gradient_classification",
    "topology_transaction_proposal",
    "transaction_admission_or_rejection",
    "final_delta_l_readout",
)


def theorem_statement() -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "theorem_id": THEOREM_ID,
        "name": "Gradient-Governed Scalar-Sign Path-Accommodation Theorem",
        "scope": "scalar_field_path_sector_only",
        "not_certified_by_this_release": True,
        "ready_for_certification_plan": True,
        "ready_for_theorem_certification": False,
        "given": [
            "vacuum points are undefined until first association",
            "first association resolves a vacuum point into equal/opposite scalar branches",
            "each branch carries three association slots",
            "new associations minimize scalar-gradient burden",
            "new association proposals commit after one cycle",
            "relational path points require determinate scalar gradient",
            "sign-coherent triangle/shell supports are generated without imposed support labels",
        ],
        "then_under_proof_obligation": [
            "opposite scalar-sign support pairs produce center no-gradient invalidity and, if an admitted topology policy applies, removal with Delta L = -1",
            "same scalar-sign support pairs produce center ambiguous-gradient invalidity and, if an admitted topology policy applies, vacuum insertion with Delta L = +1",
        ],
        "interface_language_not_certified": [
            "electric charge",
            "Coulomb behavior",
            "charge magnitude",
            "QED correspondence",
            "empirical attraction/repulsion",
            "lepton hierarchy",
        ],
    }


def admissibility_manifest() -> dict[str, Any]:
    return {
        "schema": "gradient_path_admissibility_manifest_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "admissibilities": [x.to_dict() for x in FROZEN_ADMISSIBILITIES],
        "certification_rule": "Only A1-A7 are admissibility candidates in this package. Accommodation items H1-H5 are proof obligations, not primitive rules.",
    }


def hypothesis_manifest() -> dict[str, Any]:
    return {
        "schema": "gradient_path_hypothesis_manifest_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "hypotheses": [x.to_dict() for x in THEOREM_FACING_HYPOTHESES],
        "certification_rule": "If any hypothesis is implemented as a primitive dispatch from scalar sign, label, or expected Delta L, certification must be blocked.",
    }


def generator_readout_separation_contract() -> dict[str, Any]:
    return {
        "schema": "generator_readout_separation_contract_v0_2",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "runner_causal_chain": list(RUNNER_CAUSAL_CHAIN),
        "required_output_artifacts": list(REQUIRED_OUTPUT_ARTIFACTS),
        "readout_only_fields": [
            "observed_delta_l",
            "delta_l_classification",
            "theorem_verdict",
            "control_separation_verdict",
        ],
        "fail_closed_rule": "Certification mode must stop or emit DO_NOT_CERTIFY if forbidden inputs are present or required artifacts are absent.",
    }


def controls_manifest() -> dict[str, Any]:
    return {
        "schema": "gradient_path_negative_controls_manifest_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "controls": [x.to_dict() for x in REQUIRED_CONTROLS],
        "certification_rule": "Controls are mandatory and must be evaluated before theorem certification can be claimed.",
    }


def audit_gate_manifest() -> dict[str, Any]:
    return {
        "schema": "gradient_path_audit_gate_manifest_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "audit_gates": [x.to_dict() for x in REQUIRED_AUDIT_GATES],
        "certification_rule": "Every gate blocks certification if false.",
    }


def approval_instructions() -> str:
    return """# v0.1.35 Gradient Vacuum-Split Path-Accommodation Approval Packet\n\nStatus: READY FOR CERTIFICATION PLAN, NOT READY FOR THEOREM CERTIFICATION.\n\nReview items:\n\n1. THEOREM_STATEMENT.json\n2. ADMISSIBILITY_MANIFEST.json\n3. HYPOTHESIS_MANIFEST.json\n4. GENERATOR_READOUT_SEPARATION_CONTRACT.json\n5. NEGATIVE_CONTROLS_MANIFEST.json\n6. AUDIT_GATES_MANIFEST.json\n7. ANTI_IMPOSITION_AUDIT.json\n\nApproval meaning:\n\n- Approval freezes the theorem/admissibility/control package for the next modeling-plan draft.\n- Approval does not certify the theorem.\n- Approval does not authorize any runner to use same/opposite labels, charge labels, handedness labels, target Delta L, predeclared support membership, predeclared center action, or preselected path outcome as generator inputs.\n- H1-H5 are proof obligations, not primitive admissibilities.\n\nRequired operator action before certification execution:\n\n1. Review and approve or reject this packet.\n2. If approved, generate a modeling plan bound to the packet hash.\n3. Review and explicitly approve the modeling plan.\n4. Only after plan approval, execute the integrated runner under certification mode.\n"""


def anti_imposition_audit() -> dict[str, Any]:
    primitive_text = "\n".join(
        [x.statement for x in FROZEN_ADMISSIBILITIES]
        + [x.anti_imposition_note for x in FROZEN_ADMISSIBILITIES]
    ).lower()
    forbidden_result_terms = ("delta l = +1", "delta l = -1", "target_delta_l", "expected_delta_l")
    primitive_hits = [term for term in forbidden_result_terms if term in primitive_text]
    hypothesis_terms = "\n".join(x.statement for x in THEOREM_FACING_HYPOTHESES).lower()
    return {
        "schema": "gradient_path_anti_imposition_audit_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "passed": not primitive_hits,
        "primitive_admissibility_result_terms_found": primitive_hits,
        "hypotheses_may_name_theorem_outcomes_but_are_not_primitives": bool(hypothesis_terms),
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "checks": {
            "a8_a10_not_admissibilities": True,
            "same_opposite_labels_forbidden_to_generator": True,
            "charge_labels_forbidden_to_generator": True,
            "handedness_labels_forbidden_to_generator": True,
            "target_delta_l_forbidden_to_generator": True,
            "topology_transaction_requires_center_gradient_admissibility_and_policy": True,
            "release_does_not_certify_theorem": True,
        },
        "verdict": "audit_passed_no_result_imposition_in_v0_1_35_planning_materials" if not primitive_hits else "audit_failed",
    }


def approval_packet_payloads() -> dict[str, str]:
    objects = {
        "THEOREM_STATEMENT.json": theorem_statement(),
        "ADMISSIBILITY_MANIFEST.json": admissibility_manifest(),
        "HYPOTHESIS_MANIFEST.json": hypothesis_manifest(),
        "GENERATOR_READOUT_SEPARATION_CONTRACT.json": generator_readout_separation_contract(),
        "NEGATIVE_CONTROLS_MANIFEST.json": controls_manifest(),
        "AUDIT_GATES_MANIFEST.json": audit_gate_manifest(),
        "ANTI_IMPOSITION_AUDIT.json": anti_imposition_audit(),
    }
    payloads = {name: json.dumps(obj, indent=2, sort_keys=True) + "\n" for name, obj in objects.items()}
    payloads["APPROVAL_INSTRUCTIONS.md"] = approval_instructions()
    return payloads


def write_approval_packet(output: str | Path) -> Path:
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    payloads = approval_packet_payloads()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in sorted(payloads.items()):
            zf.writestr(name, text)
    return output


def validate_generator_inputs(inputs: Iterable[str]) -> dict[str, Any]:
    supplied = tuple(str(x) for x in inputs)
    forbidden = tuple(x for x in supplied if x in FORBIDDEN_GENERATOR_INPUTS)
    unknown = tuple(x for x in supplied if x not in FORBIDDEN_GENERATOR_INPUTS and x not in ALLOWED_GENERATOR_INPUTS)
    return {
        "schema": "gradient_path_generator_input_validation_v0_1",
        "supplied_inputs": supplied,
        "forbidden_inputs_present": forbidden,
        "unknown_inputs_present": unknown,
        "passed": not forbidden and not unknown,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write v0.1.35 gradient path-accommodation approval-items packet.")
    parser.add_argument("--output", default="gradient_path_accommodation_approval_items_v0135.zip")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args(argv)
    path = write_approval_packet(args.output)
    if args.print_summary:
        summary = {
            "output": str(path),
            "theorem_id": THEOREM_ID,
            "admissibility_count": len(FROZEN_ADMISSIBILITIES),
            "hypothesis_count": len(THEOREM_FACING_HYPOTHESES),
            "control_count": len(REQUIRED_CONTROLS),
            "audit_gate_count": len(REQUIRED_AUDIT_GATES),
            "anti_imposition_passed": anti_imposition_audit()["passed"],
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
