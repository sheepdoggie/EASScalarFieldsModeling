from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import scalar_field_geometry as sfg

from .base_gate import BaseGateReport
from .control_suite import ControlSuiteReport, run_required_controls
from .evidence import EvidencePackage, build_evidence_package
from .exceptions import CertificationBlocked, ManifestError, RuleAuditError
from .fingerprints import array_hash, directory_hash, stable_json_hash
from .immutable_result import ImmutableScalarFieldGeometryResult
from .initialization_trace import InitializationEpochReport
from .initialization_settling import InitializationSettlingReport
from .manifest import ModelManifest
from .modeling_intent import ModelingIntentContract, ModelingIntentComplianceReport
from .path_debugging import (
    RunDebuggingSpec,
    build_path_facing_association_report,
    build_run_debugging_report,
)
from .readouts import DEFAULT_READOUTS, ReadoutReport, ReadoutRule
from .rule_metadata import AdmissionVerdict, RuleMetadata, RuleStatus, get_rule_metadata
from .source_audit import SourceAuditReport, audit_object_source
from .soo_functional import SOOFunctionalReport, build_soo_functional_report
from .soo_trace import SOOUpdateTrace


@dataclass(frozen=True)
class ModelPackage:
    """
    One enforceable model package.

    The raw geometry engine remains available for infrastructure use. A model
    that wants certified/admission language must go through this object and the
    run_model_package entry point.
    """

    manifest: ModelManifest
    config: sfg.ScalarFieldGeometryConfig
    scalar_update_metadata: RuleMetadata
    association_remap_metadata: RuleMetadata
    phase_rule_metadata: RuleMetadata | None = None
    pair_weight_rule_metadata: RuleMetadata | None = None
    triplet_lift_rule_metadata: RuleMetadata | None = None
    readout_rules: tuple[ReadoutRule, ...] = DEFAULT_READOUTS
    compiled_overlay_hash: str | None = None
    initialization_report: InitializationEpochReport | None = None
    initialization_soo_traces: tuple[SOOUpdateTrace, ...] = ()
    initial_two_ledger_report: object | None = None
    optional_module_report: object | None = None
    path_construction_report: object | None = None
    run_debugging_spec: RunDebuggingSpec | None = None
    initialization_settling_report: InitializationSettlingReport | None = None
    modeling_intent_contract: ModelingIntentContract | None = None
    modeling_intent_compliance_report: ModelingIntentComplianceReport | None = None


@dataclass(frozen=True)
class EnforcedRunResult:
    manifest: ModelManifest
    primary_result: ImmutableScalarFieldGeometryResult
    readouts: tuple[ReadoutReport, ...]
    controls: ControlSuiteReport
    source_audits: tuple[SourceAuditReport, ...]
    evidence: EvidencePackage
    gate: BaseGateReport
    core_hash: str
    soo_functional_report: SOOFunctionalReport | None = None
    soo_traces: tuple[SOOUpdateTrace, ...] = ()
    initialization_soo_traces: tuple[SOOUpdateTrace, ...] = ()
    initialization_report: InitializationEpochReport | None = None
    initial_two_ledger_report: object | None = None
    optional_module_report: object | None = None
    path_construction_report: object | None = None
    run_debugging_spec: RunDebuggingSpec | None = None
    soo_execution_report: object | None = None
    cyclic_return_report: object | None = None
    stiffness_input_report: object | None = None
    response_burden_report: object | None = None
    induced_stiffness_report: object | None = None
    stiffness_closure_report: object | None = None
    stiffness_feedback_report: object | None = None
    path_facing_association_report: object | None = None
    role_path_remap_report: object | None = None
    run_debugging_report: object | None = None
    initialization_settling_report: InitializationSettlingReport | None = None
    modeling_intent_contract: ModelingIntentContract | None = None
    modeling_intent_compliance_report: ModelingIntentComplianceReport | None = None

    @property
    def certified(self) -> bool:
        return self.gate.passed


