from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .fingerprints import file_hash, stable_json_hash
from .modeling_intent import ModelingIntentContract, contract_from_file, validate_contract_for_overlay

SYNTHESIS_SCHEMA = "rank3_contract_overlay_synthesis_report_v1"
OPERATOR_REQUIREMENTS_SCHEMA = "rank3_operator_required_items_report_v2"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object overlay: {path}")
    return payload


def _write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class OperatorRequiredItem:
    item_id: str
    severity: str
    category: str
    required_from_operator: bool
    prompt: str
    reason: str
    acceptable_forms: tuple[str, ...] = ()
    blocks_certification_execution: bool = True
    generator: str | None = None
    generator_args: tuple[str, ...] = ()
    review_artifacts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SynthesisCaseProposal:
    case_id: str
    source_overlay_path: str
    source_overlay_sha256: str
    synthesized_overlay_path: str | None
    synthesis_status: str
    auto_synthesized: bool
    certification_eligible_after_synthesis: bool
    compliance_violations: tuple[str, ...]
    operator_required_items: tuple[OperatorRequiredItem, ...]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OverlaySynthesisReport:
    schema: str
    generated_utc: str
    modeling_intent: str
    contract_hash: str
    synthesis_mode: str
    suite_id: str | None
    source_overlay_count: int
    synthesized_overlay_count: int
    blocked_case_count: int
    certification_eligible_case_count: int
    operator_required_item_count: int
    can_build_certification_plan: bool
    operator_action_required: bool
    global_operator_required_items: tuple[OperatorRequiredItem, ...]
    cases: tuple[SynthesisCaseProposal, ...]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class OperatorRequiredItemsReport:
    schema: str
    generated_utc: str
    context: str
    modeling_intent: str | None
    contract_hash: str | None
    requested_mode: str | None
    approved_plan_path: str | None
    output_root: str | None
    items: tuple[OperatorRequiredItem, ...]
    blocks_certification_execution: bool
    recommended_generator_command: str | None = None
    recommended_generator_outputs: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())



def operator_review_packet_outputs() -> tuple[str, ...]:
    return (
        "OPERATOR_REVIEW_PACKET_MANIFEST.json",
        "CHAT_MODELING_INSTRUCTIONS.md",
        "ADMISSION_OVERLAY_TEMPLATE.json",
        "MECHANISM_STATUS_DECLARATION_TEMPLATE.json",
        "INITIALIZATION_SETTLING_REQUIREMENTS_TEMPLATE.json",
        "NEGATIVE_CONTROL_SUITE_TEMPLATE/README.md",
        "NEGATIVE_CONTROL_SUITE_TEMPLATE/negative_control_overlay_template.json",
        "PATH_MONITOR_POLICY_TEMPLATE.json",
        "MODELING_PLAN_APPROVAL_REQUEST_TEMPLATE.json",
        "RELEASE_SIGNING_CHECKLIST.md",
        "USER_APPROVAL_CHECKLIST.md",
    )


def recommended_operator_review_packet_command(
    *,
    contract_path: str | Path | None = None,
    operator_required_items_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    suite_id: str | None = None,
) -> str:
    parts = ["rank3-generate-operator-review-packet"]
    if contract_path is not None:
        parts += ["--contract", str(contract_path)]
    else:
        parts += ["--contract", "<path/to/modeling_intent_contract.json>"]
    if operator_required_items_path is not None:
        parts += ["--operator-required-items", str(operator_required_items_path)]
    else:
        parts += ["--operator-required-items", "<path/to/OPERATOR_REQUIRED_ITEMS.json>"]
    if suite_id is not None:
        parts += ["--suite-id", suite_id]
    if output_dir is not None:
        parts += ["--output-dir", str(output_dir)]
    else:
        parts += ["--output-dir", "<path/to/OPERATOR_REVIEW_PACKET>"]
    return " ".join(parts)


def _with_generator(item: OperatorRequiredItem, *args: str) -> OperatorRequiredItem:
    return OperatorRequiredItem(
        item_id=item.item_id,
        severity=item.severity,
        category=item.category,
        required_from_operator=item.required_from_operator,
        prompt=item.prompt,
        reason=item.reason,
        acceptable_forms=item.acceptable_forms,
        blocks_certification_execution=item.blocks_certification_execution,
        generator="rank3-generate-operator-review-packet",
        generator_args=tuple(args),
        review_artifacts=operator_review_packet_outputs(),
    )


