from __future__ import annotations

import fnmatch
import json
import traceback
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Iterable, Sequence

from .certified_runner import run_declarative_overlay
from .fingerprints import file_hash, stable_json_hash
from .package_manifest import default_environment_record, package_and_sign_enforced_result
from .signing import verify_certificate
from .modeling_intent import default_exploratory_contract, contract_from_file, validate_contract_for_overlay
from .contract_overlay_synthesis import required_items_for_certification_preflight, write_operator_required_items_report
from .modeling_plan import load_modeling_plan, validate_modeling_plan
from .version_guard import enforce_latest_release_guard

BUILTIN_SUITE_ROOT = "overlay_suites"


@dataclass(frozen=True)
class BuiltinSuite:
    suite_id: str
    description: str
    required_artifacts: tuple[str, ...]


BUILTIN_SUITES: dict[str, BuiltinSuite] = {
    "charge_same_opposite_association_indexed": BuiltinSuite(
        suite_id="charge_same_opposite_association_indexed",
        description=(
            "Legacy L16-L32 same/opposite charge support path overlays using association-indexed SOO, "
            "two-ledger initialization, and identity remap. Diagnostic only; not theorem-capable for Delta L."
        ),
        required_artifacts=(
            "CERTIFICATE.json",
            "EVIDENCE_ENVELOPE.json",
            "MODELING_INTENT_CONTRACT.json",
            "MODELING_INTENT_COMPLIANCE_REPORT.json",
            "INITIAL_TWO_LEDGER_REPORT.json",
            "INITIALIZATION_SETTLING_REPORT.json",
            "OPTIONAL_MODULE_REPORT.json",
            "SOO_EXECUTION_REPORT.json",
            "CYCLIC_RETURN_REPORT.json",
            "STIFFNESS_INPUT_REPORT.json",
            "RESPONSE_BURDEN_REPORT.json",
            "INDUCED_STIFFNESS_REPORT.json",
            "STIFFNESS_CLOSURE_REPORT.json",
            "STIFFNESS_FEEDBACK_REPORT.json",
            "SOO_FUNCTIONAL_REPORT.json",
            "PATH_CONSTRUCTION_REPORT.json",
            "PATH_FACING_ASSOCIATION_REPORT.json",
        ),
    ),
    "charge_role_path_remap_dynamic_path_v0_1": BuiltinSuite(
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
        description=(
            "v0.1.23 candidate suite using role/path-preserving remap, "
            "declared relational path records, and sign-resolved midpoint readouts. "
            "Path add/remove is external-monitor-only, not intrinsic framework ontology."
        ),
        required_artifacts=(
            "CERTIFICATE.json",
            "EVIDENCE_ENVELOPE.json",
            "MODELING_INTENT_CONTRACT.json",
            "MODELING_INTENT_COMPLIANCE_REPORT.json",
            "OPTIONAL_MODULE_REPORT.json",
            "SOO_EXECUTION_REPORT.json",
            "SOO_FUNCTIONAL_REPORT.json",
            "PATH_CONSTRUCTION_REPORT.json",
            "PATH_FACING_ASSOCIATION_REPORT.json",
            "ROLE_PATH_REMAP_REPORT.json",
        ),
    ),
}


@dataclass(frozen=True)
class OverlayRunRecord:
    case_id: str
    overlay_path: str
    output_dir: str
    status: str
    certificate_valid: bool | None
    base_gate_passed: bool | None
    external_verdict: str | None
    missing_required_artifacts: tuple[str, ...]
    error: str | None = None
    modeling_mode: str = "exploratory"
    contract_hash: str | None = None
    compliance_passed: bool | None = None
    certification_eligible: bool | None = None
    warning_mode_non_certifying: bool = False
    approved_plan_hash: str | None = None


@dataclass(frozen=True)
class SuiteRunReport:
    suite_id: str
    started_utc: str
    finished_utc: str
    output_root: str
    overlay_count: int
    passed_count: int
    failed_count: int
    release_guard_passed: bool
    release_guard_cache: str | None
    modeling_mode: str
    contract_hash: str | None
    contract_path: str | None
    certification_requested: bool
    warning_mode_non_certifying: bool
    records: tuple[OverlayRunRecord, ...]
    approved_plan_hash: str | None
    modeling_plan_path: str | None
    plan_validation_passed: bool | None
    report_hash: str

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        return d


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_signing_key() -> Path:
    return Path.home() / ".rank3" / "private_key.pem"