def verify_core_integrity(
    *,
    expected_core_hash: str | None = None,
    package_root: str | Path | None = None,
) -> str:
    if package_root is None:
        package_root = Path(__file__).resolve().parent
    current_hash = directory_hash(package_root)
    if expected_core_hash is not None and current_hash != expected_core_hash:
        raise CertificationBlocked(
            "Core integrity hash mismatch. "
            f"expected={expected_core_hash}, observed={current_hash}"
        )
    return current_hash


def _audit_manifest(package: ModelPackage) -> None:
    manifest = package.manifest
    compliance = package.modeling_intent_compliance_report
    if compliance is None:
        if manifest.run_kind == "admission" or manifest.requested_certification:
            raise ManifestError("Certification/admission requires a modeling_intent compliance report.")
    elif compliance.mode == "exploratory" and (manifest.run_kind == "admission" or manifest.requested_certification):
        raise ManifestError("Exploratory modeling_intent cannot be used for admission/certification runs.")
    if compliance is not None and compliance.mode == "certification" and not compliance.passed:
        raise ManifestError("Certification modeling_intent contract did not pass pre-run compliance: " + "; ".join(compliance.violations))
    if manifest.run_kind in ("candidate", "admission") and not package.compiled_overlay_hash:
        raise ManifestError(
            "Candidate/admission runs must be compiled from a data-only declarative overlay. "
            "Direct Python ModelPackage overlays are exploratory only and cannot be used here."
        )
    if manifest.run_kind in ("candidate", "admission") and package.initialization_report is None:
        raise ManifestError("Candidate/admission runs require a compiled initialization report.")
    if package.initialization_report is not None and not package.initialization_report.passed:
        if manifest.run_kind == "admission" or manifest.requested_certification:
            raise ManifestError("Initialization report did not pass; admission/certification run is blocked.")
        # Candidate diagnostic packages may still be generated so the failed
        # initialization-settling evidence can be audited. BASE gate will fail.
    if not manifest.model_name.strip():
        raise ManifestError("model_name is required.")
    if not manifest.model_version.strip():
        raise ManifestError("model_version is required.")
    if not manifest.purpose.strip():
        raise ManifestError("purpose is required.")
    if manifest.requested_certification and manifest.run_kind != "admission":
        raise ManifestError("requested_certification=True requires run_kind='admission'.")
    if manifest.run_kind == "admission" and manifest.external_admission_verdict != AdmissionVerdict.ADMITTED:
        raise ManifestError("Admission run requires external_admission_verdict=Admitted.")
    missing_readouts = set(manifest.diagnostics.required_readouts) - {
        readout.name for readout in package.readout_rules
    }
    if missing_readouts:
        raise ManifestError(f"Missing pre-registered readout rules: {sorted(missing_readouts)}")


def _audit_rule_statuses(package: ModelPackage) -> None:
    allowed = package.manifest.required_rule_statuses()
    for label, metadata in (
        ("scalar_update_rule", package.scalar_update_metadata),
        ("association_remap_rule", package.association_remap_metadata),
    ):
        if metadata.status not in allowed:
            raise RuleAuditError(
                f"{label} {metadata.name!r} has status {metadata.status.value!r}; "
                f"run_kind={package.manifest.run_kind!r} allows "
                f"{[status.value for status in allowed]}."
            )
        if package.manifest.run_kind == "admission" and not metadata.allowed_for_certified_runs:
            raise RuleAuditError(
                f"{label} {metadata.name!r} is not allowed for certified/admission runs."
            )


def _audit_rule_sources(package: ModelPackage) -> tuple[SourceAuditReport, ...]:
    audits = (
        audit_object_source(package.config.scalar_update_rule, object_name=package.scalar_update_metadata.name),
        audit_object_source(package.config.association_remap_rule, object_name=package.association_remap_metadata.name),
    )
    failures = [audit for audit in audits if not audit.passed]
    if failures:
        raise RuleAuditError(
            "Forbidden source patterns found: "
            + "; ".join(
                f"{audit.object_name}: {audit.forbidden_hits}" for audit in failures
            )
        )
    return audits


