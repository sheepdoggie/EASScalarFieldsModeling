from __future__ import annotations

from dataclasses import dataclass, asdict, is_dataclass
from pathlib import Path
from typing import Any
import base64
import csv
import json
from datetime import datetime, timezone

from .base_gate import BaseGateReport
from .certified_runner import EnforcedRunResult
from .evidence import EvidencePackage
from .fingerprints import directory_hash, file_hash, stable_json_hash
from .rule_metadata import AdmissionVerdict

CERT_GENERATED_FILES = {
    "EVIDENCE_ENVELOPE.json",
    "EVIDENCE_ENVELOPE.sig",
    "CERTIFICATE.json",
    "SHA256SUMS.csv",
    "FRAMEWORK_PUBLIC_KEY.pem",
}


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if hasattr(value, "value"):
        return value.value
    return str(value)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default).encode("utf-8")


def write_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class EvidenceEnvelope:
    certificate_schema: str
    framework_name: str
    framework_version: str
    framework_core_hash: str
    rule_registry_hash: str
    readout_registry_hash: str
    model_type_registry_hash: str
    overlay_hash: str
    compiled_manifest_hash: str
    initialization_trace_hash: str
    soo_trace_hash: str
    soo_functional_hash: str
    control_suite_hash: str
    raw_result_hash: str
    readout_result_hash: str
    base_gate_report_hash: str
    evidence_package_hash: str
    environment_hash: str
    command_hash: str
    package_hash: str
    file_hashes: dict[str, str]
    run_id: str
    run_kind: str
    external_verdict: str
    base_gate_passed: bool
    admitted: bool
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def signable_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class CertificateRecord:
    certificate_schema: str
    certificate_status: str
    signature_algorithm: str
    envelope_hash: str
    public_key_hash: str
    run_id: str
    run_kind: str
    external_verdict: str
    base_gate_passed: bool
    admitted: bool
    certifies: str
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationReport:
    certificate_status: str
    signature_valid: bool
    file_hashes_valid: bool
    package_hash_valid: bool
    unexpected_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    details: dict[str, Any]

    @property
    def valid(self) -> bool:
        return (
            self.certificate_status == "valid_framework_certificate"
            and self.signature_valid
            and self.file_hashes_valid
            and self.package_hash_valid
            and not self.unexpected_files
            and not self.missing_files
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_file_hashes(root: str | Path) -> dict[str, str]:
    root = Path(root)
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in CERT_GENERATED_FILES:
            continue
        hashes[rel] = file_hash(path)
    return hashes


def package_hash_from_file_hashes(file_hashes: dict[str, str]) -> str:
    return stable_json_hash(file_hashes)


def write_sha256sums(root: str | Path, file_hashes: dict[str, str]) -> None:
    root = Path(root)
    with (root / "SHA256SUMS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sha256", "relative_path"])
        for rel, digest in sorted(file_hashes.items()):
            writer.writerow([digest, rel])


def build_evidence_envelope(
    *,
    result: EnforcedRunResult,
    package_root: str | Path,
    command_hash: str,
    environment_hash: str,
    rule_registry_hash: str,
    readout_registry_hash: str,
    model_type_registry_hash: str,
    framework_version: str = "0.1.0",
    run_id: str | None = None,
) -> EvidenceEnvelope:
    package_root = Path(package_root)
    file_hashes = collect_file_hashes(package_root)
    package_hash = package_hash_from_file_hashes(file_hashes)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_id = run_id or f"rank3-{timestamp}-{result.evidence.package_hash[:12]}"
    return EvidenceEnvelope(
        certificate_schema="rank3_evidence_envelope_v1",
        framework_name="rank3_enforced",
        framework_version=framework_version,
        framework_core_hash=result.core_hash,
        rule_registry_hash=rule_registry_hash,
        readout_registry_hash=readout_registry_hash,
        model_type_registry_hash=model_type_registry_hash,
        overlay_hash=result.evidence.compiled_overlay_hash,
        compiled_manifest_hash=stable_json_hash(result.manifest),
        initialization_trace_hash=result.evidence.initialization_hash,
        soo_trace_hash=result.evidence.soo_trace_hash,
        soo_functional_hash=result.evidence.soo_functional_hash,
        control_suite_hash=result.evidence.control_hash,
        raw_result_hash=result.evidence.result_hash,
        readout_result_hash=result.evidence.readout_hash,
        base_gate_report_hash=stable_json_hash(result.gate),
        evidence_package_hash=result.evidence.package_hash,
        environment_hash=environment_hash,
        command_hash=command_hash,
        package_hash=package_hash,
        file_hashes=file_hashes,
        run_id=run_id,
        run_kind=result.manifest.run_kind,
        external_verdict=result.gate.external_admission_verdict.value,
        base_gate_passed=bool(result.gate.passed),
        admitted=bool(result.gate.passed and result.gate.external_admission_verdict == AdmissionVerdict.ADMITTED),
        timestamp_utc=timestamp,
    )


