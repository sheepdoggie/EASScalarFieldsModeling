from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fingerprints import file_hash, stable_json_hash
from .modeling_intent import contract_from_file
from .workflow_protocols import (
    DEFAULT_APPROVAL_LOOP_PROTOCOL_ID,
    load_workflow_protocol,
    protocol_fingerprint,
    protocol_sequence_markdown,
    validate_workflow_protocol_payload,
)

CUSTOMIZED_PACKET_SCHEMA = "rank3_operator_agent_customized_review_packet_v1"
CUSTOMIZED_VALIDATION_SCHEMA = "rank3_operator_agent_customized_packet_validation_v1"
APPROVAL_DECISION_SCHEMA = "rank3_operator_agent_user_approval_decision_v1"

_PLACEHOLDER_RE = re.compile(r"<[^>]+>")


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


def _write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _packet_hash(output_dir: str | Path) -> str:
    output_dir = Path(output_dir)
    entries: list[tuple[str, str]] = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {"CUSTOMIZED_REVIEW_PACKET.sha256"}:
            entries.append((str(path.relative_to(output_dir)), file_hash(path)))
    return stable_json_hash(entries)


def _replace_placeholders(obj: Any, *, context: str = "") -> Any:
    """Replace raw <...> placeholders with explicit non-invented review entries.

    This is intentionally conservative. It prevents a modeling chat from leaving
    ambiguous template holes while also preventing the framework from fabricating
    non-candidate evidence.
    """
    if isinstance(obj, dict):
        return {k: _replace_placeholders(v, context=f"{context}.{k}" if context else str(k)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_placeholders(v, context=f"{context}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, str):
        if _PLACEHOLDER_RE.search(obj):
            return {
                "draft_status": "requires_modeling_chat_completion_or_explicit_absent_mark",
                "original_placeholder_label": _PLACEHOLDER_RE.sub(lambda m: m.group(0).strip("<>"), obj),
                "context": context,
                "certification_usable": False,
                "user_review_required": True,
                "instruction": (
                    "Replace this entry with a concrete proposal if it can be drafted from the contract and framework. "
                    "If it cannot be honestly supplied, set status='absent_or_non_inventable' and explain why certification cannot use it."
                ),
            }
        return obj
    return obj


@dataclass(frozen=True)
class CustomizedPacketManifest:
    schema: str
    generated_utc: str
    source_review_packet_dir: str
    output_dir: str
    prepared_by: str
    contract_path: str | None
    contract_hash: str | None
    operator_required_items_path: str | None
    source_packet_manifest_hash: str | None
    workflow_protocol_id: str | None
    workflow_protocol_sha256: str | None
    workflow_phase: str
    valid_for_user_review_only: bool
    executable_for_certification: bool
    requires_explicit_user_approval_before_modeling: bool
    generated_files: tuple[str, ...]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class CustomizedPacketValidationReport:
    schema: str
    generated_utc: str
    packet_dir: str
    structurally_valid: bool
    valid_for_user_review: bool
    approved_for_modeling: bool
    executable_for_certification: bool
    packet_sha256: str | None
    approval_decision_path: str | None
    approval_decision: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    required_next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_optional(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return _read_json(path)
    return None


def _classify_required_items(req_payload: dict[str, Any] | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw in (req_payload or {}).get("items", []) or []:
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category", "unknown"))
        item_id = str(raw.get("item_id", "unknown"))
        if category in {"release_guard"}:
            agent_action = "operator_must_supply_or_sign"
        elif item_id in {"non_candidate_mechanism_evidence"} or category == "mechanism_status":
            agent_action = "cannot_be_invented_mark_absent_unless_framework_evidence_exists"
        elif category in {"overlay_status", "initialization", "controls", "path_monitor", "planning"}:
            agent_action = "modeling_chat_must_draft_for_user_approval"
        elif category == "contract":
            agent_action = "operator_must_supply_contract"
        else:
            agent_action = "modeling_chat_must_classify_and_draft_or_mark_absent"
        rows.append({
            "item_id": item_id,
            "category": category,
            "severity": raw.get("severity"),
            "agent_action": agent_action,
            "blocks_certification_execution": bool(raw.get("blocks_certification_execution", True)),
            "prompt": raw.get("prompt"),
            "reason": raw.get("reason"),
            "acceptable_forms": raw.get("acceptable_forms", []),
            "customization_required": True,
            "user_approval_required": True,
        })
    return {
        "schema": "rank3_operator_agent_customization_decision_table_v1",
        "generated_utc": _now_utc(),
        "rows": rows,
        "rule": (
            "Draft all chat-draftable items. Do not ask the user to draft them. "
            "Mark non-inventable items honestly. Return the customized packet for approval."
        ),
    }


def _approval_loop_protocol(protocol_id: str = DEFAULT_APPROVAL_LOOP_PROTOCOL_ID) -> dict[str, Any]:
    """Load the operator-agent approval loop from a data protocol file.

    Small workflow changes now belong in ``rank3_enforced/protocols/*.json``.
    Python code only validates and renders the protocol; it should not be the
    primary place where approval-loop wording or sequencing is maintained.
    """
    payload = load_workflow_protocol(protocol_id)
    report = validate_workflow_protocol_payload(payload)
    if not report.valid:
        raise RuntimeError("invalid workflow protocol: " + "; ".join(report.errors))
    return payload


def _workflow_protocol_metadata(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": protocol.get("protocol_id"),
        "protocol_version": protocol.get("protocol_version"),
        "protocol_sha256": protocol_fingerprint(protocol),
        "protocol_schema": protocol.get("schema"),
        "protocol_status": protocol.get("status"),
    }


def _workflow_protocol_markdown(protocol: dict[str, Any]) -> str:
    return protocol_sequence_markdown(protocol)


def generate_customized_review_packet(
    *,
    review_packet_dir: str | Path,
    output_dir: str | Path,
    prepared_by: str = "modeling_chat",
    contract_path: str | Path | None = None,
    notes: str = "",
) -> CustomizedPacketManifest:
    src = Path(review_packet_dir).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"review packet directory not found: {src}")

    source_manifest = _load_optional(src / "OPERATOR_REVIEW_PACKET_MANIFEST.json")
    req_payload = _load_optional(src / "SOURCE_OPERATOR_REQUIRED_ITEMS.json")
    if req_payload is None and (src / "OPERATOR_REQUIRED_ITEMS.json").exists():
        req_payload = _load_optional(src / "OPERATOR_REQUIRED_ITEMS.json")

    contract_hash: str | None = None
    resolved_contract_path: str | None = None
    if contract_path is not None:
        cp = Path(contract_path).expanduser().resolve()
        contract_hash = contract_from_file(cp).fingerprint()
        resolved_contract_path = str(cp)
    elif source_manifest and source_manifest.get("contract_hash"):
        contract_hash = str(source_manifest.get("contract_hash"))
        resolved_contract_path = source_manifest.get("contract_path")

    generated: list[str] = []
    # Copy source templates into a trace directory and write customized versions next to them.
    for name in [
        "ADMISSION_OVERLAY_TEMPLATE.json",
        "MECHANISM_STATUS_DECLARATION_TEMPLATE.json",
        "INITIALIZATION_SETTLING_REQUIREMENTS_TEMPLATE.json",
        "PATH_MONITOR_POLICY_TEMPLATE.json",
        "MODELING_PLAN_APPROVAL_REQUEST_TEMPLATE.json",
    ]:
        p = src / name
        if p.exists():
            payload = _read_json(p)
            custom = _replace_placeholders(payload)
            custom["customized_packet_status"] = "drafted_for_user_review_not_approved"
            custom["approval_required_before_modeling"] = True
            _write_json(out / name.replace("_TEMPLATE", "_PROPOSED"), custom)
            generated.append(name.replace("_TEMPLATE", "_PROPOSED"))
    neg = src / "NEGATIVE_CONTROL_SUITE_TEMPLATE" / "negative_control_overlay_template.json"
    if neg.exists():
        custom = _replace_placeholders(_read_json(neg))
        custom["customized_packet_status"] = "drafted_for_user_review_not_approved"
        custom["approval_required_before_modeling"] = True
        _write_json(out / "NEGATIVE_CONTROL_SUITE_PROPOSED" / "negative_control_overlay_proposed.json", custom)
        generated.append("NEGATIVE_CONTROL_SUITE_PROPOSED/negative_control_overlay_proposed.json")

    decision_table = _classify_required_items(req_payload)
    _write_json(out / "CUSTOMIZATION_DECISION_TABLE.json", decision_table)
    generated.append("CUSTOMIZATION_DECISION_TABLE.json")

    protocol = _approval_loop_protocol()
    protocol_meta = _workflow_protocol_metadata(protocol)
    _write_json(out / "APPROVAL_LOOP_PROTOCOL.json", protocol)
    generated.append("APPROVAL_LOOP_PROTOCOL.json")
    _write_json(out / "WORKFLOW_PROTOCOL_METADATA.json", protocol_meta)
    generated.append("WORKFLOW_PROTOCOL_METADATA.json")

    _write_json(out / "USER_APPROVAL_DECISION_TEMPLATE.json", {
        "schema": APPROVAL_DECISION_SCHEMA,
        "decision": "<approve|revise|reject>",
        "approval_scope": "customized_review_packet_and_exact_modeling_plan",
        "approved_packet_sha256": "<fill-after-validation>",
        "approved_plan_sha256": "<required-for-certification-execution>",
        "revision_requests": [],
        "approval_notes": "",
        "hard_rule": "Certification modeling may not begin unless decision='approve' and hashes match the validation report.",
    })
    generated.append("USER_APPROVAL_DECISION_TEMPLATE.json")

    _write_text(out / "CHAT_AGENT_WORKFLOW.md", f"""
# Modeling-chat approval workflow

You are acting as a modeling agent, not as the final approving operator.

Protocol source: `{protocol_meta.get('protocol_id')}`
Protocol version: `{protocol_meta.get('protocol_version')}`
Protocol SHA-256: `{protocol_meta.get('protocol_sha256')}`

{_workflow_protocol_markdown(protocol)}

Operational rule: if the user requests changes, revise the packet, validate it again, return it again, and wait again. Certification modeling may begin only after an explicit approve decision binds the current packet hash and approved plan hash.
""")
    generated.append("CHAT_AGENT_WORKFLOW.md")

    _write_text(out / "VALIDATE_AND_RETURN_FOR_APPROVAL.sh", """
#!/usr/bin/env bash
set -euo pipefail
rank3-validate-operator-review-packet --packet-dir "$(dirname "$0")" --output "$(dirname "$0")/CUSTOMIZED_PACKET_VALIDATION_REPORT.json"
""")
    (out / "VALIDATE_AND_RETURN_FOR_APPROVAL.sh").chmod(0o755)
    generated.append("VALIDATE_AND_RETURN_FOR_APPROVAL.sh")

    manifest = CustomizedPacketManifest(
        schema=CUSTOMIZED_PACKET_SCHEMA,
        generated_utc=_now_utc(),
        source_review_packet_dir=str(src),
        output_dir=str(out),
        prepared_by=prepared_by,
        contract_path=resolved_contract_path,
        contract_hash=contract_hash,
        operator_required_items_path=str(src / "SOURCE_OPERATOR_REQUIRED_ITEMS.json") if (src / "SOURCE_OPERATOR_REQUIRED_ITEMS.json").exists() else None,
        source_packet_manifest_hash=file_hash(src / "OPERATOR_REVIEW_PACKET_MANIFEST.json") if (src / "OPERATOR_REVIEW_PACKET_MANIFEST.json").exists() else None,
        workflow_protocol_id=str(protocol_meta.get("protocol_id")) if protocol_meta.get("protocol_id") is not None else None,
        workflow_protocol_sha256=str(protocol_meta.get("protocol_sha256")) if protocol_meta.get("protocol_sha256") is not None else None,
        workflow_phase="customized_packet_drafted_for_user_review_waiting_for_approval",
        valid_for_user_review_only=True,
        executable_for_certification=False,
        requires_explicit_user_approval_before_modeling=True,
        generated_files=tuple(sorted(generated + ["CUSTOMIZED_REVIEW_PACKET_MANIFEST.json", "CUSTOMIZED_REVIEW_PACKET.sha256"])),
        notes=notes,
    )
    _write_json(out / "CUSTOMIZED_REVIEW_PACKET_MANIFEST.json", manifest.to_dict())
    h = _packet_hash(out)
    (out / "CUSTOMIZED_REVIEW_PACKET.sha256").write_text(h + "\n", encoding="utf-8")
    return manifest


def validate_customized_review_packet(
    *,
    packet_dir: str | Path,
    approval_decision_path: str | Path | None = None,
    output: str | Path | None = None,
) -> CustomizedPacketValidationReport:
    packet_dir = Path(packet_dir).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if not packet_dir.exists():
        errors.append(f"packet directory missing: {packet_dir}")
    manifest_path = packet_dir / "CUSTOMIZED_REVIEW_PACKET_MANIFEST.json"
    if not manifest_path.exists():
        errors.append("CUSTOMIZED_REVIEW_PACKET_MANIFEST.json missing")
        manifest = None
    else:
        manifest = _read_json(manifest_path)
    protocol = packet_dir / "APPROVAL_LOOP_PROTOCOL.json"
    if not protocol.exists():
        errors.append("APPROVAL_LOOP_PROTOCOL.json missing")
    tasks = packet_dir / "CHAT_AGENT_WORKFLOW.md"
    if not tasks.exists():
        errors.append("CHAT_AGENT_WORKFLOW.md missing")

    # Raw placeholders are allowed only in the approval decision template; all proposed JSON should be explicit.
    placeholder_files: list[str] = []
    for p in packet_dir.rglob("*.json"):
        if p.name in {"USER_APPROVAL_DECISION_TEMPLATE.json"}:
            continue
        text = p.read_text(encoding="utf-8")
        if _PLACEHOLDER_RE.search(text):
            placeholder_files.append(str(p.relative_to(packet_dir)))
    if placeholder_files:
        errors.append("customized packet still contains raw <...> placeholders: " + ", ".join(placeholder_files))

    packet_sha = _packet_hash(packet_dir) if packet_dir.exists() else None
    approval_decision: str | None = None
    approved_for_modeling = False
    executable = False
    approval_path_s: str | None = None
    if approval_decision_path is not None:
        approval_path = Path(approval_decision_path).expanduser().resolve()
        approval_path_s = str(approval_path)
        if not approval_path.exists():
            errors.append(f"approval decision file missing: {approval_path}")
        else:
            decision = _read_json(approval_path)
            approval_decision = str(decision.get("decision"))
            if decision.get("schema") != APPROVAL_DECISION_SCHEMA:
                errors.append("approval decision schema mismatch")
            if approval_decision == "approve":
                if decision.get("approved_packet_sha256") != packet_sha:
                    errors.append("approval decision does not bind the current packet hash")
                if not decision.get("approved_plan_sha256") or str(decision.get("approved_plan_sha256")).startswith("<"):
                    errors.append("approval decision must bind an approved modeling plan hash")
                if not errors:
                    approved_for_modeling = True
                    executable = True
            elif approval_decision == "revise":
                errors.append("user requested revision; revise, revalidate, and return for approval before modeling")
            elif approval_decision == "reject":
                errors.append("user rejected packet; certification modeling must stop")
            else:
                errors.append("approval decision must be one of approve, revise, reject")
    else:
        warnings.append("No approval decision supplied; packet is valid only for user review, not execution.")

    structurally_valid = not [e for e in errors if "approval decision" not in e and "user requested" not in e and "user rejected" not in e]
    valid_for_review = structurally_valid and manifest is not None
    if approval_decision_path is None:
        next_action = "return_customized_packet_to_user_and_wait_for_explicit_approval"
    elif approval_decision == "revise":
        next_action = "revise_packet_revalidate_return_for_approval_wait_again"
    elif approval_decision == "reject":
        next_action = "stop_certification_report_rejected_or_non_certifying"
    elif approved_for_modeling:
        next_action = "certification_modeling_may_begin_subject_to_release_guard_and_contract_gates"
    else:
        next_action = "repair_approval_or_packet_then_revalidate_before_modeling"

    report = CustomizedPacketValidationReport(
        schema=CUSTOMIZED_VALIDATION_SCHEMA,
        generated_utc=_now_utc(),
        packet_dir=str(packet_dir),
        structurally_valid=structurally_valid,
        valid_for_user_review=valid_for_review,
        approved_for_modeling=approved_for_modeling,
        executable_for_certification=executable,
        packet_sha256=packet_sha,
        approval_decision_path=approval_path_s,
        approval_decision=approval_decision,
        errors=tuple(errors),
        warnings=tuple(warnings),
        required_next_action=next_action,
    )
    if output is not None:
        _write_json(output, report.to_dict())
    return report


def main_customize(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Customize an operator review packet into a modeling-chat draft for user approval. This does not run the model.")
    parser.add_argument("--review-packet-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prepared-by", default="modeling_chat")
    parser.add_argument("--contract", default=None)
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    manifest = generate_customized_review_packet(
        review_packet_dir=args.review_packet_dir,
        output_dir=args.output_dir,
        prepared_by=args.prepared_by,
        contract_path=args.contract,
        notes=args.notes,
    )
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0


def main_validate(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a customized operator review packet and optional user approval decision. This does not run the model.")
    parser.add_argument("--packet-dir", required=True)
    parser.add_argument("--approval-decision", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    report = validate_customized_review_packet(
        packet_dir=args.packet_dir,
        approval_decision_path=args.approval_decision,
        output=args.output,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if (report.valid_for_user_review and (args.approval_decision is None or report.approved_for_modeling)) else 1


if __name__ == "__main__":
    raise SystemExit(main_customize())
