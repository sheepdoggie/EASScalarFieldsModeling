from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
import json

from .fingerprints import stable_json_hash

ModelingMode = Literal["exploratory", "certification"]


@dataclass(frozen=True)
class ModelingIntentContract:
    """Pre-run contract separating exploratory and certification/admission use.

    The contract is data only. It is not a model rule and cannot introduce
    executable monitors, kernels, or diagnostics. Certification mode uses this
    object to define what must be present before a run can have evidential
    status beyond exploratory.
    """

    contract_schema: str = "rank3_modeling_intent_contract_v1"
    modeling_intent: str = "exploratory_modeling"
    mode: ModelingMode = "exploratory"
    claim: dict[str, Any] = field(default_factory=dict)
    required_mechanisms: tuple[str, ...] = ()
    forbidden_shortcuts: tuple[str, ...] = ()
    admissible_inputs: tuple[str, ...] = ()
    required_initialization: tuple[str, ...] = ()
    required_soo_properties: tuple[str, ...] = ()
    required_monitors: tuple[str, ...] = ()
    negative_controls: tuple[str, ...] = ()
    leakage_checks: tuple[str, ...] = ()
    admission_verdict_rules: tuple[str, ...] = ()
    abort_conditions: tuple[str, ...] = ()
    allow_candidate_rules: bool = False
    allow_external_monitors: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class ModelingIntentComplianceReport:
    report_schema: str
    mode: ModelingMode
    modeling_intent: str
    contract_hash: str
    overlay_hash: str | None
    exploratory_default: bool
    certification_eligible: bool
    passed: bool
    violations: tuple[str, ...]
    warnings: tuple[str, ...]
    enforced_before_execution: bool
    forbidden_language: tuple[str, ...]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def _tuple_strs(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(x) for x in value)
    raise ValueError("expected string or list of strings")


def contract_from_dict(payload: dict[str, Any] | None, *, default_mode: str = "exploratory") -> ModelingIntentContract:
    if not payload:
        return ModelingIntentContract(mode="exploratory", modeling_intent="exploratory_default_no_contract", notes="No modeling_intent contract supplied; exploratory mode is mandatory.")
    mode = str(payload.get("mode", default_mode))
    if mode not in ("exploratory", "certification"):
        raise ValueError(f"Unsupported modeling_intent.mode: {mode}")
    return ModelingIntentContract(
        contract_schema=str(payload.get("contract_schema", "rank3_modeling_intent_contract_v1")),
        modeling_intent=str(payload.get("modeling_intent", payload.get("intent_id", "exploratory_modeling"))),
        mode=mode,  # type: ignore[arg-type]
        claim=dict(payload.get("claim", {})),
        required_mechanisms=_tuple_strs(payload.get("required_mechanisms", [])),
        forbidden_shortcuts=_tuple_strs(payload.get("forbidden_shortcuts", [])),
        admissible_inputs=_tuple_strs(payload.get("admissible_inputs", [])),
        required_initialization=_tuple_strs(payload.get("required_initialization", [])),
        required_soo_properties=_tuple_strs(payload.get("required_soo_properties", [])),
        required_monitors=_tuple_strs(payload.get("required_monitors", [])),
        negative_controls=_tuple_strs(payload.get("negative_controls", [])),
        leakage_checks=_tuple_strs(payload.get("leakage_checks", [])),
        admission_verdict_rules=_tuple_strs(payload.get("admission_verdict_rules", [])),
        abort_conditions=_tuple_strs(payload.get("abort_conditions", [])),
        allow_candidate_rules=bool(payload.get("allow_candidate_rules", False)),
        allow_external_monitors=bool(payload.get("allow_external_monitors", False)),
        notes=str(payload.get("notes", "")),
    )


def contract_from_file(path: str | Path) -> ModelingIntentContract:
    return contract_from_dict(json.loads(Path(path).read_text(encoding="utf-8")), default_mode="certification")