def _base_operator_items(contract: ModelingIntentContract) -> list[OperatorRequiredItem]:
    items: list[OperatorRequiredItem] = []
    if contract.mode == "certification":
        items.extend([
            OperatorRequiredItem(
                item_id="admission_overlay_specification",
                severity="blocking",
                category="overlay_status",
                required_from_operator=True,
                prompt=(
                    "Provide overlays explicitly marked run_kind='admission' and "
                    "requested_certification=true, or approve a synthesized plan whose cases "
                    "already satisfy those fields without candidate promotion."
                ),
                reason="Certification mode cannot execute candidate overlays as admission evidence.",
                acceptable_forms=("JSON overlay files", "approved generated overlay suite"),
            ),
            OperatorRequiredItem(
                item_id="non_candidate_mechanism_evidence",
                severity="blocking",
                category="mechanism_status",
                required_from_operator=True,
                prompt=(
                    "Identify the non-candidate scalar update, remap, readout, initialization, "
                    "and admission-verdict mechanisms to use for the certification attempt."
                ),
                reason="The contract forbids candidate-rule certification unless explicitly allowed.",
                acceptable_forms=("registered admitted rule IDs", "contract amendment allowing candidate status", "explicit non-certifying downgrade"),
            ),
            OperatorRequiredItem(
                item_id="initialization_settling_requirements",
                severity="blocking",
                category="initialization",
                required_from_operator=True,
                prompt=(
                    "Provide initialization/settling parameters and witness/readout requirements "
                    "that meet the contract before the diagnostic measurement phase begins."
                ),
                reason="The contract requires steady/recurrent initialization evidence.",
                acceptable_forms=("initialization block", "settling gate block", "witness set declaration"),
            ),
            OperatorRequiredItem(
                item_id="negative_control_suite",
                severity="blocking",
                category="controls",
                required_from_operator=True,
                prompt="Provide concrete negative-control overlays required by the modeling_intent contract.",
                reason="Certification requires controls; a theorem-target suite without controls is not admission-capable.",
                acceptable_forms=("overlay JSON controls", "control suite directory", "contract amendment"),
            ),
            OperatorRequiredItem(
                item_id="path_edit_monitor_policy",
                severity="blocking",
                category="path_monitor",
                required_from_operator=True,
                prompt=(
                    "Specify whether path add/remove monitors are absent, exploratory-only, or "
                    "contract-admitted. If present, provide the external monitor request/logging policy."
                ),
                reason="Path add/remove is not intrinsic EAS ontology and cannot be hidden in framework rules.",
                acceptable_forms=("no-path-edit declaration", "external monitor config", "operator-approved exploratory downgrade"),
            ),
        ])
    return items


def _items_from_compliance(violations: Sequence[str]) -> tuple[OperatorRequiredItem, ...]:
    items: list[OperatorRequiredItem] = []
    text = "\n".join(violations)
    if "run_kind='admission'" in text or "requested_certification=true" in text:
        items.append(OperatorRequiredItem(
            item_id="overlay_admission_flags",
            severity="blocking",
            category="overlay_status",
            required_from_operator=True,
            prompt="Provide or approve overlays with run_kind='admission' and requested_certification=true.",
            reason="The selected overlay is not marked as a certification/admission run.",
            acceptable_forms=("edited overlay", "new overlay", "synthesized overlay approved by operator"),
        ))
    if "candidate" in text:
        items.append(OperatorRequiredItem(
            item_id="candidate_rule_replacement_or_contract_amendment",
            severity="blocking",
            category="mechanism_status",
            required_from_operator=True,
            prompt="Replace candidate mechanisms with admitted mechanisms, or amend the contract to allow candidate rules as non-certifying evidence.",
            reason="The supplied contract forbids candidate-rule certification.",
            acceptable_forms=("admitted rule ID", "updated contract", "exploratory-mode rerun"),
        ))
    if "path construction" in text or "support-to-support" in text:
        items.append(OperatorRequiredItem(
            item_id="support_to_support_path_construction",
            severity="blocking",
            category="path_construction",
            required_from_operator=True,
            prompt="Provide a declared support-to-support relational path construction allowed by the contract.",
            reason="The contract target requires declared relational paths.",
            acceptable_forms=("role_path_two_support_v0_1", "linear_support_path_v0_2", "new registered admitted construction"),
        ))
    if not items:
        items.append(OperatorRequiredItem(
            item_id="contract_compliance_repair",
            severity="blocking",
            category="contract_compliance",
            required_from_operator=True,
            prompt="Repair the overlay so it satisfies the modeling_intent compliance report before certification execution.",
            reason="The selected overlay failed contract compliance.",
            acceptable_forms=("updated overlay JSON", "updated contract", "exploratory-mode downgrade"),
        ))
    return tuple(items)