def suite_resource_files(suite_id: str) -> list[Path]:
    if suite_id not in BUILTIN_SUITES:
        raise ValueError(f"Unknown built-in suite: {suite_id}")
    suite_res = resources.files("rank3_enforced").joinpath(BUILTIN_SUITE_ROOT, suite_id)
    paths: list[Path] = []
    with resources.as_file(suite_res) as suite_path:
        if not suite_path.exists():
            raise FileNotFoundError(f"Built-in suite resources not found: {suite_id}")
        paths = sorted(Path(suite_path).glob("*.json"))
    return paths


def overlay_files_from_source(*, suite_id: str | None = None, overlays_dir: str | Path | None = None) -> list[Path]:
    if suite_id and overlays_dir:
        raise ValueError("Use either suite_id or overlays_dir, not both.")
    if suite_id:
        return suite_resource_files(suite_id)
    if overlays_dir is None:
        raise ValueError("Either suite_id or overlays_dir is required.")
    root = Path(overlays_dir)
    files = sorted(root.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON overlays found in {root}")
    return files


def filter_overlay_files(
    files: Sequence[Path],
    *,
    case_ids: Sequence[str] = (),
    case_globs: Sequence[str] = (),
) -> list[Path]:
    """Filter overlay files by case stem without depending on cwd.

    case_ids are exact overlay stems without .json. case_globs are fnmatch
    patterns applied to the same stem. The original sorted file order is
    preserved. Missing exact case IDs are rejected fail-closed.
    """
    ids = tuple(str(x) for x in case_ids if str(x).strip())
    globs = tuple(str(x) for x in case_globs if str(x).strip())
    if not ids and not globs:
        return list(files)
    by_stem = {p.stem: p for p in files}
    missing = tuple(x for x in ids if x not in by_stem)
    if missing:
        raise FileNotFoundError(
            "Requested overlay case(s) not found: "
            + ", ".join(missing)
            + ". Available cases include: "
            + ", ".join(sorted(by_stem)[:10])
        )
    selected: list[Path] = []
    selected_stems: set[str] = set()
    for p in files:
        stem = p.stem
        matched = stem in ids or any(fnmatch.fnmatchcase(stem, pattern) for pattern in globs)
        if matched and stem not in selected_stems:
            selected.append(p)
            selected_stems.add(stem)
    if not selected:
        raise FileNotFoundError(
            "No overlay cases matched filters: exact="
            + repr(ids)
            + " globs="
            + repr(globs)
        )
    return selected



def _debug_module_params(*, depth: int, max_points: int) -> dict[str, object]:
    return {
        "module_id": "run_debugging",
        "status": "experimental_instrumentation",
        "params": {
            "enabled": True,
            "path_neighborhood_depth": int(depth),
            "include_phi_history": True,
            "include_ordered_differences": True,
            "include_association_rows": True,
            "include_soo_step_report_links": True,
            "max_points": int(max_points),
        },
    }


def stage_overlay_with_debug(
    *,
    overlay_path: str | Path,
    staging_dir: str | Path,
    depth: int = 1,
    max_points: int = 256,
) -> Path:
    """Return a staged overlay with run_debugging explicitly enabled.

    The source overlay is not modified. This keeps built-in suites debug-free by
    default while allowing the run manager to create a fully auditable overlay
    when the operator explicitly requests instrumentation.
    """
    source = Path(overlay_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    modules = [m for m in payload.get("optional_modules", payload.get("modules", [])) if m.get("module_id") != "run_debugging"]
    modules.append(_debug_module_params(depth=depth, max_points=max_points))
    payload["optional_modules"] = modules
    notes = str(payload.get("notes", ""))
    payload["notes"] = (notes + "\nRun-debugging instrumentation was explicitly enabled by the run manager.").strip()
    staging = Path(staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    target = staging / source.name
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target



def stage_overlay_with_run_overrides(
    *,
    overlay_path: str | Path,
    staging_dir: str | Path,
    settling_overrides: dict[str, object] | None = None,
    execution_overrides: dict[str, object] | None = None,
    modeling_intent_payload: dict[str, object] | None = None,
    debug: bool = False,
    debug_depth: int = 1,
    debug_max_points: int = 256,
) -> Path:
    """Stage an overlay with operator-requested run-time overrides.

    Overrides are written into a temporary overlay, keeping built-in suites
    immutable. This is used for initialization-only and long-settling debug
    runs. The staged overlay is still data-only and its hash is captured in the
    evidence envelope.
    """
    source = Path(overlay_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    notes = str(payload.get("notes", ""))
    changed: list[str] = []

    if settling_overrides:
        init = dict(payload.get("initialization", {}))
        settling = dict(init.get("settling", {}))
        for key, value in settling_overrides.items():
            if value is not None:
                settling[str(key)] = value
        init["settling"] = settling
        payload["initialization"] = init
        changed.append("initialization.settling")

    if execution_overrides:
        execution = dict(payload.get("execution", {}))
        for key, value in execution_overrides.items():
            if value is not None:
                execution[str(key)] = value
        payload["execution"] = execution
        changed.append("execution")

    if modeling_intent_payload is not None:
        payload["modeling_intent"] = modeling_intent_payload
        changed.append("modeling_intent")

    modules = [m for m in payload.get("optional_modules", payload.get("modules", [])) if m.get("module_id") != "run_debugging"]
    if debug:
        modules.append(_debug_module_params(depth=debug_depth, max_points=debug_max_points))
        changed.append("run_debugging")
    payload["optional_modules"] = modules

    if changed:
        payload["notes"] = (notes + "\nRun-manager staged overrides: " + ", ".join(changed) + ".").strip()

    staging = Path(staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    suffix = "staged" + ("_debug" if debug else "")
    target = staging / f"{source.stem}__{suffix}.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def build_settling_overrides(
    *,
    init_min_cycles: int | None = None,
    init_max_cycles: int | None = None,
    init_recurrence_period_max: int | None = None,
    init_recurrence_period_min: int | None = None,
    init_consecutive_stable_cycles: int | None = None,
    init_tol_rms: float | None = None,
    init_tol_q95: float | None = None,
    init_tol_max: float | None = None,
    init_tol_sign: float | None = None,
    init_progress_interval: int | None = None,
) -> dict[str, object]:
    mapping = {
        "min_cycles": init_min_cycles,
        "max_cycles": init_max_cycles,
        "recurrence_period_min": init_recurrence_period_min,
        "recurrence_period_max": init_recurrence_period_max,
        "consecutive_stable_cycles_required": init_consecutive_stable_cycles,
        "tol_rms": init_tol_rms,
        "tol_q95": init_tol_q95,
        "tol_max": init_tol_max,
        "tol_sign": init_tol_sign,
        "progress_interval_cycles": init_progress_interval,
    }
    return {k: v for k, v in mapping.items() if v is not None}

def _progress(enabled: bool, message: str) -> None:
    if enabled:
        print(message, flush=True)

def _write_json_file(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_contract_rejection_case(
    *,
    overlay_path: str | Path,
    output_dir: str | Path,
    contract: object,
    compliance_report: object,
    modeling_mode: str,
    command: str,
    release_guard_report: object | None = None,
    modeling_plan: object | None = None,
    plan_validation_report: object | None = None,
    reason: str = "modeling_intent contract did not pass pre-run compliance",
) -> OverlayRunRecord:
    """Write a non-modeling failure package for certification fail-closed cases.

    This function intentionally does not run SOO. It records the supplied
    contract and compliance report so independent auditors can verify that the
    requested certification contract, not the exploratory default, governed the
    decision to stop.
    """
    overlay = Path(overlay_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    try:
        overlay_payload = json.loads(overlay.read_text(encoding="utf-8"))
    except Exception:
        overlay_payload = {"overlay_read_error": True}
    if overlay.exists():
        (output / "overlay.json").write_text(overlay.read_text(encoding="utf-8"), encoding="utf-8")
    contract_dict = contract.to_dict() if hasattr(contract, "to_dict") else contract
    report_dict = compliance_report.to_dict() if hasattr(compliance_report, "to_dict") else compliance_report
    _write_json_file(output / "MODELING_INTENT_CONTRACT.json", contract_dict)
    _write_json_file(output / "MODELING_INTENT_COMPLIANCE_REPORT.json", report_dict)
    if modeling_plan is not None:
        _write_json_file(output / "MODELING_PLAN.json", modeling_plan.to_dict() if hasattr(modeling_plan, "to_dict") else modeling_plan)
        _write_json_file(output / "MODELING_PLAN.sha256", (modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None))
    if plan_validation_report is not None:
        _write_json_file(output / "MODELING_PLAN_VALIDATION_REPORT.json", plan_validation_report.to_dict() if hasattr(plan_validation_report, "to_dict") else plan_validation_report)
    _write_json_file(output / "CONTRACT_PROPAGATION_REPORT.json", {
        "schema": "rank3_contract_propagation_report_v0_1",
        "modeling_mode": modeling_mode,
        "contract_hash": getattr(contract, "fingerprint", lambda: None)(),
        "compliance_contract_hash": getattr(compliance_report, "contract_hash", None),
        "contract_hash_matches_compliance": getattr(contract, "fingerprint", lambda: None)() == getattr(compliance_report, "contract_hash", None),
        "supplied_contract_used": True,
        "exploratory_default_substituted": False,
        "pre_run_enforced": True,
        "model_executed": False,
        "reason": reason,
        "approved_plan_hash": (modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None),
        "plan_validation_passed": bool(getattr(plan_validation_report, "passed", False)) if plan_validation_report is not None else None,
    })
    _write_json_file(output / "RUN_CLASSIFICATION.json", {
        "schema": "rank3_run_classification_v0_1",
        "classification": "certification_blocked_pre_run" if modeling_mode == "certification" else "exploratory_contract_rejected_pre_run",
        "evidential_status": "non_certifying",
        "model_executed": False,
        "warning_mode_non_certifying": False,
        "command": command,
        "approved_plan_hash": (modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None),
        "plan_validation_passed": bool(getattr(plan_validation_report, "passed", False)) if plan_validation_report is not None else None,
        "overlay_hash": file_hash(overlay) if overlay.exists() else None,
        "overlay_run_kind": overlay_payload.get("run_kind"),
        "overlay_requested_certification": overlay_payload.get("requested_certification"),
    })
    if release_guard_report is not None:
        _write_json_file(output / "release_guard.json", release_guard_report.to_dict() if hasattr(release_guard_report, "to_dict") else release_guard_report)
    (output / "RUN_ERROR.txt").write_text(reason + "\n", encoding="utf-8")
    return OverlayRunRecord(
        case_id=output.name,
        overlay_path=str(overlay),
        output_dir=str(output),
        status="failed",
        certificate_valid=None,
        base_gate_passed=None,
        external_verdict=None,
        missing_required_artifacts=(),
        error=reason,
        modeling_mode=modeling_mode,
        contract_hash=getattr(contract, "fingerprint", lambda: None)(),
        compliance_passed=bool(getattr(compliance_report, "passed", False)),
        certification_eligible=bool(getattr(compliance_report, "certification_eligible", False)),
        warning_mode_non_certifying=False,
        approved_plan_hash=(modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None),
    )

def list_builtin_suites() -> list[dict[str, object]]:
    rows = []
    for suite_id, suite in sorted(BUILTIN_SUITES.items()):
        count = 0
        try:
            count = len(suite_resource_files(suite_id))
        except Exception:
            count = -1
        rows.append(
            {
                "suite_id": suite_id,
                "description": suite.description,
                "overlay_count": count,
                "required_artifacts": list(suite.required_artifacts),
            }
        )
    return rows


def write_workspace(path: str | Path) -> Path:
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    (root / "SUITES.json").write_text(json.dumps(list_builtin_suites(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# Rank-3 Run Workspace\n\n"
        "This workspace is intentionally code-free. Do not copy `rank3_enforced/` here.\n\n"
        "Use installed console commands, for example:\n\n"
        "```bash\n"
        "rank3-check-release-guard --force-refresh\n"
        "rank3-list-suites\n"
        "rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 --output-root runs/charge_role_path --signing-key ~/.rank3/private_key.pem\n"
        "```\n\n"
        "The run manager loads built-in overlays from the installed package and writes signed evidence packages under `runs/`.\n",
        encoding="utf-8",
    )
    return root


def run_signed_overlay_case(
    *,
    overlay_path: str | Path,
    output_dir: str | Path,
    private_key_path: str | Path | None = None,
    release_guard_cache_dir: str | Path | None = None,
    command: str = "rank3-run-overlay",
    required_artifacts: Sequence[str] = (),
    modeling_mode: str = "exploratory",
    contract_hash: str | None = None,
    release_manifest_url: str | None = None,
    release_signature_url: str | None = None,
    release_public_key_url: str | None = None,
    framework_zip_path: str | Path | None = None,
    modeling_plan: object | None = None,
    plan_validation_report: object | None = None,
) -> OverlayRunRecord:
    overlay = Path(overlay_path)
    output = Path(output_dir)
    key = Path(private_key_path) if private_key_path is not None else default_signing_key()
    cache_dir = Path(release_guard_cache_dir) if release_guard_cache_dir is not None else output.parent
    case_id = output.name
    try:
        guard_report = enforce_latest_release_guard(
            run_kind="candidate",
            cache_dir=cache_dir,
            manifest_url=release_manifest_url,
            signature_url=release_signature_url,
            public_key_url=release_public_key_url,
            framework_zip_path=framework_zip_path,
        )
        result = run_declarative_overlay(overlay)
        environment = default_environment_record()
        environment["release_guard"] = guard_report.to_dict()
        environment["overlay_file_sha256"] = file_hash(overlay)
        environment["modeling_mode"] = modeling_mode
        environment["suite_contract_hash"] = contract_hash
        environment["warning_mode_non_certifying"] = bool(not guard_report.passed or guard_report.mode in {"warn", "warning", "off"})
        if modeling_plan is not None:
            environment["modeling_plan_hash"] = modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None
            environment["modeling_plan_payload"] = modeling_plan.to_dict() if hasattr(modeling_plan, "to_dict") else modeling_plan
        if plan_validation_report is not None:
            environment["modeling_plan_validation_report"] = plan_validation_report.to_dict() if hasattr(plan_validation_report, "to_dict") else plan_validation_report
        package_and_sign_enforced_result(
            result=result,
            output_dir=output,
            private_key_path=key,
            overlay_path=overlay,
            command=command,
            environment=environment,
        )
        verification = verify_certificate(output)
        missing = tuple(name for name in required_artifacts if not (output / name).is_file())
        status = "passed" if verification.valid and not missing else "failed"
        return OverlayRunRecord(
            case_id=case_id,
            overlay_path=str(overlay),
            output_dir=str(output),
            status=status,
            certificate_valid=verification.valid,
            base_gate_passed=bool(result.gate.passed),
            external_verdict=str(result.gate.external_admission_verdict.value),
            missing_required_artifacts=missing,
            error=None if status == "passed" else "Missing required artifacts or invalid certificate.",
            modeling_mode=modeling_mode,
            contract_hash=contract_hash,
            compliance_passed=bool(getattr(result.modeling_intent_compliance_report, "passed", False)) if result.modeling_intent_compliance_report else None,
            certification_eligible=bool(getattr(result.modeling_intent_compliance_report, "certification_eligible", False)) if result.modeling_intent_compliance_report else None,
            warning_mode_non_certifying=bool(not guard_report.passed or guard_report.mode in {"warn", "warning", "off"}),
            approved_plan_hash=(modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None),
        )
    except Exception as exc:
        output.mkdir(parents=True, exist_ok=True)
        error_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        (output / "RUN_ERROR.txt").write_text(error_text, encoding="utf-8")
        return OverlayRunRecord(
            case_id=case_id,
            overlay_path=str(overlay),
            output_dir=str(output),
            status="failed",
            certificate_valid=None,
            base_gate_passed=None,
            external_verdict=None,
            missing_required_artifacts=tuple(required_artifacts),
            error=error_text,
            modeling_mode=modeling_mode,
            contract_hash=contract_hash,
            compliance_passed=None,
            certification_eligible=None,
            warning_mode_non_certifying=False,
            approved_plan_hash=(modeling_plan.fingerprint() if hasattr(modeling_plan, "fingerprint") else None),
        )


def run_overlay_suite(
    *,
    suite_id: str | None = None,
    overlays_dir: str | Path | None = None,
    output_root: str | Path,
    private_key_path: str | Path | None = None,
    fail_fast: bool = True,
    required_artifacts: Sequence[str] | None = None,
    progress: bool = True,
    debug: bool = False,
    debug_depth: int = 1,
    debug_max_points: int = 256,
    case_ids: Sequence[str] = (),
    case_globs: Sequence[str] = (),
    settling_overrides: dict[str, object] | None = None,
    execution_overrides: dict[str, object] | None = None,
    initialization_progress: bool = False,
    modeling_mode: str = "exploratory",
    modeling_intent_contract_path: str | Path | None = None,
    release_manifest_url: str | None = None,
    release_signature_url: str | None = None,
    release_public_key_url: str | None = None,
    framework_zip_path: str | Path | None = None,
    approved_plan_path: str | Path | None = None,
) -> SuiteRunReport:
    started = _now_utc()
    overlays_all = overlay_files_from_source(suite_id=suite_id, overlays_dir=overlays_dir)
    overlays = filter_overlay_files(overlays_all, case_ids=case_ids, case_globs=case_globs)
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    if modeling_mode not in ("exploratory", "certification"):
        raise ValueError("modeling_mode must be exploratory or certification")
    if modeling_mode == "certification" and modeling_intent_contract_path is None:
        items = required_items_for_certification_preflight(
            contract=None,
            requested_mode=modeling_mode,
            missing_contract=True,
            missing_approved_plan=approved_plan_path is None,
        )
        write_operator_required_items_report(
            path=output_root_path / "OPERATOR_REQUIRED_ITEMS.json",
            context="certification_preflight_missing_contract",
            items=items,
            contract=None,
            requested_mode=modeling_mode,
            approved_plan_path=approved_plan_path,
            output_root=output_root_path,
        )
        raise ValueError("certification mode requires --modeling-intent-contract. See OPERATOR_REQUIRED_ITEMS.json in the output root.")
    modeling_contract = (
        contract_from_file(modeling_intent_contract_path)
        if modeling_intent_contract_path is not None
        else default_exploratory_contract()
    )
    if modeling_mode == "certification" and modeling_contract.mode != "certification":
        raise ValueError("--mode certification requires a certification modeling_intent contract")
    if modeling_mode == "exploratory" and modeling_contract.mode != "exploratory" and modeling_intent_contract_path is None:
        raise ValueError("internal error: exploratory default contract should be exploratory")
    modeling_intent_payload = modeling_contract.to_dict()

    modeling_plan = None
    plan_validation_report = None
    if modeling_mode == "certification":
        if approved_plan_path is None:
            items = required_items_for_certification_preflight(
                contract=modeling_contract,
                requested_mode=modeling_mode,
                missing_approved_plan=True,
            )
            write_operator_required_items_report(
                path=output_root_path / "OPERATOR_REQUIRED_ITEMS.json",
                context="certification_preflight_missing_approved_plan",
                items=items,
                contract=modeling_contract,
                requested_mode=modeling_mode,
                approved_plan_path=approved_plan_path,
                output_root=output_root_path,
            )
            raise ValueError("certification mode requires --approved-plan generated and approved before execution. See OPERATOR_REQUIRED_ITEMS.json in the output root.")
        modeling_plan = load_modeling_plan(approved_plan_path)
        plan_validation_report = validate_modeling_plan(
            contract=modeling_contract,
            plan=modeling_plan,
            overlay_files=overlays,
            require_approved=True,
        )
        if not plan_validation_report.passed:
            output_root_path.mkdir(parents=True, exist_ok=True)
            (output_root_path / "MODELING_PLAN.json").write_text(json.dumps(modeling_plan.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (output_root_path / "MODELING_PLAN_VALIDATION_REPORT.json").write_text(json.dumps(plan_validation_report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
            blockers = list(getattr(plan_validation_report, "execution_blocking_violations", ()))
            structural = list(getattr(plan_validation_report, "violations", ()))
            reasons = structural + blockers
            items = required_items_for_certification_preflight(
                contract=modeling_contract,
                requested_mode=modeling_mode,
                invalid_plan_reasons=reasons,
            )
            write_operator_required_items_report(
                path=output_root_path / "OPERATOR_REQUIRED_ITEMS.json",
                context="certification_preflight_invalid_or_nonexecutable_plan",
                items=items,
                contract=modeling_contract,
                requested_mode=modeling_mode,
                approved_plan_path=approved_plan_path,
                output_root=output_root_path,
                notes="The approved modeling plan is structurally invalid or has no contract-executable certification cases.",
            )
            raise ValueError("certification mode requires a valid and executable approved modeling plan: " + "; ".join(reasons) + ". See OPERATOR_REQUIRED_ITEMS.json in the output root.")
        if debug or settling_overrides or execution_overrides:
            items = required_items_for_certification_preflight(
                contract=modeling_contract,
                requested_mode=modeling_mode,
                invalid_plan_reasons=("runtime overrides were requested outside the approved plan",),
            )
            write_operator_required_items_report(
                path=output_root_path / "OPERATOR_REQUIRED_ITEMS.json",
                context="certification_preflight_runtime_overrides_not_in_plan",
                items=items,
                contract=modeling_contract,
                requested_mode=modeling_mode,
                approved_plan_path=approved_plan_path,
                output_root=output_root_path,
            )
            raise ValueError("certification execution cannot add run-time overrides outside the approved modeling plan. Regenerate and reapprove the plan.")
    plan_cases_by_id = {case.case_id: case for case in getattr(modeling_plan, "cases", ())} if modeling_plan is not None else {}

    suite_label = suite_id or f"external:{Path(overlays_dir).resolve()}"
    _progress(progress, f"[suite] {suite_label}")
    _progress(progress, f"[suite] overlays={len(overlays)} selected_from={len(overlays_all)} output={output_root_path}")
    _progress(progress, "[release-guard] checking latest signed framework manifest")
    try:
        guard = enforce_latest_release_guard(
            run_kind="candidate",
            cache_dir=output_root_path,
            manifest_url=release_manifest_url,
            signature_url=release_signature_url,
            public_key_url=release_public_key_url,
            framework_zip_path=framework_zip_path,
        )
    except Exception as exc:
        if modeling_mode == "certification":
            items = required_items_for_certification_preflight(
                contract=modeling_contract,
                requested_mode=modeling_mode,
                release_guard_reasons=(str(exc),),
            )
            write_operator_required_items_report(
                path=output_root_path / "OPERATOR_REQUIRED_ITEMS.json",
                context="certification_release_guard_failed",
                items=items,
                contract=modeling_contract,
                requested_mode=modeling_mode,
                approved_plan_path=approved_plan_path,
                output_root=output_root_path,
                notes="Release guard failed before model execution. Provide signed local release files or reachable signed release URLs.",
            )
        raise
    (output_root_path / "release_guard.json").write_text(json.dumps(guard.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root_path / "MODELING_INTENT_CONTRACT.json").write_text(json.dumps(modeling_contract.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root_path / "MODELING_INTENT_CONTRACT.sha256").write_text(modeling_contract.fingerprint() + "\n", encoding="utf-8")
    if modeling_plan is not None:
        (output_root_path / "MODELING_PLAN.json").write_text(json.dumps(modeling_plan.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_root_path / "MODELING_PLAN.sha256").write_text(modeling_plan.fingerprint() + "\n", encoding="utf-8")
    if plan_validation_report is not None:
        (output_root_path / "MODELING_PLAN_VALIDATION_REPORT.json").write_text(json.dumps(plan_validation_report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _progress(progress, f"[release-guard] passed={guard.passed} cache={guard.cache_path}")

    if required_artifacts is None:
        if suite_id and suite_id in BUILTIN_SUITES:
            required_artifacts = BUILTIN_SUITES[suite_id].required_artifacts
        else:
            required_artifacts = ("CERTIFICATE.json", "EVIDENCE_ENVELOPE.json")
    if debug and "RUN_DEBUG_REPORT.json" not in required_artifacts:
        required_artifacts = tuple(required_artifacts) + ("RUN_DEBUG_REPORT.json",)

    if debug:
        _progress(progress, f"[debug] enabled depth={debug_depth} max_points={debug_max_points}")
    else:
        _progress(progress, "[debug] off")
    if settling_overrides:
        _progress(progress, f"[init-settling-overrides] {json.dumps(settling_overrides, sort_keys=True)}")
    if execution_overrides:
        _progress(progress, f"[execution-overrides] {json.dumps(execution_overrides, sort_keys=True)}")

    old_progress_env = None
    import os
    if initialization_progress:
        old_progress_env = os.environ.get("RANK3_INIT_PROGRESS")
        os.environ["RANK3_INIT_PROGRESS"] = "1"

    records: list[OverlayRunRecord] = []
    staging_dir = output_root_path / ".rank3_staged_overlays"
    for index, overlay in enumerate(overlays, start=1):
        case_id = overlay.stem
        if modeling_mode == "certification" and modeling_plan is not None:
            plan_case = plan_cases_by_id.get(case_id)
            if plan_case is None:
                raise ValueError(f"approved modeling plan does not contain selected case: {case_id}")
            overlay_for_run = Path(plan_case.planned_overlay_path)
        elif debug or settling_overrides or execution_overrides or modeling_intent_payload is not None:
            overlay_for_run = stage_overlay_with_run_overrides(
                overlay_path=overlay,
                staging_dir=staging_dir,
                settling_overrides=settling_overrides,
                execution_overrides=execution_overrides,
                debug=debug,
                debug_depth=debug_depth,
                debug_max_points=debug_max_points,
                modeling_intent_payload=modeling_intent_payload,
            )
        else:
            overlay_for_run = overlay
        # Pre-run contract validation is fail-closed for certification mode.
        overlay_payload_for_contract = json.loads(Path(overlay_for_run).read_text(encoding="utf-8"))
        overlay_hash_for_contract = file_hash(overlay_for_run)
        compliance_report = validate_contract_for_overlay(
            contract=modeling_contract,
            overlay_payload=overlay_payload_for_contract,
            overlay_hash=overlay_hash_for_contract,
        )
        if modeling_mode == "certification" and not compliance_report.passed:
            _progress(progress, f"[{index}/{len(overlays)}] BLOCK {case_id} contract compliance failed")
            record = write_contract_rejection_case(
                overlay_path=overlay_for_run,
                output_dir=output_root_path / "runs" / case_id,
                contract=modeling_contract,
                compliance_report=compliance_report,
                modeling_mode=modeling_mode,
                command=f"rank3-run-suite {suite_label}",
                release_guard_report=guard,
                modeling_plan=modeling_plan,
                plan_validation_report=plan_validation_report,
                reason="Certification blocked before model execution: modeling_intent contract compliance failed.",
            )
            records.append(record)
            if fail_fast:
                _progress(progress, "[suite] stopping on first contract failure; use --continue-on-failure to continue")
                break
            continue

        _progress(progress, f"[{index}/{len(overlays)}] START {case_id}")
        t0 = time.perf_counter()
        record = run_signed_overlay_case(
            overlay_path=overlay_for_run,
            output_dir=output_root_path / "runs" / case_id,
            private_key_path=private_key_path,
            release_guard_cache_dir=output_root_path,
            command=f"rank3-run-suite {suite_label}" + (" --debug" if debug else ""),
            required_artifacts=required_artifacts,
            modeling_mode=modeling_mode,
            contract_hash=modeling_contract.fingerprint(),
            release_manifest_url=release_manifest_url,
            release_signature_url=release_signature_url,
            release_public_key_url=release_public_key_url,
            framework_zip_path=framework_zip_path,
            modeling_plan=modeling_plan,
            plan_validation_report=plan_validation_report,
        )
        elapsed = time.perf_counter() - t0
        records.append(record)
        if record.status == "passed":
            _progress(progress, f"[{index}/{len(overlays)}] PASS  {case_id} elapsed={elapsed:.2f}s")
        else:
            _progress(progress, f"[{index}/{len(overlays)}] FAIL  {case_id} elapsed={elapsed:.2f}s")
            if record.error:
                _progress(progress, "[error] " + record.error.splitlines()[-1])
        if record.status != "passed" and fail_fast:
            _progress(progress, "[suite] stopping on first failure; use --continue-on-failure to continue")
            break

    if initialization_progress:
        if old_progress_env is None:
            os.environ.pop("RANK3_INIT_PROGRESS", None)
        else:
            os.environ["RANK3_INIT_PROGRESS"] = old_progress_env

    passed_count = sum(1 for r in records if r.status == "passed")
    failed_count = sum(1 for r in records if r.status != "passed")
    finished = _now_utc()
    payload_for_hash = {
        "suite_id": suite_label,
        "started_utc": started,
        "finished_utc": finished,
        "output_root": str(output_root_path),
        "modeling_mode": modeling_mode,
        "contract_hash": modeling_contract.fingerprint(),
        "approved_plan_hash": modeling_plan.fingerprint() if modeling_plan is not None else None,
        "plan_validation_passed": bool(plan_validation_report.passed) if plan_validation_report is not None else None,
        "records": [asdict(r) for r in records],
    }
    report = SuiteRunReport(
        suite_id=suite_label,
        started_utc=started,
        finished_utc=finished,
        output_root=str(output_root_path),
        overlay_count=len(overlays),
        passed_count=passed_count,
        failed_count=failed_count,
        release_guard_passed=guard.passed,
        release_guard_cache=str(guard.cache_path) if guard.cache_path else None,
        modeling_mode=modeling_mode,
        contract_hash=modeling_contract.fingerprint(),
        contract_path=str(modeling_intent_contract_path) if modeling_intent_contract_path is not None else None,
        certification_requested=(modeling_mode == "certification"),
        warning_mode_non_certifying=bool(not guard.passed or guard.mode in {"warn", "warning", "off"}),
        records=tuple(records),
        approved_plan_hash=modeling_plan.fingerprint() if modeling_plan is not None else None,
        modeling_plan_path=str(approved_plan_path) if approved_plan_path is not None else None,
        plan_validation_passed=bool(plan_validation_report.passed) if plan_validation_report is not None else None,
        report_hash=stable_json_hash(payload_for_hash),
    )
    (output_root_path / "SUITE_RUN_REPORT.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write package-level SHA256 sums for easy transfer verification.
    sums: list[str] = []
    for path in sorted(p for p in output_root_path.rglob("*") if p.is_file()):
        rel = path.relative_to(output_root_path)
        if rel.as_posix() == "SHA256SUMS.csv":
            continue
        sums.append(f"{file_hash(path)}  {rel.as_posix()}")
    (output_root_path / "SHA256SUMS.csv").write_text("\n".join(sums) + "\n", encoding="utf-8")
    _progress(progress, f"[suite] finished passed={passed_count} failed={failed_count} total={len(overlays)}")
    _progress(progress, f"[suite] report={output_root_path / 'SUITE_RUN_REPORT.json'}")
    return report
