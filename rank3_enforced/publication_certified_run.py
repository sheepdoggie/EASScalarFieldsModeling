from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .certificates import read_json, write_json
from .dual_package import create_dual_evidence_package, verify_dual_evidence_package
from .exceptions import CertificationBlocked, ManifestError
from .fingerprints import directory_hash, file_hash, stable_json_hash
from .package_manifest import default_environment_record, registry_hashes
from .run_manager import default_signing_key
from .certified_runner import run_declarative_overlay, verify_core_integrity
from .version_guard import enforce_latest_release_guard

POLICY_ID = "publication_certified_run_v1"
FORBIDDEN_INPUT_KEY_FRAGMENTS = (
    "callable",
    "function",
    "python",
    "module_path",
    "script",
    "source_code",
    "code",
    "lambda",
    "eval",
    "exec",
    "subprocess",
    "importlib",
    "pickle",
    "cloudpickle",
    "dill",
)
FORBIDDEN_INPUT_STRING_FRAGMENTS = (
    "__import__",
    "eval(",
    "exec(",
    "subprocess",
    "os.system",
    "importlib",
    "lambda ",
)
FORBIDDEN_EXTERNAL_CODE_SUFFIXES = (
    ".py",
    ".pyc",
    ".pyo",
    ".ipynb",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".so",
    ".pyd",
    ".dll",
    ".dylib",
)


@dataclass(frozen=True)
class PublicationInputAuditReport:
    schema: str
    policy_id: str
    overlay_path: str
    overlay_sha256: str | None
    overlay_is_json: bool
    overlay_is_data_only: bool
    overlay_parent_code_free: bool
    forbidden_key_hits: tuple[str, ...]
    forbidden_string_hits: tuple[str, ...]
    forbidden_external_code_files: tuple[str, ...]
    passed: bool
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class PublicationCertifiedRunReport:
    schema: str
    policy_id: str
    framework_version: str
    started_utc: str
    finished_utc: str
    overlay_path: str
    output_dir: str
    command: str
    command_hash: str
    environment_hash: str
    framework_core_hash: str
    registry_hashes: dict[str, str]
    input_audit: PublicationInputAuditReport
    release_guard_passed: bool
    transfer_manifest_hash: str | None
    transfer_package_valid_without_decryption: bool | None
    blocked: bool
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.blocked
            and not self.errors
            and self.input_audit.passed
            and self.release_guard_passed
            and bool(self.transfer_package_valid_without_decryption)
            and bool(self.transfer_manifest_hash)
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["passed"] = self.passed
        return d

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _walk_json(value: Any, path: str = "$") -> tuple[list[str], list[str]]:
    key_hits: list[str] = []
    string_hits: list[str] = []
    if isinstance(value, dict):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            lower_key = key.lower()
            for fragment in FORBIDDEN_INPUT_KEY_FRAGMENTS:
                if fragment in lower_key:
                    key_hits.append(f"{path}.{key}")
                    break
            sub_key_hits, sub_string_hits = _walk_json(raw_value, f"{path}.{key}")
            key_hits.extend(sub_key_hits)
            string_hits.extend(sub_string_hits)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            sub_key_hits, sub_string_hits = _walk_json(item, f"{path}[{index}]")
            key_hits.extend(sub_key_hits)
            string_hits.extend(sub_string_hits)
    elif isinstance(value, str):
        lower = value.lower()
        for fragment in FORBIDDEN_INPUT_STRING_FRAGMENTS:
            if fragment in lower:
                string_hits.append(path)
                break
    return key_hits, string_hits


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _forbidden_code_files(root: Path, *, allowed_files: Iterable[Path] = ()) -> tuple[str, ...]:
    allowed = {p.resolve() for p in allowed_files}
    hits: list[str] = []
    if not root.exists():
        return ()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() in allowed:
            continue
        if path.suffix.lower() in FORBIDDEN_EXTERNAL_CODE_SUFFIXES:
            hits.append(path.relative_to(root).as_posix())
    return tuple(hits)