def _reset_rule_trace_if_available(rule: object) -> None:
    reset = getattr(rule, "reset_trace", None)
    if callable(reset):
        reset()


def _collect_rule_traces_if_available(rule: object) -> tuple[SOOUpdateTrace, ...]:
    get_traces = getattr(rule, "get_traces", None)
    if callable(get_traces):
        traces = get_traces()
        return tuple(traces)
    return ()

def _finalize_rule_feedback_if_available(rule: object) -> None:
    finalize = getattr(rule, "finalize_feedback_reports", None)
    if callable(finalize):
        finalize()


def _get_rule_report_if_available(rule: object, method_name: str) -> object | None:
    getter = getattr(rule, method_name, None)
    if callable(getter):
        return getter()
    return None


def _audit_soo_traces(
    *,
    package: ModelPackage,
    result: ImmutableScalarFieldGeometryResult,
    traces: tuple[SOOUpdateTrace, ...],
) -> tuple[bool, dict[str, object]]:
    uses_declarative_soo = package.scalar_update_metadata.name == "soo_declarative_v0_1"
    expected_count = max(0, package.config.n_layers - 1)

    if not uses_declarative_soo:
        return True, {"uses_declarative_soo": False, "trace_count": len(traces)}

    count_passed = len(traces) == expected_count
    invariant_passed = all(trace.invariants.passed for trace in traces)
    phi_hash_passed = True
    phase_passed = True
    for index, trace in enumerate(traces):
        if index < result.phi.shape[0] - 1:
            phi_hash_passed = phi_hash_passed and trace.phi_current_hash == array_hash(result.phi[index])
            phase_passed = phase_passed and trace.phase == int(package.config.phase_rule(index) % 3)

    passed = count_passed and invariant_passed and phi_hash_passed and phase_passed
    details = {
        "uses_declarative_soo": True,
        "trace_count": len(traces),
        "expected_trace_count": expected_count,
        "count_passed": count_passed,
        "invariant_passed": invariant_passed,
        "phi_hash_passed": phi_hash_passed,
        "phase_passed": phase_passed,
        "trace_hashes": [trace.fingerprint() for trace in traces],
    }
    return passed, details


def _run_readouts(
    *,
    result: ImmutableScalarFieldGeometryResult,
    readout_rules: tuple[ReadoutRule, ...],
) -> tuple[ReadoutReport, ...]:
    reports: list[ReadoutReport] = []
    for readout in readout_rules:
        reports.append(readout(result))
    return tuple(reports)


