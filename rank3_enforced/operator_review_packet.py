from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contract_overlay_synthesis import OPERATOR_REQUIREMENTS_SCHEMA
from .fingerprints import file_hash, stable_json_hash
from .modeling_intent import ModelingIntentContract, contract_from_file
from .run_manager import BUILTIN_SUITES

PACKET_SCHEMA = "rank3_operator_review_packet_v2"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


@dataclass(frozen=True)
class OperatorReviewPacketManifest:
    packet_schema: str
    generated_utc: str
    modeling_intent: str
    contract_hash: str
    contract_path: str
    operator_required_items_path: str | None
    synthesis_report_path: str | None
    suite_id: str | None
    output_dir: str
    purpose: str
    workflow_status: str
    requires_user_approval_before_modeling: bool
    generated_files: tuple[str, ...]
    source_hashes: dict[str, str]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def _claim_text(contract: ModelingIntentContract) -> str:
    if not contract.claim:
        return "No claim supplied in contract."
    return "\n".join(f"- `{k}`: `{v}`" for k, v in contract.claim.items())


def _items_text(req_payload: dict[str, Any] | None) -> str:
    if not req_payload:
        return "No OPERATOR_REQUIRED_ITEMS.json supplied. Use this packet as the initial review scaffold."
    items = req_payload.get("items", [])
    if not isinstance(items, list) or not items:
        return "No specific operator-required items were listed."
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            f"- **{item.get('item_id', 'unknown')}** ({item.get('category', 'unknown')}, {item.get('severity', 'unknown')}): "
            f"{item.get('prompt', '')} Reason: {item.get('reason', '')}"
        )
    return "\n".join(out)


def admission_overlay_template(contract: ModelingIntentContract, *, suite_id: str | None) -> dict[str, Any]:
    return {
        "template_schema": "rank3_admission_overlay_template_v1",
        "template_status": "operator_review_required_not_executable_as_is",
        "modeling_intent": contract.to_dict(),
        "model_type": "<operator-select-admitted-model-type>",
        "run_kind": "admission",
        "requested_certification": True,
        "suite_id_basis": suite_id,
        "claim_under_test": contract.claim,
        "rules": {
            "scalar_update_rule": "<operator-select-non-candidate-whole-field-SOO-rule>",
            "association_remap_rule": "<operator-select-admitted-remap-rule-or-identity>",
        },
        "path_construction": {
            "rule": "<role_path_two_support_v0_1-or-other-contract-admitted-path-construction>",
            "phase_complete": True,
            "lanes": "<declare phase-complete relational lanes>",
            "support_layout": "<declare supports, dressings, path nodes, and non-overlap witness>",
        },
        "initialization": {
            "mode": "<operator-declare-steady-or-recurrent-initialization>",
            "settling_gate_required": True,
            "witness_sets": ["<path-facing exterior witnesses>", "<support dressing witnesses>"],
            "abort_if_not_settled": True,
        },
        "readouts": [
            "<dynamic_path_readout>",
            "<signed_midpoint_or_center-pair_record>",
            "<BASE_gate_report>",
            "<admission_verdict_report>",
        ],
        "controls": [
            "<negative-control-overlay-id-1>",
            "<negative-control-overlay-id-2>",
        ],
        "path_edit_policy": {
            "intrinsic_path_length_rule_allowed": False,
            "external_monitor_allowed": bool(contract.allow_external_monitors),
            "external_monitor_id": "<none-or-operator-approved-monitor>",
            "operator_review_required_for_add_remove": True,
        },
        "leakage_prevention": {
            "orientation_labels_may_trigger_edits": False,
            "diagnostics_used_as_update_inputs": False,
            "candidate_rule_certification_allowed": bool(contract.allow_candidate_rules),
        },
        "abort_conditions": list(contract.abort_conditions),
        "notes": "Template only. The modeling chat must replace every <...> placeholder and return this to the operator/user for approval before execution.",
    }


