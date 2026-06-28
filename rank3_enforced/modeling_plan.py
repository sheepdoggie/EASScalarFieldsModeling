from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
import json

from .fingerprints import file_hash, stable_json_hash
from .modeling_intent import ModelingIntentContract, contract_from_file, validate_contract_for_overlay

PLAN_SCHEMA = "rank3_modeling_execution_plan_v1"
PLAN_VALIDATION_SCHEMA = "rank3_modeling_plan_validation_v1"
APPROVED_STATUS = "approved_for_execution"
DRAFT_STATUS = "draft_pending_user_approval"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _inject_contract(source: Path, target: Path, contract: ModelingIntentContract) -> Path:
    payload = _read_json(source)
    payload["modeling_intent"] = contract.to_dict()
    notes = str(payload.get("notes", ""))
    payload["notes"] = (notes + "\nModeling plan staged this overlay with the supplied modeling_intent contract.").strip()
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_json(target, payload)
    return target


@dataclass(frozen=True)
class ModelingPlanCase:
    case_id: str
    source_overlay_path: str
    planned_overlay_path: str
    source_overlay_sha256: str
    planned_overlay_sha256: str
    compliance_passed: bool
    certification_eligible: bool
    violations: tuple[str, ...]
    warnings: tuple[str, ...]
    will_execute_model_if_run: bool


@dataclass(frozen=True)
class ModelingExecutionPlan:
    plan_schema: str
    plan_status: str
    generated_utc: str
    modeling_mode: str
    modeling_intent: str
    contract_hash: str
    suite_id: str | None
    overlays_dir: str | None
    output_overlays_dir: str | None
    selected_case_count: int
    certification_eligible_case_count: int
    blocked_case_count: int
    cases: tuple[ModelingPlanCase, ...]
    approval: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class ModelingPlanValidationReport:
    report_schema: str
    passed: bool
    require_approved: bool
    plan_status: str | None
    plan_hash: str | None
    contract_hash: str | None
    expected_contract_hash: str | None
    case_count: int
    certification_eligible_case_count: int
    blocked_case_count: int
    violations: tuple[str, ...]
    warnings: tuple[str, ...]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def build_modeling_plan(
    *,
    contract: ModelingIntentContract,
    overlay_files: Sequence[str | Path],
    suite_id: str | None = None,
    overlays_dir: str | Path | None = None,
    output_overlays_dir: str | Path | None = None,
    modeling_mode: str = "certification",
    plan_status: str = DRAFT_STATUS,
    notes: str = "",
) -> ModelingExecutionPlan:
    """Build a reviewable, non-executing modeling plan from a contract and overlays.

    The plan is data-only. It does not run SOO and does not mutate source overlays.
    When output_overlays_dir is supplied, contract-staged overlay copies are written
    there so the user can inspect the exact run inputs proposed for approval.
    """
    if modeling_mode not in ("exploratory", "certification"):
        raise ValueError("modeling_mode must be exploratory or certification")
    out_dir = Path(output_overlays_dir).resolve() if output_overlays_dir else None
    cases: list[ModelingPlanCase] = []
    for overlay_path in overlay_files:
        source = Path(overlay_path).resolve()
        if out_dir is not None:
            planned = _inject_contract(source, out_dir / source.name, contract)
        else:
            planned = source
        payload = _read_json(planned)
        planned_hash = file_hash(planned)
        compliance = validate_contract_for_overlay(
            contract=contract,
            overlay_payload=payload,
            overlay_hash=planned_hash,
        )
        cases.append(ModelingPlanCase(
            case_id=source.stem,
            source_overlay_path=str(source),
            planned_overlay_path=str(planned.resolve()),
            source_overlay_sha256=file_hash(source),
            planned_overlay_sha256=planned_hash,
            compliance_passed=bool(compliance.passed),
            certification_eligible=bool(compliance.certification_eligible),
            violations=tuple(compliance.violations),
            warnings=tuple(compliance.warnings),
            will_execute_model_if_run=bool(modeling_mode != "certification" or compliance.passed),
        ))
    eligible = sum(1 for c in cases if c.certification_eligible)
    blocked = sum(1 for c in cases if not c.will_execute_model_if_run)
    return ModelingExecutionPlan(
        plan_schema=PLAN_SCHEMA,
        plan_status=plan_status,
        generated_utc=_now_utc(),
        modeling_mode=modeling_mode,
        modeling_intent=contract.modeling_intent,
        contract_hash=contract.fingerprint(),
        suite_id=suite_id,
        overlays_dir=str(Path(overlays_dir).resolve()) if overlays_dir is not None else None,
        output_overlays_dir=str(out_dir) if out_dir is not None else None,
        selected_case_count=len(cases),
        certification_eligible_case_count=eligible,
        blocked_case_count=blocked,
        cases=tuple(cases),
        approval={},
        notes=notes,
    )


def load_modeling_plan(path: str | Path) -> ModelingExecutionPlan:
    payload = _read_json(path)
    if payload.get("plan_schema") != PLAN_SCHEMA:
        raise ValueError(f"Unsupported modeling plan schema: {payload.get('plan_schema')}")
    cases = tuple(ModelingPlanCase(**case) for case in payload.get("cases", []))
    return ModelingExecutionPlan(
        plan_schema=str(payload["plan_schema"]),
        plan_status=str(payload.get("plan_status", "")),
        generated_utc=str(payload.get("generated_utc", "")),
        modeling_mode=str(payload.get("modeling_mode", "")),
        modeling_intent=str(payload.get("modeling_intent", "")),
        contract_hash=str(payload.get("contract_hash", "")),
        suite_id=payload.get("suite_id"),
        overlays_dir=payload.get("overlays_dir"),
        output_overlays_dir=payload.get("output_overlays_dir"),
        selected_case_count=int(payload.get("selected_case_count", len(cases))),
        certification_eligible_case_count=int(payload.get("certification_eligible_case_count", 0)),
        blocked_case_count=int(payload.get("blocked_case_count", 0)),
        cases=cases,
        approval=dict(payload.get("approval", {})),
        notes=str(payload.get("notes", "")),
    )


