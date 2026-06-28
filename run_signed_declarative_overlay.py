from __future__ import annotations

import sys
from pathlib import Path

from rank3_enforced import run_declarative_overlay
from rank3_enforced.package_manifest import default_environment_record, package_and_sign_enforced_result
from rank3_enforced.version_guard import enforce_latest_release_guard
from rank3_enforced.signing import verify_certificate


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python run_signed_declarative_overlay.py "
            "<overlay.json> <output_dir> <private_key.pem>"
        )
        raise SystemExit(2)
    overlay_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    private_key_path = Path(sys.argv[3])
    # Required latest-version guard. The first successful check writes a
    # run-environment cache; looped executions in the same working directory
    # reuse that cache instead of fetching GitHub on every run.
    guard_report = enforce_latest_release_guard(run_kind="candidate", cache_dir=output_dir.parent)
    result = run_declarative_overlay(overlay_path)
    environment = default_environment_record()
    environment["release_guard"] = guard_report.to_dict()
    package_and_sign_enforced_result(
        result=result,
        output_dir=output_dir,
        private_key_path=private_key_path,
        overlay_path=overlay_path,
        command=" ".join(sys.argv),
        environment=environment,
    )
    verification = verify_certificate(output_dir)
    print("Release guard passed:", guard_report.passed)
    print("Release guard cache:", guard_report.cache_path)
    print("Signed package:", output_dir)
    print("Certificate valid:", verification.valid)
    print("Run kind:", result.manifest.run_kind)
    print("External verdict:", result.gate.external_admission_verdict.value)
    print("BASE gate passed:", result.gate.passed)


if __name__ == "__main__":
    main()