def audit_publication_overlay_input(
    overlay_path: str | Path,
    *,
    strict_overlay_parent_code_free: bool = True,
) -> PublicationInputAuditReport:
    overlay = Path(overlay_path).resolve()
    overlay_sha = file_hash(overlay) if overlay.exists() and overlay.is_file() else None
    overlay_is_json = overlay.exists() and overlay.is_file() and overlay.suffix.lower() == ".json"
    key_hits: list[str] = []
    string_hits: list[str] = []
    details: dict[str, Any] = {}
    if overlay_is_json:
        try:
            payload = json.loads(overlay.read_text(encoding="utf-8"))
            key_hits, string_hits = _walk_json(payload)
            details["top_level_keys"] = sorted(payload.keys()) if isinstance(payload, dict) else []
        except Exception as exc:  # pragma: no cover - exact JSON decoder text varies
            details["json_parse_error"] = str(exc)
            overlay_is_json = False
    forbidden_files = ()
    if strict_overlay_parent_code_free and overlay.exists():
        forbidden_files = _forbidden_code_files(overlay.parent, allowed_files=(overlay,))
    parent_code_free = not forbidden_files
    data_only = overlay_is_json and not key_hits and not string_hits
    passed = bool(overlay_is_json and data_only and parent_code_free)
    return PublicationInputAuditReport(
        schema="rank3_publication_input_audit_v1",
        policy_id=POLICY_ID,
        overlay_path=str(overlay),
        overlay_sha256=overlay_sha,
        overlay_is_json=bool(overlay_is_json),
        overlay_is_data_only=bool(data_only),
        overlay_parent_code_free=bool(parent_code_free),
        forbidden_key_hits=tuple(key_hits),
        forbidden_string_hits=tuple(string_hits),
        forbidden_external_code_files=forbidden_files,
        passed=passed,
        details=details,
    )


def publication_environment_record(
    *,
    command: str,
    input_audit: PublicationInputAuditReport,
    release_guard: Any,
) -> dict[str, Any]:
    env = default_environment_record()
    env.update(
        {
            "publication_policy_id": POLICY_ID,
            "framework_version": __version__,
            "command": command,
            "input_audit_hash": input_audit.fingerprint(),
            "input_audit": input_audit.to_dict(),
            "release_guard": release_guard.to_dict() if hasattr(release_guard, "to_dict") else str(release_guard),
            "cwd": os.getcwd(),
            "argv": sys.argv,
            "platform_python_implementation": platform.python_implementation(),
        }
    )
    return env


def run_publication_certified_overlay(
    *,
    overlay_path: str | Path,
    output_dir: str | Path,
    signing_private_key_path: str | Path,
    recipient_public_key_path: str | Path,
    command: str,
    strict_overlay_parent_code_free: bool = True,
    keep_canonical_directory: bool = False,
    expected_core_hash: str | None = None,
) -> PublicationCertifiedRunReport:
    started = _now_utc()
    output = Path(output_dir).resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    transfer_manifest_hash: str | None = None
    transfer_valid: bool | None = None
    release_guard_passed = False
    input_audit = audit_publication_overlay_input(
        overlay_path,
        strict_overlay_parent_code_free=strict_overlay_parent_code_free,
    )
    try:
        if not input_audit.passed:
            raise CertificationBlocked("Publication-certified run blocked by input audit failure.")
        # Publication-grade runs must be through installed framework code and latest-release guard.
        release_guard = enforce_latest_release_guard(run_kind="candidate", cache_dir=output)
        release_guard_passed = bool(release_guard.passed)
        if not release_guard_passed:
            raise CertificationBlocked("Publication-certified run blocked by release guard failure.")
        core_hash = verify_core_integrity(expected_core_hash=expected_core_hash)
        env = publication_environment_record(
            command=command,
            input_audit=input_audit,
            release_guard=release_guard,
        )
        result = run_declarative_overlay(Path(overlay_path).resolve())
        manifest = create_dual_evidence_package(
            result=result,
            output_dir=output,
            signing_private_key_path=signing_private_key_path,
            recipient_public_key_path=recipient_public_key_path,
            overlay_path=overlay_path,
            command=command,
            environment=env,
            keep_canonical_directory=keep_canonical_directory,
        )
        transfer_manifest_hash = manifest.fingerprint()
        verify = verify_dual_evidence_package(output)
        transfer_valid = verify.valid
        if not verify.valid:
            raise CertificationBlocked("Publication-certified run produced an invalid transfer package.")
    except Exception as exc:
        errors.append(str(exc))
        core_hash = verify_core_integrity(expected_core_hash=None)
    finished = _now_utc()
    report = PublicationCertifiedRunReport(
        schema="rank3_publication_certified_run_report_v1",
        policy_id=POLICY_ID,
        framework_version=__version__,
        started_utc=started,
        finished_utc=finished,
        overlay_path=str(Path(overlay_path).resolve()),
        output_dir=str(output),
        command=command,
        command_hash=stable_json_hash(command),
        environment_hash=stable_json_hash(default_environment_record()),
        framework_core_hash=core_hash,
        registry_hashes=registry_hashes(),
        input_audit=input_audit,
        release_guard_passed=release_guard_passed,
        transfer_manifest_hash=transfer_manifest_hash,
        transfer_package_valid_without_decryption=transfer_valid,
        blocked=bool(errors),
        errors=tuple(errors),
    )
    write_json(output / "PUBLICATION_CERTIFIED_RUN_REPORT.json", report.to_dict())
    return report


