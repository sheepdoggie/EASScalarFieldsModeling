from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from .fingerprints import stable_json_hash

WORKFLOW_PROTOCOL_REPORT_SCHEMA = "rank3_workflow_protocol_validation_report_v1"
DEFAULT_APPROVAL_LOOP_PROTOCOL_ID = "certification_operator_agent_approval_loop_v1"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _protocol_resource_path(protocol_id: str) -> Any:
    return resources.files("rank3_enforced").joinpath("protocols", f"{protocol_id}.json")


def load_workflow_protocol(protocol_id: str = DEFAULT_APPROVAL_LOOP_PROTOCOL_ID) -> dict[str, Any]:
    path = _protocol_resource_path(protocol_id)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"workflow protocol not found: {protocol_id}") from exc
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"workflow protocol must be a JSON object: {protocol_id}")
    return payload


def protocol_fingerprint(payload: dict[str, Any]) -> str:
    return stable_json_hash(payload)


def compute_workflow_protocols_sha256(protocol_ids: tuple[str, ...] = (DEFAULT_APPROVAL_LOOP_PROTOCOL_ID,)) -> str:
    entries: list[tuple[str, str]] = []
    for pid in protocol_ids:
        payload = load_workflow_protocol(pid)
        entries.append((pid, protocol_fingerprint(payload)))
    return stable_json_hash(tuple(sorted(entries)))


@dataclass(frozen=True)
class WorkflowProtocolValidationReport:
    schema: str
    generated_utc: str
    protocol_id: str | None
    protocol_version: str | None
    protocol_sha256: str | None
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    mandatory_sequence_ids: tuple[str, ...]
    forbidden_behaviors: tuple[str, ...]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_REQUIRED_TOP_LEVEL = (
    "schema",
    "protocol_id",
    "protocol_version",
    "mandatory_sequence",
    "forbidden_behaviors",
    "approval_decision_requirements",
)

_REQUIRED_FORBIDDEN = (
    "run_before_explicit_approval",
    "treat_silence_as_approval",
    "run_after_revision_request_without_revision_revalidation_and_reapproval",
    "promote_candidate_overlay_by_label_change",
    "make_path_add_remove_intrinsic_framework_rule",
)

_REQUIRED_SEQUENCE_IDS = (
    "draft_chat_draftable_items",
    "mark_non_inventable_items",
    "validate_customized_packet_for_review",
    "return_to_user_for_approval",
    "wait_for_explicit_decision",
    "handle_revision_request",
    "record_approval_decision",
    "validate_approval_decision",
    "execute_only_after_approval_gate",
)