def approve_modeling_plan(
    *,
    plan_path: str | Path,
    output_path: str | Path,
    approved_by: str = "user",
    notes: str = "",
) -> ModelingExecutionPlan:
    draft = load_modeling_plan(plan_path)
    draft_hash = draft.fingerprint()
    approved = ModelingExecutionPlan(
        plan_schema=draft.plan_schema,
        plan_status=APPROVED_STATUS,
        generated_utc=draft.generated_utc,
        modeling_mode=draft.modeling_mode,
        modeling_intent=draft.modeling_intent,
        contract_hash=draft.contract_hash,
        suite_id=draft.suite_id,
        overlays_dir=draft.overlays_dir,
        output_overlays_dir=draft.output_overlays_dir,
        selected_case_count=draft.selected_case_count,
        certification_eligible_case_count=draft.certification_eligible_case_count,
        blocked_case_count=draft.blocked_case_count,
        cases=draft.cases,
        approval={
            "approval_status": APPROVED_STATUS,
            "approved_by": approved_by,
            "approved_utc": _now_utc(),
            "draft_plan_hash": draft_hash,
            "approval_notes": notes,
        },
        notes=draft.notes,
    )
    _write_json(output_path, approved.to_dict())
    return approved


def validate_modeling_plan(
    *,
    contract: ModelingIntentContract,
    plan: ModelingExecutionPlan,
    overlay_files: Sequence[str | Path] | None = None,
    require_approved: bool = False,
) -> ModelingPlanValidationReport:
    violations: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}
    if plan.contract_hash != contract.fingerprint():
        violations.append("plan contract_hash does not match supplied modeling_intent contract")
    if plan.modeling_intent != contract.modeling_intent:
        violations.append("plan modeling_intent does not match supplied contract")
    if require_approved and plan.plan_status != APPROVED_STATUS:
        violations.append("certification execution requires an approved modeling plan")
    if plan.plan_status == APPROVED_STATUS and plan.approval.get("approval_status") != APPROVED_STATUS:
        violations.append("approved plan status lacks matching approval record")
    case_by_id = {case.case_id: case for case in plan.cases}
    details["planned_case_ids"] = sorted(case_by_id)
    if len(case_by_id) != len(plan.cases):
        violations.append("plan contains duplicate case_id entries")
    if overlay_files is not None:
        selected = {Path(p).stem: Path(p).resolve() for p in overlay_files}
        details["selected_case_ids"] = sorted(selected)
        missing_from_plan = sorted(set(selected) - set(case_by_id))
        extra_in_plan = sorted(set(case_by_id) - set(selected))
        if missing_from_plan:
            violations.append("selected overlay case(s) missing from approved plan: " + ", ".join(missing_from_plan))
        if extra_in_plan:
            warnings.append("approved plan contains case(s) not selected for this run: " + ", ".join(extra_in_plan))
        for case_id, source_path in selected.items():
            case = case_by_id.get(case_id)
            if case is None:
                continue
            # The selected source may be the original source or the plan-staged overlay. Accept either hash.
            observed = file_hash(source_path)
            if observed not in {case.source_overlay_sha256, case.planned_overlay_sha256}:
                violations.append(f"overlay hash mismatch for case {case_id}")
            planned_path = Path(case.planned_overlay_path)
            if planned_path.exists():
                planned_observed = file_hash(planned_path)
                if planned_observed != case.planned_overlay_sha256:
                    violations.append(f"planned overlay file hash mismatch for case {case_id}")
                payload = _read_json(planned_path)
                compliance = validate_contract_for_overlay(
                    contract=contract,
                    overlay_payload=payload,
                    overlay_hash=planned_observed,
                )
                if bool(compliance.passed) != bool(case.compliance_passed):
                    violations.append(f"stored compliance result is stale for case {case_id}")
            else:
                warnings.append(f"planned overlay path does not exist for case {case_id}: {planned_path}")
    eligible = sum(1 for c in plan.cases if c.certification_eligible)
    blocked = sum(1 for c in plan.cases if not c.will_execute_model_if_run)
    if eligible != plan.certification_eligible_case_count:
        violations.append("plan certification_eligible_case_count does not match case records")
    if blocked != plan.blocked_case_count:
        violations.append("plan blocked_case_count does not match case records")
    return ModelingPlanValidationReport(
        report_schema=PLAN_VALIDATION_SCHEMA,
        passed=not violations,
        require_approved=require_approved,
        plan_status=plan.plan_status,
        plan_hash=plan.fingerprint(),
        contract_hash=plan.contract_hash,
        expected_contract_hash=contract.fingerprint(),
        case_count=len(plan.cases),
        certification_eligible_case_count=eligible,
        blocked_case_count=blocked,
        violations=tuple(violations),
        warnings=tuple(warnings),
        details=details,
    )


def write_modeling_plan(path: str | Path, plan: ModelingExecutionPlan) -> None:
    _write_json(path, plan.to_dict())


def write_plan_validation_report(path: str | Path, report: ModelingPlanValidationReport) -> None:
    _write_json(path, report.to_dict())