def _candidate_like(payload: dict[str, Any]) -> bool:
    haystack = json.dumps(payload, sort_keys=True).lower()
    return "candidate" in haystack


def _attempt_safe_overlay_synthesis(
    *,
    payload: dict[str, Any],
    contract: ModelingIntentContract,
    allow_candidate_promotion: bool,
) -> tuple[dict[str, Any] | None, tuple[OperatorRequiredItem, ...], str]:
    """Return a synthesized overlay only when doing so is not a scientific promotion.

    The function intentionally refuses to convert candidate overlays into admission overlays
    unless the operator explicitly allowed candidate promotion. Even when allowed, candidate
    promotion does not create certification eligibility unless the contract allows candidate
    rules; otherwise the resulting overlay will still be rejected by compliance validation.
    """
    if contract.mode != "certification":
        out = dict(payload)
        out["modeling_intent"] = contract.to_dict()
        out["synthesis"] = {
            "synthesis_schema": SYNTHESIS_SCHEMA,
            "synthesis_status": "exploratory_overlay_staged",
            "candidate_promotion_performed": False,
        }
        return out, (), "synthesized_exploratory_staging"
    if _candidate_like(payload) and not allow_candidate_promotion:
        return None, (
            OperatorRequiredItem(
                item_id="candidate_overlay_not_auto_promoted",
                severity="blocking",
                category="anti_leakage",
                required_from_operator=True,
                prompt=(
                    "Supply an independently authored admission overlay or explicitly approve a "
                    "non-certifying candidate-to-admission experiment. The synthesizer will not "
                    "turn candidate overlays into admission overlays automatically."
                ),
                reason="Automatic promotion of a candidate overlay would be label-based certification leakage.",
                acceptable_forms=("operator-authored admission overlay", "exploratory-mode run", "contract amendment"),
            ),
        ), "blocked_candidate_not_promoted"
    out = dict(payload)
    out["modeling_intent"] = contract.to_dict()
    out["run_kind"] = "admission"
    out["requested_certification"] = True
    out.setdefault("controls", [])
    out.setdefault("synthesis", {})
    out["synthesis"] = {
        "synthesis_schema": SYNTHESIS_SCHEMA,
        "synthesis_status": "operator_review_required",
        "candidate_promotion_performed": bool(_candidate_like(payload)),
        "operator_must_approve_before_execution": True,
        "contract_hash": contract.fingerprint(),
    }
    return out, (), "synthesized_requires_operator_review"