def mechanism_status_template(contract: ModelingIntentContract) -> dict[str, Any]:
    return {
        "template_schema": "rank3_mechanism_status_declaration_v1",
        "template_status": "operator_review_required_not_executable_as_is",
        "modeling_intent": contract.modeling_intent,
        "contract_hash": contract.fingerprint(),
        "mechanisms": [
            {
                "required_mechanism": mech,
                "proposed_rule_or_artifact": "<operator/modeling-chat-fill>",
                "status": "<admitted|candidate|provisional|absent|forbidden>",
                "evidence_path_or_hash": "<path-or-hash>",
                "certification_usable": False,
                "notes": "Explain why this is non-candidate and contract-admissible, or mark absent.",
            }
            for mech in contract.required_mechanisms
        ],
        "candidate_rules_allowed_by_contract": bool(contract.allow_candidate_rules),
    }


def initialization_template(contract: ModelingIntentContract) -> dict[str, Any]:
    return {
        "template_schema": "rank3_initialization_settling_requirements_v1",
        "template_status": "operator_review_required_not_executable_as_is",
        "required_initialization": list(contract.required_initialization),
        "settling_gate": {
            "required": True,
            "criteria": "<fixed/recurrent witness criteria before diagnostic phase>",
            "min_cycles": "<integer>",
            "max_cycles": "<integer>",
            "witness_points_or_records": ["<record-1>", "<record-2>"],
            "abort_if_failed": True,
        },
        "notes": "Populate with concrete pre-run initialization values; do not use post-run fitted criteria.",
    }


def negative_control_template(contract: ModelingIntentContract) -> dict[str, Any]:
    return {
        "template_schema": "rank3_negative_control_overlay_template_v1",
        "template_status": "operator_review_required_not_executable_as_is",
        "modeling_intent": contract.to_dict(),
        "run_kind": "admission_control",
        "requested_certification": True,
        "control_id": "<operator-fill-control-id>",
        "control_type": "<" + "|".join(contract.negative_controls or ("negative_control",)) + ">",
        "must_not_reproduce_target_event": True,
        "expected_non_admission_reason": "<predeclared reason>",
        "overlay_body": "<copy/adapt admission overlay body here without target-enabling shortcut>",
    }


def path_monitor_policy_template(contract: ModelingIntentContract) -> dict[str, Any]:
    return {
        "template_schema": "rank3_path_monitor_policy_v1",
        "template_status": "operator_review_required_not_executable_as_is",
        "path_add_remove_is_eas_ontology": False,
        "intrinsic_framework_path_length_rule_allowed": False,
        "external_monitors_allowed_by_contract": bool(contract.allow_external_monitors),
        "selected_policy": "<none|exploratory_only|contract_admitted_external_monitor>",
        "monitor_id": "<none-or-monitor-id>",
        "monitor_inputs": ["path_monitor_snapshot", "signed_scalar_records", "dynamic_path_state"],
        "forbidden_inputs": ["orientation label as edit trigger", "target Delta L as edit trigger"],
        "transaction_logging_required": True,
        "operator_approval_required_before_certification_use": True,
        "notes": "A monitor may request path edits; it must not make path length change intrinsic EAS ontology.",
    }


def plan_approval_request_template(contract: ModelingIntentContract, *, suite_id: str | None) -> dict[str, Any]:
    return {
        "template_schema": "rank3_modeling_plan_approval_request_v1",
        "template_status": "operator_review_required_not_approved",
        "suite_id": suite_id,
        "modeling_intent": contract.modeling_intent,
        "contract_hash": contract.fingerprint(),
        "proposed_overlay_directory": "<path/to/customized/admission/overlays>",
        "proposed_plan_path": "<path/to/draft/modeling_plan.json>",
        "operator_decision": "<approve|reject|revise>",
        "approval_conditions": [
            "all placeholders replaced",
            "plan_certification_executable=true",
            "negative controls present",
            "release identity/signature verified",
            "no candidate-rule certification unless contract allows it",
        ],
    }