def _build_base_gate(
    *,
    package: ModelPackage,
    result: ImmutableScalarFieldGeometryResult,
    controls: ControlSuiteReport,
    source_audits: tuple[SourceAuditReport, ...],
    readouts: tuple[ReadoutReport, ...],
    evidence: EvidencePackage,
    soo_trace_audit_passed: bool,
    soo_trace_details: dict[str, object],
) -> BaseGateReport:
    required_readouts = set(package.manifest.diagnostics.required_readouts)
    completed_readouts = {report.name for report in readouts}
    missing_readouts = sorted(required_readouts - completed_readouts)

    source_provenance_passed = all(
        bool(value)
        for value in (
            evidence.manifest_hash,
            evidence.initial_state_hash,
            evidence.initial_phi_hash,
            evidence.scalar_update_rule_hash,
            evidence.association_remap_rule_hash,
            evidence.result_hash,
            evidence.readout_hash,
            evidence.control_hash,
            evidence.compiled_overlay_hash,
            evidence.soo_trace_hash,
            evidence.soo_functional_hash,
            evidence.initialization_hash,
        )
    )

    verdict_independence_passed = (
        not missing_readouts
        and all(audit.passed for audit in source_audits)
        and soo_trace_audit_passed
        and (package.initialization_report is None or package.initialization_report.passed)
    )

    blind_generation_projection_separation_passed = (
        "visualization_as_physical_space" in package.manifest.forbidden_interpretations
    )

    leakage_manipulation_checks_passed = (
        result.verify()
        and all(state.verify() for state in result.states)
        and all(audit.passed for audit in source_audits)
        and soo_trace_audit_passed
        and (package.initialization_report is None or package.initialization_report.passed)
    )

    details = {
        "missing_readouts": missing_readouts,
        "control_reports": [report.__dict__ for report in controls.reports],
        "source_audits": [audit.__dict__ for audit in source_audits],
        "result_verified_immutable": result.verify(),
        "evidence_package_hash": evidence.package_hash,
        "soo_trace_audit": soo_trace_details,
        "soo_trace_hash": evidence.soo_trace_hash,
        "soo_functional_hash": evidence.soo_functional_hash,
        "initialization_hash": evidence.initialization_hash,
        "initialization_report": package.initialization_report.__dict__ if package.initialization_report else None,
        "initial_two_ledger_report": package.initial_two_ledger_report,
        "optional_module_report": package.optional_module_report,
        "path_construction_report": package.path_construction_report,
        "run_debugging_spec": package.run_debugging_spec,
        "initialization_settling_report": package.initialization_settling_report,
        "modeling_intent_contract_hash": (package.modeling_intent_contract.fingerprint() if package.modeling_intent_contract else None),
        "modeling_intent_compliance_report": package.modeling_intent_compliance_report,
        "soo_primitive_operator": getattr(package.config.scalar_update_rule, "primitive_operator_id", None),
        "rule_statuses": {
            "scalar_update": package.scalar_update_metadata.status.value,
            "association_remap": package.association_remap_metadata.status.value,
        },
    }

    return BaseGateReport(
        source_provenance_passed=source_provenance_passed,
        verdict_independence_passed=verdict_independence_passed,
        blind_generation_projection_separation_passed=blind_generation_projection_separation_passed,
        negative_controls_passed=controls.passed,
        leakage_manipulation_checks_passed=leakage_manipulation_checks_passed,
        external_admission_verdict=package.manifest.external_admission_verdict,
        details=details,
    )