def synthesize_overlays_from_contract(
    *,
    contract: ModelingIntentContract,
    overlay_files: Sequence[str | Path],
    output_overlays_dir: str | Path,
    suite_id: str | None = None,
    allow_candidate_promotion: bool = False,
    notes: str = "",
) -> OverlaySynthesisReport:
    out_dir = Path(output_overlays_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cases: list[SynthesisCaseProposal] = []
    global_items = _base_operator_items(contract)
    for overlay_path in overlay_files:
        source = Path(overlay_path).expanduser().resolve()
        payload = _read_json(source)
        synthesized_payload, synth_items, synth_status = _attempt_safe_overlay_synthesis(
            payload=payload,
            contract=contract,
            allow_candidate_promotion=allow_candidate_promotion,
        )
        synthesized_path: Path | None = None
        cert_eligible = False
        violations: tuple[str, ...] = ()
        items = list(synth_items)
        if synthesized_payload is not None:
            synthesized_path = out_dir / source.name
            _write_json(synthesized_path, synthesized_payload)
            compliance = validate_contract_for_overlay(
                contract=contract,
                overlay_payload=synthesized_payload,
                overlay_hash=file_hash(synthesized_path),
            )
            cert_eligible = bool(compliance.certification_eligible)
            violations = tuple(compliance.violations)
            if not compliance.passed:
                items.extend(_items_from_compliance(compliance.violations))
        else:
            # Validate original just to attach concrete compliance reasons to the proposal.
            compliance = validate_contract_for_overlay(
                contract=contract,
                overlay_payload=payload,
                overlay_hash=file_hash(source),
            )
            cert_eligible = False
            violations = tuple(compliance.violations)
            items.extend(_items_from_compliance(compliance.violations))
        cases.append(SynthesisCaseProposal(
            case_id=source.stem,
            source_overlay_path=str(source),
            source_overlay_sha256=file_hash(source),
            synthesized_overlay_path=str(synthesized_path) if synthesized_path else None,
            synthesis_status=synth_status,
            auto_synthesized=synthesized_path is not None,
            certification_eligible_after_synthesis=cert_eligible,
            compliance_violations=violations,
            operator_required_items=tuple(items),
            notes="Certification-eligible only if compliance passes after synthesis and operator approval.",
        ))
    eligible = sum(1 for c in cases if c.certification_eligible_after_synthesis)
    synthesized_count = sum(1 for c in cases if c.synthesized_overlay_path)
    blocked = len(cases) - eligible
    item_count = len(global_items) + sum(len(c.operator_required_items) for c in cases)
    report = OverlaySynthesisReport(
        schema=SYNTHESIS_SCHEMA,
        generated_utc=_now_utc(),
        modeling_intent=contract.modeling_intent,
        contract_hash=contract.fingerprint(),
        synthesis_mode="contract_driven_operator_review_required",
        suite_id=suite_id,
        source_overlay_count=len(cases),
        synthesized_overlay_count=synthesized_count,
        blocked_case_count=blocked,
        certification_eligible_case_count=eligible,
        operator_required_item_count=item_count,
        can_build_certification_plan=bool(contract.mode != "certification" or eligible > 0),
        operator_action_required=bool(item_count > 0 or contract.mode == "certification"),
        global_operator_required_items=tuple(global_items),
        cases=tuple(cases),
        notes=notes or "Generated by contract-driven overlay synthesis. This report is planning evidence only; it does not execute SOO.",
    )
    _write_json(out_dir / "OVERLAY_SYNTHESIS_REPORT.json", report.to_dict())
    req_report = operator_required_items_from_synthesis(report, context="overlay_synthesis")
    _write_json(out_dir / "OPERATOR_REQUIRED_ITEMS.json", req_report.to_dict())
    return report


def operator_required_items_from_synthesis(report: OverlaySynthesisReport, *, context: str) -> OperatorRequiredItemsReport:
    items: list[OperatorRequiredItem] = list(report.global_operator_required_items)
    for case in report.cases:
        items.extend(case.operator_required_items)
    # Deduplicate by item_id/category/prompt to keep reports readable.
    dedup: dict[tuple[str, str, str], OperatorRequiredItem] = {}
    for item in items:
        dedup[(item.item_id, item.category, item.prompt)] = item
    wrapped_items = tuple(_with_generator(item) for item in dedup.values())
    return OperatorRequiredItemsReport(
        schema=OPERATOR_REQUIREMENTS_SCHEMA,
        generated_utc=_now_utc(),
        context=context,
        modeling_intent=report.modeling_intent,
        contract_hash=report.contract_hash,
        requested_mode="certification",
        approved_plan_path=None,
        output_root=None,
        items=wrapped_items,
        blocks_certification_execution=any(i.blocks_certification_execution for i in wrapped_items),
        recommended_generator_command=recommended_operator_review_packet_command(),
        recommended_generator_outputs=operator_review_packet_outputs(),
        notes="Operator must supply or approve the listed items before certification-mode execution is allowed. Use the recommended generator command to create a review packet for the modeling chat/user approval workflow.",
    )


def write_operator_required_items_report(
    *,
    path: str | Path,
    context: str,
    items: Sequence[OperatorRequiredItem],
    contract: ModelingIntentContract | None = None,
    requested_mode: str | None = None,
    approved_plan_path: str | Path | None = None,
    output_root: str | Path | None = None,
    notes: str = "",
) -> OperatorRequiredItemsReport:
    path = Path(path)
    generator_output_dir = path.parent / "OPERATOR_REVIEW_PACKET"
    wrapped_items = tuple(_with_generator(item) for item in items)
    recommended_command = recommended_operator_review_packet_command(
        contract_path=None,
        operator_required_items_path=path,
        output_dir=generator_output_dir,
    )
    report = OperatorRequiredItemsReport(
        schema=OPERATOR_REQUIREMENTS_SCHEMA,
        generated_utc=_now_utc(),
        context=context,
        modeling_intent=contract.modeling_intent if contract else None,
        contract_hash=contract.fingerprint() if contract else None,
        requested_mode=requested_mode,
        approved_plan_path=str(approved_plan_path) if approved_plan_path else None,
        output_root=str(output_root) if output_root else None,
        items=wrapped_items,
        blocks_certification_execution=any(i.blocks_certification_execution for i in wrapped_items),
        recommended_generator_command=recommended_command,
        recommended_generator_outputs=operator_review_packet_outputs(),
        notes=notes or "Certification execution is blocked until the operator provides the required items. The modeling chat should run the recommended generator command, customize the resulting packet, and return it to the operator/user for approval before certification execution.",
    )
    _write_json(path, report.to_dict())
    # Give modeling chats/operators an immediately visible next command. The
    # command intentionally contains a contract placeholder when the caller did
    # not pass an actual contract path; this keeps the framework from guessing
    # a user-specific file location.
    try:
        script = path.parent / "GENERATE_OPERATOR_REVIEW_PACKET.sh"
        script.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + recommended_command + "\n", encoding="utf-8")
        script.chmod(0o755)
    except Exception:
        pass
    return report