def default_exploratory_contract() -> ModelingIntentContract:
    return contract_from_dict(None)


def charge_path_adjustment_certification_template() -> ModelingIntentContract:
    return ModelingIntentContract(
        modeling_intent="charge_path_adjustment_theorem",
        mode="certification",
        claim={
            "same_orientation": "Delta L = +1",
            "opposite_orientation": "Delta L = -1",
            "magnitude": "|Delta L| / L = 1 / L",
        },
        required_mechanisms=(
            "whole_field_SOO",
            "signed_scalar_values_preserved",
            "zero_crossing_allowed",
            "support_steady_initialization",
            "phase_complete_relational_paths",
            "role_path_remap_if_remap_enabled",
            "external_path_monitor_only_for_path_edits",
        ),
        forbidden_shortcuts=(
            "orientation_label_triggers_path_edit",
            "intrinsic_path_length_change_rule",
            "center_only_diagnostic_as_path_change",
            "graph_shortest_path_substitution_for_Delta_L",
            "candidate_kernel_certification",
            "post_hoc_diagnostic_selection",
            "scalar_value_copy_during_remap",
        ),
        admissible_inputs=(
            "data_only_overlay",
            "registered_rules_only",
            "predeclared_initialization",
            "predeclared_controls",
        ),
        required_initialization=(
            "steady_or_recurrent_path_facing_exterior_records",
            "initial_two_ledger_report",
        ),
        required_soo_properties=(
            "whole_field_update",
            "signed_values_not_rectified",
            "SOO_trace_available",
        ),
        required_monitors=(
            "path_monitor_snapshot",
            "external_path_edit_request_log_if_path_edits_enabled",
            "dynamic_path_readout",
        ),
        negative_controls=(
            "no_remap_control",
            "wrong_continuation_slot_control",
            "broken_path_control",
            "label_swap_control",
            "sign_randomized_control",
        ),
        leakage_checks=(
            "orientation_labels_not_read_by_path_edit_logic",
            "diagnostics_not_used_as_update_inputs",
            "external_monitor_declares_exploratory_status",
        ),
        admission_verdict_rules=(
            "Admitted only if BASE gate passes",
            "Admitted only if contract compliance passes",
            "Admitted only if negative controls do not reproduce target event",
            "Ambiguous if required mechanism absent",
            "Rejected if forbidden shortcut is used",
        ),
        abort_conditions=(
            "missing_required_mechanism",
            "failed_initialization_gate",
            "candidate_rule_used_for_certification_without explicit allowance",
            "release_guard_failed",
        ),
        allow_candidate_rules=False,
        allow_external_monitors=True,
        notes="Template contract; edit explicitly before certification/admission use.",
    )


