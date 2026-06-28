from __future__ import annotations

import sys
from pathlib import Path

from rank3_enforced import run_declarative_overlay


def main() -> None:
    overlay_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("overlays/minimal_control_overlay.json")
    result = run_declarative_overlay(overlay_path)
    print("Overlay:", overlay_path)
    print("Model:", result.manifest.model_name)
    print("Run kind:", result.manifest.run_kind)
    print("External verdict:", result.gate.external_admission_verdict.value)
    print("BASE gate passed:", result.gate.passed)
    print("Certified/admitted:", result.certified)
    print("Controls passed:", result.controls.passed)
    print("Compiled overlay hash:", result.evidence.compiled_overlay_hash)
    print("Evidence package hash:", result.evidence.package_hash)


if __name__ == "__main__":
    main()