def required_items_for_certification_preflight(
    *,
    contract: ModelingIntentContract | None,
    requested_mode: str,
    missing_contract: bool = False,
    missing_approved_plan: bool = False,
    invalid_plan_reasons: Sequence[str] = (),
    release_guard_reasons: Sequence[str] = (),
) -> tuple[OperatorRequiredItem, ...]:
    items: list[OperatorRequiredItem] = []
    if missing_contract:
        items.append(OperatorRequiredItem(
            item_id="modeling_intent_contract_required",
            severity="blocking",
            category="contract",
            required_from_operator=True,
            prompt="Provide --modeling-intent-contract pointing to the approved certification contract JSON.",
            reason="Certification mode cannot begin without a predeclared modeling_intent contract.",
            acceptable_forms=("contract JSON path",),
        ))
    if missing_approved_plan:
        items.append(OperatorRequiredItem(
            item_id="approved_modeling_plan_required",
            severity="blocking",
            category="planning",
            required_from_operator=True,
            prompt="Provide --approved-plan generated by rank3-plan-from-modeling-intent and approved by the operator.",
            reason="Certification mode requires operator approval of the exact executable run plan before execution.",
            acceptable_forms=("approved plan JSON path",),
        ))
    for idx, reason in enumerate(invalid_plan_reasons):
        items.append(OperatorRequiredItem(
            item_id=f"invalid_approved_plan_{idx+1}",
            severity="blocking",
            category="planning",
            required_from_operator=True,
            prompt="Repair/regenerate the modeling plan, then approve the repaired plan before certification execution.",
            reason=str(reason),
            acceptable_forms=("regenerated plan", "operator-approved revised plan", "external overlays satisfying contract"),
        ))
    for idx, reason in enumerate(release_guard_reasons):
        items.append(OperatorRequiredItem(
            item_id=f"release_guard_item_{idx+1}",
            severity="blocking",
            category="release_guard",
            required_from_operator=True,
            prompt="Provide signed local release files or reachable signed release URLs for the release guard.",
            reason=str(reason),
            acceptable_forms=("--release-manifest", "--release-signature", "--release-public-key", "--framework-zip"),
        ))
    if requested_mode == "certification" and contract is not None:
        items.extend(_base_operator_items(contract))
    # Deduplicate by item_id only for preflight.
    dedup: dict[str, OperatorRequiredItem] = {}
    for item in items:
        dedup.setdefault(item.item_id, item)
    return tuple(dedup.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize or request overlays from a modeling_intent contract without running the model.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--suite-id", help="Built-in suite ID to use as source templates.")
    source.add_argument("--overlays-dir", help="Directory containing external overlay JSON templates.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output-overlays", required=True)
    parser.add_argument("--allow-candidate-promotion", action="store_true", help="Permit candidate-to-admission field synthesis. This usually remains non-certifying unless the contract also allows candidate rules.")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--case-glob", action="append", default=[])
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    from .run_manager import overlay_files_from_source, filter_overlay_files
    contract = contract_from_file(args.contract)
    files = overlay_files_from_source(suite_id=args.suite_id, overlays_dir=args.overlays_dir)
    files = filter_overlay_files(files, case_ids=args.case, case_globs=args.case_glob)
    report = synthesize_overlays_from_contract(
        contract=contract,
        overlay_files=files,
        output_overlays_dir=args.output_overlays,
        suite_id=args.suite_id,
        allow_candidate_promotion=args.allow_candidate_promotion,
        notes=args.notes,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.can_build_certification_plan else 2


if __name__ == "__main__":
    raise SystemExit(main())