def validate_contract_for_overlay(
    *,
    contract: ModelingIntentContract,
    overlay_payload: dict[str, Any] | None,
    overlay_hash: str | None,
) -> ModelingIntentComplianceReport:
    violations: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}
    payload = overlay_payload or {}
    exploratory_default = contract.modeling_intent == "exploratory_default_no_contract"
    forbidden_language = ("confirmed", "certified", "admitted", "proved", "theorem_holds", "usable_downstream")

    run_kind = str(payload.get("run_kind", "unknown"))
    requested_certification = bool(payload.get("requested_certification", False))
    rules = dict(payload.get("rules", {}))
    scalar_rule = str(rules.get("scalar_update_rule", ""))
    remap_rule = str(rules.get("association_remap_rule", ""))
    model_type = str(payload.get("model_type", ""))
    optional_modules = tuple(str(m.get("module_id", m.get("id", ""))) for m in payload.get("optional_modules", payload.get("modules", [])) if isinstance(m, dict))
    controls = tuple(str(x) for x in payload.get("controls", payload.get("requested_controls", [])))
    readouts = tuple(str(x) for x in payload.get("readouts", payload.get("requested_readouts", [])))
    initialization = dict(payload.get("initialization", {}))
    path_construction = dict(payload.get("path_construction", {}))
    notes = str(payload.get("notes", ""))
    details.update({
        "run_kind": run_kind,
        "requested_certification": requested_certification,
        "model_type": model_type,
        "scalar_update_rule": scalar_rule,
        "association_remap_rule": remap_rule,
        "optional_modules": optional_modules,
        "controls": controls,
        "readouts": readouts,
        "initialization_mode": initialization.get("mode"),
        "path_construction_rule": path_construction.get("rule"),
    })

    if contract.mode == "exploratory":
        if run_kind == "admission" or requested_certification:
            violations.append("exploratory modeling_intent cannot be used with admission run_kind or requested_certification")
        lowered = notes.lower()
        used_forbidden_language = tuple(word for word in forbidden_language if word in lowered)
        if used_forbidden_language:
            warnings.append("exploratory overlay notes contain certification-language: " + ", ".join(used_forbidden_language))
        certification_eligible = False
    else:
        certification_eligible = True
        if run_kind != "admission" or not requested_certification:
            violations.append("certification mode requires run_kind='admission' and requested_certification=true")
        if not contract.claim:
            violations.append("certification mode requires a predeclared claim")
        if not contract.required_mechanisms:
            violations.append("certification mode requires required_mechanisms")
        if not contract.forbidden_shortcuts:
            violations.append("certification mode requires forbidden_shortcuts")
        if not contract.negative_controls:
            violations.append("certification mode requires negative_controls")
        if not contract.leakage_checks:
            violations.append("certification mode requires leakage_checks")
        if "candidate" in scalar_rule and not contract.allow_candidate_rules:
            violations.append("candidate scalar update rule used while contract forbids candidate-rule certification")
        if "external_path_monitor" in optional_modules and not contract.allow_external_monitors:
            violations.append("external monitor requested while contract forbids external monitors")
        # Charge theorem specific guardrails when named.
        if contract.modeling_intent == "charge_path_adjustment_theorem":
            if path_construction.get("rule") not in ("role_path_two_support_v0_1", "linear_support_path_v0_2"):
                violations.append("charge_path_adjustment_theorem requires declared support-to-support relational path construction")
            required_negative_controls = {
                "no_remap_control",
                "wrong_continuation_slot_control",
                "broken_path_control",
                "label_swap_control",
                "sign_randomized_control",
            }
            missing_controls = sorted(required_negative_controls - set(controls))
            if missing_controls:
                violations.append("charge_path_adjustment_theorem missing required negative controls: " + ", ".join(missing_controls))
            if model_type == "charge_path_adjustment_admission_v0_1":
                if scalar_rule != "bounded_context_soo_v1":
                    violations.append("charge_path_adjustment_admission_v0_1 requires non-candidate bounded_context_soo_v1")
                if "candidate" in model_type:
                    violations.append("admission model type may not be candidate-labeled")
            if "external_path_monitor_only_for_path_edits" in contract.required_mechanisms:
                # This checks that path edit logic is not represented as an intrinsic remap/path mutation rule.
                if str(remap_rule).startswith("gated_path_") or "lengthening" in str(remap_rule) or "shortening" in str(remap_rule):
                    violations.append("path-length edit appears as intrinsic framework rule rather than external monitor request")
                if "admitted_nonlabel_path_monitor_v1" in optional_modules:
                    # The overlay parser has already rejected executable logic. The model type registry checks params.
                    details["admitted_nonlabel_path_monitor_present"] = True

    passed = not violations
    return ModelingIntentComplianceReport(
        report_schema="rank3_modeling_intent_compliance_v1",
        mode=contract.mode,
        modeling_intent=contract.modeling_intent,
        contract_hash=contract.fingerprint(),
        overlay_hash=overlay_hash,
        exploratory_default=exploratory_default,
        certification_eligible=certification_eligible and passed,
        passed=passed,
        violations=tuple(violations),
        warnings=tuple(warnings),
        enforced_before_execution=True,
        forbidden_language=forbidden_language,
        details=details,
    )