def write_enforced_run_package(
    *,
    result: EnforcedRunResult,
    output_dir: str | Path,
    overlay_path: str | Path | None = None,
    command: str = "not_recorded",
    environment: dict[str, Any] | None = None,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if overlay_path is not None:
        overlay_path = Path(overlay_path)
        (output / "overlay.json").write_text(overlay_path.read_text(encoding="utf-8"), encoding="utf-8")
    write_json(output / "compiled_manifest.json", result.manifest)
    write_json(output / "evidence_package.json", result.evidence)
    write_json(output / "BASE_GATE_REPORT.json", result.gate)
    write_json(output / "control_results.json", result.controls)
    write_json(output / "source_audits.json", result.source_audits)
    write_json(output / "readout_results.json", result.readouts)
    write_json(output / "soo_traces.json", result.soo_traces)
    write_json(output / "SOO_FUNCTIONAL_REPORT.json", result.soo_functional_report)
    write_json(output / "SOO_EXECUTION_REPORT.json", getattr(result, "soo_execution_report", None))
    write_json(output / "CYCLIC_RETURN_REPORT.json", getattr(result, "cyclic_return_report", None))
    write_json(output / "STIFFNESS_INPUT_REPORT.json", getattr(result, "stiffness_input_report", None))
    write_json(output / "RESPONSE_BURDEN_REPORT.json", getattr(result, "response_burden_report", None))
    write_json(output / "INDUCED_STIFFNESS_REPORT.json", getattr(result, "induced_stiffness_report", None))
    write_json(output / "STIFFNESS_CLOSURE_REPORT.json", getattr(result, "stiffness_closure_report", None))
    write_json(output / "STIFFNESS_FEEDBACK_REPORT.json", getattr(result, "stiffness_feedback_report", None))
    write_json(output / "initialization_soo_traces.json", result.initialization_soo_traces)
    write_json(output / "initialization_report.json", result.initialization_report)
    write_json(output / "INITIALIZATION_SETTLING_REPORT.json", getattr(result, "initialization_settling_report", None))
    write_json(output / "INITIAL_TWO_LEDGER_REPORT.json", getattr(result, "initial_two_ledger_report", None))
    write_json(output / "OPTIONAL_MODULE_REPORT.json", getattr(result, "optional_module_report", None))
    write_json(output / "PATH_CONSTRUCTION_REPORT.json", getattr(result, "path_construction_report", None))
    write_json(output / "PATH_FACING_ASSOCIATION_REPORT.json", getattr(result, "path_facing_association_report", None))
    write_json(output / "RUN_DEBUG_REPORT.json", getattr(result, "run_debugging_report", None))
    write_json(
        output / "raw_result_package.json",
        {
            "result_hash": result.primary_result.fingerprint(),
            "phi_shape": tuple(int(x) for x in result.primary_result.phi.shape),
            "phi_hash": result.evidence.result_hash,
            "state_fingerprints": [state.fingerprint for state in result.primary_result.states],
            "geometry_snapshot_hashes": [snap.fingerprint() for snap in result.primary_result.geometry_snapshots],
            "result_verified_immutable": result.primary_result.verify(),
        },
    )
    write_json(output / "command.json", {"command": command, "command_hash": stable_json_hash(command)})
    write_json(output / "environment.json", environment or {"environment": "not_recorded"})