def verify_publication_certified_package(
    transfer_dir: str | Path,
    *,
    recipient_private_key_path: str | Path | None = None,
) -> dict[str, Any]:
    transfer_dir = Path(transfer_dir)
    dual_report = verify_dual_evidence_package(
        transfer_dir,
        recipient_private_key_path=recipient_private_key_path,
    )
    report_path = transfer_dir / "PUBLICATION_CERTIFIED_RUN_REPORT.json"
    publication_report = read_json(report_path) if report_path.exists() else None
    publication_passed = bool(publication_report and publication_report.get("passed") is True)
    return {
        "schema": "rank3_publication_package_verification_v1",
        "policy_id": POLICY_ID,
        "dual_package_valid": dual_report.valid,
        "dual_package_report": dual_report.to_dict(),
        "publication_report_present": report_path.exists(),
        "publication_report_passed": publication_passed,
        "valid": bool(dual_report.valid and publication_passed),
    }


def main_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one overlay in publication-certified mode and create signed plaintext+encrypted evidence.")
    parser.add_argument("overlay", help="Data-only declarative overlay JSON")
    parser.add_argument("output_dir", help="Output transfer package directory")
    parser.add_argument("--signing-key", default=str(default_signing_key()), help="Ed25519 private signing key path")
    parser.add_argument("--recipient-public-key", required=True, help="X25519 recipient public encryption key path")
    parser.add_argument("--expected-core-hash", default=None, help="Optional expected rank3_enforced core directory hash")
    parser.add_argument("--keep-canonical-directory", action="store_true", help="Keep unzipped canonical evidence directory for local inspection")
    parser.add_argument("--allow-code-near-overlay", action="store_true", help="Disable strict overlay-parent code-free audit; not recommended")
    args = parser.parse_args(argv)
    command = "rank3-run-publication-certified " + " ".join(sys.argv[1:] if argv is None else argv)
    report = run_publication_certified_overlay(
        overlay_path=args.overlay,
        output_dir=args.output_dir,
        signing_private_key_path=args.signing_key,
        recipient_public_key_path=args.recipient_public_key,
        command=command,
        strict_overlay_parent_code_free=not args.allow_code_near_overlay,
        keep_canonical_directory=args.keep_canonical_directory,
        expected_core_hash=args.expected_core_hash,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str))
    return 0 if report.passed else 1


def main_verify(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a publication-certified transfer package.")
    parser.add_argument("transfer_dir", help="Publication transfer package directory")
    parser.add_argument("--recipient-private-key", default=None, help="Optional X25519 private key to decrypt and verify inner certificate")
    args = parser.parse_args(argv)
    report = verify_publication_certified_package(
        args.transfer_dir,
        recipient_private_key_path=args.recipient_private_key,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["valid"] else 1