def validate_workflow_protocol_payload(payload: dict[str, Any]) -> WorkflowProtocolValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    for key in _REQUIRED_TOP_LEVEL:
        if key not in payload:
            errors.append(f"missing top-level field: {key}")
    if payload.get("schema") != "rank3_workflow_protocol_v1":
        errors.append("schema must be rank3_workflow_protocol_v1")
    protocol_id = payload.get("protocol_id")
    protocol_version = payload.get("protocol_version")
    seq = payload.get("mandatory_sequence", [])
    if not isinstance(seq, list) or not seq:
        errors.append("mandatory_sequence must be a non-empty list")
        seq_ids: tuple[str, ...] = tuple()
    else:
        seq_ids = tuple(str(step.get("id", "")) for step in seq if isinstance(step, dict))
        for req_id in _REQUIRED_SEQUENCE_IDS:
            if req_id not in seq_ids:
                errors.append(f"mandatory_sequence missing required step id: {req_id}")
        step_nums = [step.get("step") for step in seq if isinstance(step, dict)]
        if step_nums != sorted(step_nums):
            errors.append("mandatory_sequence steps must be sorted by step number")
        for step in seq:
            if not isinstance(step, dict):
                errors.append("mandatory_sequence contains non-object step")
                continue
            if step.get("id") in {"return_to_user_for_approval", "wait_for_explicit_decision"} and not step.get("must_wait_after_step"):
                errors.append(f"step {step.get('id')} must set must_wait_after_step=true")
            if step.get("id") != "execute_only_after_approval_gate" and step.get("may_execute_model_after_step") is True:
                errors.append(f"step {step.get('id')} may not allow model execution")
    forbidden = payload.get("forbidden_behaviors", [])
    if not isinstance(forbidden, list):
        errors.append("forbidden_behaviors must be a list")
        forbidden_t = tuple()
    else:
        forbidden_t = tuple(str(x) for x in forbidden)
        for req in _REQUIRED_FORBIDDEN:
            if req not in forbidden_t:
                errors.append(f"forbidden_behaviors missing required rule: {req}")
    approval = payload.get("approval_decision_requirements", {})
    if not isinstance(approval, dict):
        errors.append("approval_decision_requirements must be an object")
    else:
        allowed = set(str(x) for x in approval.get("allowed_decisions", []))
        if allowed != {"approve", "revise", "reject"}:
            errors.append("approval_decision_requirements.allowed_decisions must be exactly approve/revise/reject")
        if approval.get("approve_requires_packet_hash") is not True:
            errors.append("approval must require approved packet hash")
        if approval.get("approve_requires_plan_hash") is not True:
            errors.append("approval must require approved plan hash")
        if approval.get("revise_requires_revalidation_before_return") is not True:
            errors.append("revision must require revalidation before return")
    authority = payload.get("authority", {})
    if isinstance(authority, dict):
        if authority.get("protocol_controls_chat_workflow_not_eas_ontology") is not True:
            errors.append("protocol must state it controls workflow, not EAS ontology")
        if authority.get("path_add_remove_is_not_intrinsic_eas_ontology") is not True:
            errors.append("protocol must state path add/remove is not intrinsic EAS ontology")
    else:
        warnings.append("authority object missing or malformed")
    valid = not errors
    return WorkflowProtocolValidationReport(
        schema=WORKFLOW_PROTOCOL_REPORT_SCHEMA,
        generated_utc=_now_utc(),
        protocol_id=str(protocol_id) if protocol_id is not None else None,
        protocol_version=str(protocol_version) if protocol_version is not None else None,
        protocol_sha256=protocol_fingerprint(payload) if isinstance(payload, dict) else None,
        valid=valid,
        errors=tuple(errors),
        warnings=tuple(warnings),
        mandatory_sequence_ids=seq_ids,
        forbidden_behaviors=forbidden_t,
        next_action="protocol_valid_for_operator_agent_generation" if valid else "repair_protocol_before_generating_operator_agent_instructions",
    )


def validate_workflow_protocol(protocol_id: str = DEFAULT_APPROVAL_LOOP_PROTOCOL_ID) -> WorkflowProtocolValidationReport:
    return validate_workflow_protocol_payload(load_workflow_protocol(protocol_id))


def protocol_sequence_markdown(payload: dict[str, Any]) -> str:
    lines = ["Mandatory sequence:", ""]
    for step in payload.get("mandatory_sequence", []):
        if not isinstance(step, dict):
            continue
        lines.append(f"{step.get('step')}. **{step.get('id')}** — {step.get('action')}")
        if step.get("must_wait_after_step"):
            lines.append("   - Stop and wait; do not model after this step.")
        if step.get("loops_to_step"):
            lines.append(f"   - Revision loop returns to step {step.get('loops_to_step')}.")
    lines.extend(["", "Forbidden behavior:", ""])
    for rule in payload.get("forbidden_behaviors", []):
        lines.append(f"- `{rule}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a data-driven workflow protocol used by the operator-agent layer.")
    parser.add_argument("--protocol-id", default=DEFAULT_APPROVAL_LOOP_PROTOCOL_ID)
    parser.add_argument("--protocol-file", default=None, help="Validate an explicit JSON file instead of an installed protocol id.")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    if args.protocol_file:
        report = validate_workflow_protocol_payload(_read_json(args.protocol_file))
    else:
        report = validate_workflow_protocol(args.protocol_id)
    payload = report.to_dict()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        _write_json(args.output, payload)
    print(text, end="")
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
