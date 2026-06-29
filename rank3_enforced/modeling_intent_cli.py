from __future__ import annotations

import argparse
import json
from pathlib import Path

from .modeling_intent import (
    charge_path_adjustment_certification_template,
    contract_from_file,
    validate_contract_for_overlay,
)
from .modeling_plan import (
    approve_modeling_plan,
    build_modeling_plan,
    load_modeling_plan,
    validate_modeling_plan,
    write_modeling_plan,
)
from .run_manager import overlay_files_from_source, filter_overlay_files, BUILTIN_SUITES


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main_template(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a modeling_intent contract template.")
    parser.add_argument("--intent", default="charge_path_adjustment_theorem", choices=["charge_path_adjustment_theorem"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    contract = charge_path_adjustment_certification_template()
    _write_json(Path(args.output), contract.to_dict())
    print(f"Wrote modeling_intent contract template: {args.output}")
    return 0


def main_validate(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a modeling_intent contract against an overlay JSON.")
    parser.add_argument("contract")
    parser.add_argument("overlay")
    args = parser.parse_args(argv)
    contract = contract_from_file(args.contract)
    overlay_payload = json.loads(Path(args.overlay).read_text(encoding="utf-8"))
    report = validate_contract_for_overlay(contract=contract, overlay_payload=overlay_payload, overlay_hash=None)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


def _add_source_args(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--suite-id", choices=sorted(BUILTIN_SUITES.keys()), help="Built-in suite ID to plan or validate.")
    source.add_argument("--overlays-dir", help="Directory containing external overlay JSON files.")
    parser.add_argument("--case", action="append", default=[], help="Exact overlay case stem to include; may be repeated.")
    parser.add_argument("--case-glob", action="append", default=[], help="fnmatch-style overlay stem pattern to include; may be repeated.")


def _selected_overlay_files(args: argparse.Namespace) -> list[Path]:
    files = overlay_files_from_source(suite_id=args.suite_id, overlays_dir=args.overlays_dir)
    return filter_overlay_files(files, case_ids=args.case, case_globs=args.case_glob)


def main_plan(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a reviewable modeling plan from a modeling_intent contract. This does not run the model.")
    _add_source_args(parser)
    parser.add_argument("--contract", required=True, help="modeling_intent contract JSON")
    parser.add_argument("--output-plan", required=True, help="Draft plan JSON to write")
    parser.add_argument("--output-overlays", help="Optional directory for exact staged overlays proposed by the plan")
    parser.add_argument("--mode", choices=["exploratory", "certification"], default="certification")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    contract = contract_from_file(args.contract)
    overlays = _selected_overlay_files(args)
    plan = build_modeling_plan(
        contract=contract,
        overlay_files=overlays,
        suite_id=args.suite_id,
        overlays_dir=args.overlays_dir,
        output_overlays_dir=args.output_overlays,
        modeling_mode=args.mode,
        notes=args.notes,
    )
    write_modeling_plan(args.output_plan, plan)
    print(f"Wrote draft modeling plan: {args.output_plan}")
    if args.output_overlays:
        print(f"Wrote staged plan overlays: {args.output_overlays}")
    print(json.dumps({
        "plan_status": plan.plan_status,
        "plan_hash": plan.fingerprint(),
        "selected_case_count": plan.selected_case_count,
        "certification_eligible_case_count": plan.certification_eligible_case_count,
        "blocked_case_count": plan.blocked_case_count,
        "plan_certification_executable": plan.plan_certification_executable,
        "execution_blocking_reasons": plan.execution_blocking_reasons,
    }, indent=2, sort_keys=True))
    return 0


def main_approve_plan(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mark a reviewed modeling plan as approved for execution. This does not run the model.")
    parser.add_argument("--plan", required=True, help="Draft modeling plan JSON")
    parser.add_argument("--output", required=True, help="Approved modeling plan JSON to write")
    parser.add_argument("--approved-by", default="user")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    approved = approve_modeling_plan(plan_path=args.plan, output_path=args.output, approved_by=args.approved_by, notes=args.notes)
    print(f"Wrote approved modeling plan: {args.output}")
    print(json.dumps({
        "plan_status": approved.plan_status,
        "approved_plan_hash": approved.fingerprint(),
        "draft_plan_hash": approved.approval.get("draft_plan_hash"),
        "certification_eligible_case_count": approved.certification_eligible_case_count,
        "blocked_case_count": approved.blocked_case_count,
        "plan_certification_executable": approved.plan_certification_executable,
        "execution_blocking_reasons": approved.execution_blocking_reasons,
    }, indent=2, sort_keys=True))
    return 0


def main_validate_plan(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an approved modeling plan against a contract and selected overlays. This does not run the model.")
    _add_source_args(parser)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--output-report")
    args = parser.parse_args(argv)
    contract = contract_from_file(args.contract)
    plan = load_modeling_plan(args.plan)
    overlays = _selected_overlay_files(args)
    report = validate_modeling_plan(contract=contract, plan=plan, overlay_files=overlays, require_approved=args.require_approved)
    payload = report.to_dict()
    if args.output_report:
        _write_json(Path(args.output_report), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.passed else 1