def run_model_package(package: ModelPackage) -> EnforcedRunResult:
    """
    The single certified/enforced entry point.

    It audits before execution, runs required controls, runs the primary model,
    freezes and hashes the evidential records, runs pre-registered readouts, and
    constructs a blocking BASE gate.
    """

    core_hash = verify_core_integrity(expected_core_hash=package.manifest.expected_core_hash)
    _audit_manifest(package)
    _audit_rule_statuses(package)
    source_audits = _audit_rule_sources(package)

    controls = run_required_controls(
        config=package.config,
        required_controls=package.manifest.diagnostics.required_controls,
    )

    _reset_rule_trace_if_available(package.config.scalar_update_rule)

    primary_result = ImmutableScalarFieldGeometryResult.from_result(
        sfg.run_scalar_field_geometry(package.config)
    )

    soo_traces = _collect_rule_traces_if_available(package.config.scalar_update_rule)
    _finalize_rule_feedback_if_available(package.config.scalar_update_rule)
    soo_execution_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_soo_execution_report")
    if soo_execution_report is None:
        soo_execution_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_bounded_context_execution_report")
    cyclic_return_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_cyclic_return_report")
    stiffness_input_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_stiffness_input_report")
    response_burden_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_response_burden_report")
    induced_stiffness_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_induced_stiffness_report")
    stiffness_closure_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_stiffness_closure_report")
    stiffness_feedback_report = _get_rule_report_if_available(package.config.scalar_update_rule, "get_stiffness_feedback_report")
    path_facing_association_report = build_path_facing_association_report(
        path_report=package.path_construction_report,
        initial_state=primary_result.states[0] if primary_result.states else None,
    )
    role_path_remap_report = _get_rule_report_if_available(
        package.config.association_remap_rule,
        "get_role_path_remap_reports",
    )
    run_debugging_report = build_run_debugging_report(
        spec=package.run_debugging_spec,
        result=primary_result,
        path_report=package.path_construction_report,
        initial_phi_previous=package.config.initial_phi_previous,
        path_facing_report=path_facing_association_report,
        soo_execution_report=soo_execution_report,
    )
    soo_trace_audit_passed, soo_trace_details = _audit_soo_traces(
        package=package,
        result=primary_result,
        traces=soo_traces,
    )
    soo_trace_hash = stable_json_hash([trace.fingerprint() for trace in soo_traces]) if soo_traces else "not_applicable"
    soo_functional_report = build_soo_functional_report(
        scalar_update_rule=package.config.scalar_update_rule,
        metadata=package.scalar_update_metadata,
    )
    soo_functional_hash = soo_functional_report.fingerprint()

    readouts = _run_readouts(
        result=primary_result,
        readout_rules=package.readout_rules,
    )

    evidence = build_evidence_package(
        manifest=package.manifest,
        scalar_update_metadata=package.scalar_update_metadata,
        association_remap_metadata=package.association_remap_metadata,
        result=primary_result,
        readouts=readouts,
        controls_hash=controls.fingerprint(),
        compiled_overlay_hash=package.compiled_overlay_hash,
        soo_trace_hash=soo_trace_hash,
        soo_functional_hash=soo_functional_hash,
        initialization_hash=(
            package.initialization_report.fingerprint()
            if package.initialization_report is not None
            else "not_applicable"
        ),
    )

    gate = _build_base_gate(
        package=package,
        result=primary_result,
        controls=controls,
        source_audits=source_audits,
        readouts=readouts,
        evidence=evidence,
        soo_trace_audit_passed=soo_trace_audit_passed,
        soo_trace_details=soo_trace_details,
    )

    if package.manifest.requested_certification and not gate.passed:
        raise CertificationBlocked(
            "Certification/admission blocked by BASE gate. "
            f"Details: {gate.details}"
        )

    return EnforcedRunResult(
        manifest=package.manifest,
        primary_result=primary_result,
        readouts=readouts,
        controls=controls,
        source_audits=source_audits,
        evidence=evidence,
        gate=gate,
        core_hash=core_hash,
        soo_functional_report=soo_functional_report,
        soo_traces=soo_traces,
        initialization_soo_traces=package.initialization_soo_traces,
        initialization_report=package.initialization_report,
        initial_two_ledger_report=package.initial_two_ledger_report,
        optional_module_report=package.optional_module_report,
        path_construction_report=package.path_construction_report,
        run_debugging_spec=package.run_debugging_spec,
        soo_execution_report=soo_execution_report,
        cyclic_return_report=cyclic_return_report,
        stiffness_input_report=stiffness_input_report,
        response_burden_report=response_burden_report,
        induced_stiffness_report=induced_stiffness_report,
        stiffness_closure_report=stiffness_closure_report,
        stiffness_feedback_report=stiffness_feedback_report,
        path_facing_association_report=path_facing_association_report,
        role_path_remap_report=role_path_remap_report,
        run_debugging_report=run_debugging_report,
        initialization_settling_report=package.initialization_settling_report,
        modeling_intent_contract=package.modeling_intent_contract,
        modeling_intent_compliance_report=package.modeling_intent_compliance_report,
    )


def run_declarative_overlay(path: str | Path) -> EnforcedRunResult:
    """Run a certified/candidate-capable data-only overlay.

    This is the enforced entry point for candidate/admission modeling. It accepts
    JSON overlay files only. It does not import or execute overlay Python.
    """

    from .overlay_loader import load_declarative_overlay
    from .overlay_compiler import compile_overlay_to_model_package

    overlay, overlay_hash = load_declarative_overlay(path)
    package = compile_overlay_to_model_package(overlay, overlay_hash=overlay_hash)
    return run_model_package(package)
