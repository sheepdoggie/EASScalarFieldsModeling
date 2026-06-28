from __future__ import annotations

import sys
from pathlib import Path

from rank3_enforced import run_declarative_overlay
from rank3_enforced.dual_package import create_dual_evidence_package, verify_dual_evidence_package
from rank3_enforced.package_manifest import default_environment_record
from rank3_enforced.version_guard import enforce_latest_release_guard


def main() -> None:
    if len(sys.argv) != 5:
        print(
            "Usage: python run_dual_declarative_overlay.py "
            "<overlay.json> <output_dir> <signing_private_key.pem> <recipient_encryption_public_key.pem>"
        )
        raise SystemExit(2)
    overlay_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    signing_private_key_path = Path(sys.argv[3])
    recipient_public_key_path = Path(sys.argv[4])
    # Required latest-version guard. The first successful check writes a
    # run-environment cache; looped executions in the same working directory
    # reuse that cache instead of fetching GitHub on every run.
    guard_report = enforce_latest_release_guard(run_kind="candidate", cache_dir=output_dir)
    result = run_declarative_overlay(overlay_path)
    environment = default_environment_record()
    environment["release_guard"] = guard_report.to_dict()
    manifest = create_dual_evidence_package(
        result=result,
        output_dir=output_dir,
        signing_private_key_path=signing_private_key_path,
        recipient_public_key_path=recipient_public_key_path,
        overlay_path=overlay_path,
        command=" ".join(sys.argv),
        environment=environment,
    )
    verification = verify_dual_evidence_package(output_dir)
    print("Release guard passed:", guard_report.passed)
    print("Release guard cache:", guard_report.cache_path)
    print("Dual evidence package:", output_dir)
    print("Transfer manifest valid without decryption:", verification.valid)
    print("Canonical package SHA-256:", manifest.canonical_package_sha256)
    print("Plaintext package:", output_dir / manifest.plaintext_package_name)
    print("Encrypted package:", output_dir / manifest.encrypted_package_name)
    print("Run kind:", result.manifest.run_kind)
    print("External verdict:", result.gate.external_admission_verdict.value)
    print("BASE gate passed:", result.gate.passed)


if __name__ == "__main__":
    main()