def generate_operator_review_packet(
    *,
    contract_path: str | Path,
    output_dir: str | Path,
    operator_required_items_path: str | Path | None = None,
    synthesis_report_path: str | Path | None = None,
    suite_id: str | None = None,
    notes: str = "",
) -> OperatorReviewPacketManifest:
    contract_path = Path(contract_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    contract = contract_from_file(contract_path)
    req_payload = _read_json(operator_required_items_path)
    synth_payload = _read_json(synthesis_report_path)

    generated: list[str] = []
    source_hashes: dict[str, str] = {"contract": file_hash(contract_path)}
    if operator_required_items_path:
        source_hashes["operator_required_items"] = file_hash(operator_required_items_path)
    if synthesis_report_path:
        source_hashes["synthesis_report"] = file_hash(synthesis_report_path)

    files: dict[str, Any] = {
        "ADMISSION_OVERLAY_TEMPLATE.json": admission_overlay_template(contract, suite_id=suite_id),
        "MECHANISM_STATUS_DECLARATION_TEMPLATE.json": mechanism_status_template(contract),
        "INITIALIZATION_SETTLING_REQUIREMENTS_TEMPLATE.json": initialization_template(contract),
        "NEGATIVE_CONTROL_SUITE_TEMPLATE/negative_control_overlay_template.json": negative_control_template(contract),
        "PATH_MONITOR_POLICY_TEMPLATE.json": path_monitor_policy_template(contract),
        "MODELING_PLAN_APPROVAL_REQUEST_TEMPLATE.json": plan_approval_request_template(contract, suite_id=suite_id),
    }
    for rel, payload in files.items():
        _write_json(out / rel, payload)
        generated.append(rel)

    _write_text(out / "NEGATIVE_CONTROL_SUITE_TEMPLATE/README.md", f"""
# Negative control suite template

Create one concrete overlay for each required negative control in the contract:

{chr(10).join(f'- {c}' for c in contract.negative_controls) or '- <none declared>'}

Each control must be predeclared, must not use the target result as an input, and must be included in the modeling plan before approval.
""")
    generated.append("NEGATIVE_CONTROL_SUITE_TEMPLATE/README.md")

    _write_text(out / "RELEASE_SIGNING_CHECKLIST.md", """
# Release signing checklist

Before any certification/admission execution, provide or verify:

- `FRAMEWORK_RELEASE_MANIFEST.json`
- `FRAMEWORK_RELEASE_MANIFEST.sig`
- `FRAMEWORK_RELEASE_PUBLIC_KEY.pem`
- the internal framework release ZIP named by the manifest
- release identity self-consistency via `rank3-check-release-identity`

Private signing keys must remain outside the repository and outside run packages.
""")
    generated.append("RELEASE_SIGNING_CHECKLIST.md")

    _write_text(out / "USER_APPROVAL_CHECKLIST.md", f"""
# User approval checklist

The modeling chat must return a customized packet for review before any certification run.

Approve only if:

- the contract claim is the intended claim:
{_claim_text(contract)}
- every `<...>` placeholder has been replaced or explicitly rejected;
- all proposed mechanisms are non-candidate or the contract explicitly allows them;
- all negative controls are concrete overlays;
- the path-monitor policy does not make path length change intrinsic EAS ontology;
- the initialization/settling gate is predeclared;
- the modeling plan is executable under the contract;
- the release files are signed and verified;
- `rank3-validate-operator-review-packet` reports `valid_for_user_review=true`;
- no modeling execution has already occurred.

Operator decision must be explicit: `approve`, `revise`, or `reject`.
Silence, partial agreement, and template generation are not approval.
""")
    generated.append("USER_APPROVAL_CHECKLIST.md")

    _write_text(out / "CHAT_APPROVAL_LOOP_PROTOCOL.md", """
# Required approval loop for modeling chats

This packet is not approval to run. It is a scaffold for drafting the materials that the user/operator must review.

Mandatory sequence:

1. Generate or inspect `OPERATOR_REQUIRED_ITEMS.json`.
2. Generate this operator review packet.
3. Run `rank3-customize-operator-review-packet` to produce a customized packet.
4. Draft every chat-draftable item. Do not ask the user to draft items the chat can draft.
5. Mark every non-inventable item honestly as absent/non-certification-usable.
6. Validate the customized packet with `rank3-validate-operator-review-packet`.
7. Return the customized packet and validation report to the user/operator for approval.
8. Stop and wait for an explicit user decision.
9. If the user requests changes, revise the packet, validate it again, return it again, and wait again.
10. If the user rejects it, stop certification and report rejected/non-certifying status.
11. If the user approves it, record `USER_APPROVAL_DECISION.json` binding the approved packet hash and approved plan hash.
12. Validate the approval decision with `rank3-validate-operator-review-packet --approval-decision`.
13. Begin certification modeling only after approval validation says `approved_for_modeling=true`.

Forbidden:

- Do not run before approval.
- Do not infer approval from silence.
- Do not run after a revision request until revised, revalidated, returned, and approved.
- Do not relabel candidate overlays or mechanisms as admission evidence.
- Do not make path add/remove intrinsic EAS ontology.
""")
    generated.append("CHAT_APPROVAL_LOOP_PROTOCOL.md")

    _write_json(out / "CHAT_TASKS.json", {
        "schema": "rank3_chat_operator_agent_tasks_v1",
        "mode": "certification_material_preparation_only",
        "may_execute_model_before_approval": False,
        "tasks": [
            {"step": 1, "action": "read_contract_and_required_items", "must_wait_after_step": False},
            {"step": 2, "action": "customize_review_packet", "command": "rank3-customize-operator-review-packet --review-packet-dir <this_packet> --output-dir <customized_packet>", "must_wait_after_step": False},
            {"step": 3, "action": "validate_customized_packet", "command": "rank3-validate-operator-review-packet --packet-dir <customized_packet>", "must_wait_after_step": False},
            {"step": 4, "action": "return_customized_packet_to_user", "must_wait_after_step": True},
            {"step": 5, "action": "wait_for_explicit_user_decision", "allowed_decisions": ["approve", "revise", "reject"], "must_wait_after_step": True},
            {"step": 6, "on_decision": "revise", "action": "revise_revalidate_return_and_wait_again", "must_wait_after_step": True},
            {"step": 7, "on_decision": "reject", "action": "stop_certification", "must_wait_after_step": False},
            {"step": 8, "on_decision": "approve", "action": "record_approval_decision_and_validate_hashes", "must_wait_after_step": False},
            {"step": 9, "action": "begin_modeling_only_if_approval_validation_passes", "must_wait_after_step": False}
        ],
    })
    generated.append("CHAT_TASKS.json")

    _write_text(out / "GENERATE_CUSTOMIZED_REVIEW_PACKET.sh", """
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/../CUSTOMIZED_REVIEW_PACKET}"
rank3-customize-operator-review-packet --review-packet-dir "$HERE" --output-dir "$OUT"
rank3-validate-operator-review-packet --packet-dir "$OUT" --output "$OUT/CUSTOMIZED_PACKET_VALIDATION_REPORT.json"
""")
    (out / "GENERATE_CUSTOMIZED_REVIEW_PACKET.sh").chmod(0o755)
    generated.append("GENERATE_CUSTOMIZED_REVIEW_PACKET.sh")

    _write_text(out / "CHAT_MODELING_INSTRUCTIONS.md", f"""
# Instructions for the modeling chat

You are preparing a certification/admission modeling attempt. Do not run SOO/model execution yet.

Workflow:

1. Read the modeling_intent contract.
2. Read OPERATOR_REQUIRED_ITEMS.json if supplied.
3. Run `rank3-customize-operator-review-packet` or complete the equivalent customization manually.
4. Draft every item the chat can draft: admission overlay proposals, initialization/settling gates, negative controls, path-monitor policy, and draft modeling plan.
5. Do not ask the user to draft chat-draftable items; return your proposed drafts for review.
6. For items that cannot be invented, mark them honestly as absent/non-certification-usable and explain why.
7. Replace or explicitly resolve every `<...>` placeholder.
8. Do not promote candidate overlays to admission evidence by relabeling.
9. Do not encode same/opposite orientation labels as path-edit triggers.
10. Do not make path add/remove intrinsic EAS ontology.
11. Validate the customized packet with `rank3-validate-operator-review-packet`.
12. Return the customized packet, draft plan, and validation report to the operator/user for approval.
13. Stop and wait for explicit operator/user decision.
14. If changes are required, revise the packet, validate it again, return it again, and wait again.
15. If rejected, stop and report non-certifying/rejected status.
16. If approved, record a USER_APPROVAL_DECISION.json binding the approved packet hash and approved plan hash.
17. Validate the approval decision.
18. Begin certification modeling only after approval validation reports approved_for_modeling=true.

Contract hash: `{contract.fingerprint()}`
Suite basis: `{suite_id}`

Required items currently reported:

{_items_text(req_payload)}
""")
    generated.append("CHAT_MODELING_INSTRUCTIONS.md")

    if req_payload is not None:
        _write_json(out / "SOURCE_OPERATOR_REQUIRED_ITEMS.json", req_payload)
        generated.append("SOURCE_OPERATOR_REQUIRED_ITEMS.json")
    if synth_payload is not None:
        _write_json(out / "SOURCE_OVERLAY_SYNTHESIS_REPORT.json", synth_payload)
        generated.append("SOURCE_OVERLAY_SYNTHESIS_REPORT.json")

    manifest = OperatorReviewPacketManifest(
        packet_schema=PACKET_SCHEMA,
        generated_utc=_now_utc(),
        modeling_intent=contract.modeling_intent,
        contract_hash=contract.fingerprint(),
        contract_path=str(contract_path),
        operator_required_items_path=str(Path(operator_required_items_path).expanduser().resolve()) if operator_required_items_path else None,
        synthesis_report_path=str(Path(synthesis_report_path).expanduser().resolve()) if synthesis_report_path else None,
        suite_id=suite_id,
        output_dir=str(out),
        purpose="Generate customized operator-review artifacts before certification/admission model execution.",
        workflow_status="draft_templates_for_modeling_chat_customization",
        requires_user_approval_before_modeling=True,
        generated_files=tuple(sorted(generated + ["OPERATOR_REVIEW_PACKET_MANIFEST.json", "OPERATOR_REVIEW_PACKET_MANIFEST.sha256"])),
        source_hashes=source_hashes,
        notes=notes,
    )
    _write_json(out / "OPERATOR_REVIEW_PACKET_MANIFEST.json", manifest.to_dict())
    (out / "OPERATOR_REVIEW_PACKET_MANIFEST.sha256").write_text(manifest.fingerprint() + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an operator review packet from a contract and operator-required-items report. This does not run the model.")
    parser.add_argument("--contract", required=True, help="Path to modeling_intent contract JSON")
    parser.add_argument("--operator-required-items", help="Path to OPERATOR_REQUIRED_ITEMS.json")
    parser.add_argument("--synthesis-report", help="Path to OVERLAY_SYNTHESIS_REPORT.json")
    parser.add_argument("--suite-id", choices=sorted(BUILTIN_SUITES.keys()), default=None)
    parser.add_argument("--output-dir", required=True, help="Directory to write the review packet")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    manifest = generate_operator_review_packet(
        contract_path=args.contract,
        operator_required_items_path=args.operator_required_items,
        synthesis_report_path=args.synthesis_report,
        suite_id=args.suite_id,
        output_dir=args.output_dir,
        notes=args.notes,
    )
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
